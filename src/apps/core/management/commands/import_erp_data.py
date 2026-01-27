import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.dateparse import parse_date
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.core.services import DataImporter
from apps.users.models import User
from apps.currencies.models import Currency, ExchangeRate
import csv
import os
from pathlib import Path
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Import ERP data from CSV files in /data directory'

    def add_arguments(self, parser):
        parser.add_argument('--users-only', action='store_true', help='Only import users')

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR.parent / 'data'
        if not os.path.exists(base_dir):
            if os.path.exists('/data'):
                base_dir = Path('/data')
        
        print(f"DEBUG: Data Import Base Directory: {base_dir}")
        importer = DataImporter()
        
        # 1. Autoload Users if requested or if DB is empty?
        # Let's just allow a flag
        if options['users_only']:
            self.import_users(base_dir / 'users.csv')
            print("Syncing Permissions...")
            call_command('setup_permissions')
            return

        # 1. Currencies 
        self.import_currencies(base_dir / 'currencies.csv')
        
        # 2. Users (Keep here - system level)
        self.import_users(base_dir / 'users.csv')
        
        # 3. Dynamic Data via Service
        if os.path.exists(base_dir / 'flights.csv'):
            print("Importing Flights...")
            with open(base_dir / 'flights.csv', 'rb') as f:
                importer.process_csv(f, 'flights')
                
        if os.path.exists(base_dir / 'tours.csv'):
            print("Importing Tours...")
            with open(base_dir / 'tours.csv', 'rb') as f:
                importer.process_csv(f, 'tours')
                
        if os.path.exists(base_dir / 'clients.csv'):
            print("Importing Clients...")
            with open(base_dir / 'clients.csv', 'rb') as f:
                importer.process_csv(f, 'clients')

        print("Syncing Permissions...")
        call_command('setup_permissions')

    def import_currencies(self, path):
        if not os.path.exists(path): return
        print(f"Importing Currencies from {path}...")
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                c, _ = Currency.objects.get_or_create(
                    code=row['code'],
                    defaults={'name': row['name'], 'symbol': row['symbol']}
                )
                if row['code'] == 'CAD':
                    c.is_base = True
                    c.save()
                try:
                    ExchangeRate.objects.get_or_create(
                        currency=c,
                        date='2026-01-01',
                        defaults={'rate_to_base': row['rate_to_cad']}
                    )
                except: pass

    def import_users(self, path):
        if not os.path.exists(path): return
        print(f"Importing Users from {path}...")
        # Use utf-8-sig to handle BOM from Windows Excel CSVs
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                username = row['username'].strip()
                if not username: continue
                
                user, created = User.objects.update_or_create(
                    username=username,
                    defaults={
                        'role': row['role'],
                        'email': row['email'],
                        'is_active': True
                    }
                )
                if created:
                    user.set_password(row['password'])
                    user.save()
                    print(f"Created user: {username}")
                else:
                    print(f"Updated user: {username}")

