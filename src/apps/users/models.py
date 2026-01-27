from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        IT_ADMIN = 'IT_ADMIN', 'IT Admin'
        MANAGER = 'MANAGER', 'Manager'
        ACCOUNTANT = 'ACCOUNTANT', 'Accountant'
        SALES = 'SALES', 'Sales'
        MARKETING = 'MARKETING', 'Marketing'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SALES)
    department = models.CharField(max_length=100, blank=True)

    def is_manager(self):
        return self.role == self.Role.MANAGER

    def is_accountant(self):
        return self.role == self.Role.ACCOUNTANT
    
    def is_sales(self):
        return self.role == self.Role.SALES

    def save(self, *args, **kwargs):
        # Enforce Admin Access for all specified roles
        if self.role in [self.Role.IT_ADMIN, self.Role.MANAGER, self.Role.ACCOUNTANT, self.Role.SALES, self.Role.MARKETING]:
            self.is_staff = True
        super().save(*args, **kwargs)
