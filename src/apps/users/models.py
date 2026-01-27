from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        MANAGER = 'MANAGER', 'Manager'
        ACCOUNTANT = 'ACCOUNTANT', 'Accountant'
        SALES = 'SALES', 'Sales'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SALES)
    department = models.CharField(max_length=100, blank=True)

    def is_manager(self):
        return self.role == self.Role.MANAGER

    def is_accountant(self):
        return self.role == self.Role.ACCOUNTANT
    
    def is_sales(self):
        return self.role == self.Role.SALES
