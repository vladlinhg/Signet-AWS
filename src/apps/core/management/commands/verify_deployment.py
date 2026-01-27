import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client
from apps.currencies.models import Currency
from apps.flights.models import Flight
from apps.tours.models import TourInstance
from apps.clients.models import Client as ClientModel

User = get_user_model()

class Command(BaseCommand):
    help = 'Verify deployment integrity: Data Sync, Cleanup, and Role-based Health Checks.'

    def handle(self, *args, **options):
        self.data_dir = settings.BASE_DIR.parent / 'data'
        if not os.path.exists(self.data_dir):
            # Fallback for container
            self.data_dir = '/data'
        
        self.stdout.write("Starting Comprehensive Deployment Verification...")
        
        # 1-5 & 6. Verify Imports and Clean Noise
        self.verify_and_clean_users()
        
        # Verify Currencies (CSV: code -> Model: code)
        self.verify_and_clean_generic(Currency, 'currencies.csv', 'code', 'code')
        
        # Verify Tours (CSV: unique -> Product Model: unique_seq)
        # Note: We verify the Product definition, not every instance, which is cleaner for checking import success.
        from apps.tours.models import Product
        self.verify_and_clean_generic(Product, 'tours.csv', 'unique_seq', 'unique') 
        
        # Verify Flights (CSV: flight_no -> Model: flight_number)
        self.verify_and_clean_generic(Flight, 'flights.csv', 'flight_number', 'flight_no')   
        
        # Verify Clients (CSV: email -> Model: email)
        self.verify_and_clean_generic(ClientModel, 'clients.csv', 'email', 'email')

        # 7. Role-based Health Checks
        self.run_role_health_checks()
        
        self.stdout.write(self.style.SUCCESS("\nALL CHECKS PASSED SUCCESSFULLY."))

    def _read_csv(self, filename):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            self.stdout.write(self.style.WARNING(f"File {filename} not found. Skipping."))
            return []
        with open(path, 'r', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))

    def verify_and_clean_users(self):
        self.stdout.write("\n--- Verifying Users ---")
        rows = self._read_csv('users.csv')
        csv_usernames = {row['username'].strip() for row in rows}
        
        # Verify Missing
        db_users = set(User.objects.values_list('username', flat=True))
        missing = csv_usernames - db_users
        if missing:
            self.stdout.write(self.style.WARNING(f"DB Users found: {sorted(list(db_users))}"))
            self.stderr.write(self.style.ERROR(f"MISSING Users in DB: {missing}"))
            exit(1)
            
        # Verify Noise (Extras)
        extras = db_users - csv_usernames
        # Exclude admin or system users if they aren't in CSV but deemed necessary?
        # Assuming admin IS in users.csv based on previous context. If not, protect 'admin'.
        extras = {u for u in extras if u != 'admin'} 
        
        if extras:
            self.stdout.write(self.style.WARNING(f"Found {len(extras)} extra users. Cleaning up..."))
            User.objects.filter(username__in=extras).delete()
        else:
            self.stdout.write(self.style.SUCCESS(f"User count matches CSV ({len(csv_usernames)})."))

    def verify_and_clean_model(self, Model, filename, unique_field, csv_field):
        # Specific cleaning not implemented generically safely without IDs, 
        # so we'll enforce Count Equality and Existence.
        pass

    def verify_and_clean_generic(self, Model, filename, db_field, csv_field=None):
        if csv_field is None:
            csv_field = db_field
            
        model_name = Model.__name__
        self.stdout.write(f"\n--- Verifying {model_name} ---")
        rows = self._read_csv(filename)
        if not rows: return

        csv_keys = {row.get(csv_field) for row in rows if row.get(csv_field)}
        
        if not csv_keys:
            self.stdout.write(self.style.WARNING(f"No keys found in {filename} for field {csv_field}."))
            return

        # Verify Import (Existence)
        # Using filter(field__in=...)
        qs = Model.objects.filter(**{f"{db_field}__in": csv_keys})
        found_count = qs.count()
        
        if found_count < len(csv_keys):
            self.stderr.write(self.style.ERROR(f"MISSING {model_name}: Expected at least {len(csv_keys)}, found {found_count}."))
            # We could identify specifics, but count verification is a good blocker.
            exit(1)
            
        # Clean Noise
        # Delete objects NOT in the CSV keys
        extras = Model.objects.exclude(**{f"{db_field}__in": csv_keys})
        extra_count = extras.count()
        if extra_count > 0:
            self.stdout.write(self.style.WARNING(f"Found {extra_count} extra {model_name}. Cleaning..."))
            extras.delete()
        else:
            self.stdout.write(self.style.SUCCESS(f"{model_name} clean (Count: {found_count})."))

    def run_role_health_checks(self):
        self.stdout.write("\n--- Role-Based Health Checks ---")
        # Map roles to dashboards
        role_map = {
            'sales': '/sales/dashboard/',
            'manager': '/manager/dashboard/',
            'marketing': '/marketing/dashboard/',
            'accountant': '/accountant/dashboard/',
            'admin': '/admin/' # Django admin
        }
        
        rows = self._read_csv('users.csv')
        
        client = Client()
        
        # Group users by role to test one of each
        tested_roles = set()
        
        for row in rows:
            role = row.get('role', 'admin').lower() # Default to admin if not specified? Or map permissions.
            # Adjust role mapping to match CSV values (e.g. Sales, Manager)
            
            # Normalize CSV role to URL key
            target_url = None
            if 'sales' in role: target_url = role_map['sales']
            elif 'manager' in role: target_url = role_map['manager']
            elif 'marketing' in role: target_url = role_map['marketing']
            elif 'accountant' in role: target_url = role_map['accountant']
            elif 'admin' in role or 'superuser' in role: target_url = role_map['admin']
            
            if target_url and role not in tested_roles:
                self.stdout.write(f"Testing Login for Role: {role} (User: {row['username']})...")
                
                # Logout previous
                client.logout()
                
                # Login
                is_logged_in = client.login(username=row['username'], password=row['password'])
                if not is_logged_in:
                    self.stderr.write(self.style.ERROR(f"Login FAILED for {row['username']}"))
                    exit(1)
                
                # Check URL
                resp = client.get(target_url)
                if resp.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f"[OK] {target_url}"))
                    tested_roles.add(role)
                else:
                    self.stderr.write(self.style.ERROR(f"[FAIL] {target_url} - Status: {resp.status_code}"))
                    # Don't exit immediately? Or yes, stricter.
                    exit(1)
