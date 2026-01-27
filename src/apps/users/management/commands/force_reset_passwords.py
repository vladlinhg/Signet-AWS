from django.core.management.base import BaseCommand
from apps.users.models import User
import csv
from pathlib import Path

class Command(BaseCommand):
    help = 'Force reset passwords for users in CSV'

    def handle(self, *args, **options):
        csv_path = Path('data/users.csv')
        if not csv_path.exists():
            # In docker, path might be different? Default Base is OK.
            print("CSV not found at data/users.csv. Trying absolute if needed.")
            # If run from /app/ inside docker, data is at /app/data
            if not csv_path.exists():
                 # Try absolute (in Docker context)
                 csv_path = Path('/app/data/users.csv')
                 
        if not csv_path.exists():
             print(f"FAILED: Could not find users.csv at {csv_path}")
             return

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    u = User.objects.get(username=row['username'])
                    u.set_password(row['password'])
                    u.save()
                    self.stdout.write(f"Reset password for {u.username}")
                except User.DoesNotExist:
                    self.stdout.write(f"User {row['username']} not found, skipping.")
