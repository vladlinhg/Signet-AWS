from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Sets is_staff=True for all existing users with valid roles.'

    def handle(self, *args, **options):
        users = User.objects.all()
        count = 0
        for user in users:
            if user.role in [User.Role.IT_ADMIN, User.Role.MANAGER, User.Role.ACCOUNTANT, User.Role.SALES, User.Role.MARKETING]:
                if not user.is_staff:
                    user.is_staff = True
                    user.save()
                    count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} users to is_staff=True.'))
