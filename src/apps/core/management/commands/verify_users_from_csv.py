import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class Command(BaseCommand):
    help = 'Verifies that users in data/users.csv exist in the database.'

    def handle(self, *args, **options):
        # Path logic matching import_erp_data
        base_dir = settings.BASE_DIR.parent / 'data'
        csv_path = base_dir / 'users.csv'
        
        # Fallback for container mapping if needed, but above should work given docker volume
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.WARNING(f"CSV not found at {csv_path}. Checking /data/users.csv..."))
            if os.path.exists('/data/users.csv'):
                csv_path = '/data/users.csv'
            else:
                self.stderr.write(self.style.ERROR(f"Could not find users.csv at {csv_path} or /data/users.csv"))
                exit(1)

        self.stdout.write(f"Verifying users from {csv_path}...")
        
        missing_users = []
        checked_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                username = row.get('username')
                if not username:
                    continue
                
                checked_count += 1
                if not User.objects.filter(username=username).exists():
                    missing_users.append(username)
        
        if missing_users:
            self.stderr.write(self.style.ERROR(f"FAIL: The following users are missing from DB: {', '.join(missing_users)}"))
            exit(1)
        else:
            self.stdout.write(self.style.SUCCESS(f"SUCCESS: All {checked_count} users from CSV verifyed in database."))
