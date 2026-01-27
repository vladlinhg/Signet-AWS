import os
import django
import random
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.clients.models import Client
from apps.tours.models import Product, TourInstance
from apps.flights.models import Flight, FlightTicket
from apps.currencies.models import Currency, ExchangeRate

User = get_user_model()

def run():
    print("Initializing DB Content...")
    
    # Users
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@signet.com', 'adminpass')
        print("Created Superuser: admin")

    roles = [
        ('sales_agent', User.Role.SALES),
        ('manager_user', User.Role.MANAGER),
        ('accountant_user', User.Role.ACCOUNTANT),
        ('marketing_user', User.Role.MARKETING),
        ('it_admin_user', User.Role.IT_ADMIN)
    ]
    
    for username, role in roles:
        if not User.objects.filter(username=username).exists():
            u = User.objects.create_user(username, f'{username}@signet.com', 'password123')
            u.role = role
            u.save() # Triggers save() hook for is_staff
            print(f"Created User: {username} ({role})")

    # Currencies
    usd, _ = Currency.objects.get_or_create(code='USD', defaults={'symbol': '$', 'name': 'US Dollar'})
    cad, _ = Currency.objects.get_or_create(code='CAD', defaults={'symbol': 'C$', 'name': 'Canadian Dollar'})
    
    # Clients
    if Client.objects.count() == 0:
        for i in range(5):
            Client.objects.create(
                first_name=f'Client{i}',
                last_name='Test',
                email=f'client{i}@test.com',
                phone=f'555-010{i}'
            )
        print("Created 5 Clients")
        
    # Products
    if Product.objects.count() == 0:
        p1 = Product.objects.create(
            name='Safari Adventure', 
            country_code='KEN', days_count='10', unique_seq='001'
        )
        p2 = Product.objects.create(
            name='City Break', 
            country_code='FRA', days_count='05', unique_seq='002'
        )
        print("Created Products")
        
    print("DB Init Complete.")

if __name__ == '__main__':
    run()
