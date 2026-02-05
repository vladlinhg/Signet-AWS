import os
import django
import random
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.clients.models import Client, City, Ethnicity
from apps.tours.models import Product, TourInstance
from apps.flights.models import Flight, FlightTicket, Airline, Airport, FlightInstance
from apps.currencies.models import Currency, ExchangeRate
from apps.core.initial_data import USERS, CURRENCIES, CITIES, ETHNICITIES

User = get_user_model()

def run():
    print("Initializing DB Content from Config...")

    # 1. Users
    print(f"Loading {len(USERS)} Users...")
    for user_data in USERS:
        username = user_data['username']
        defaults = {
            'email': user_data['email'],
            'role': getattr(User.Role, user_data['role'], 'SALES'),
            'is_staff': True,
            'is_superuser': user_data.get('is_superuser', False)
        }
        u, created = User.objects.update_or_create(username=username, defaults=defaults)
        if created:
            u.set_password(user_data['password'])
            u.save()
            print(f"  Created: {username}")
        else:
            print(f"  Updated: {username}")

    # 2. Currencies
    print(f"Loading {len(CURRENCIES)} Currencies...")
    for curr_data in CURRENCIES:
        c, _ = Currency.objects.get_or_create(
            code=curr_data['code'],
            defaults={'name': curr_data['name'], 'symbol': curr_data['symbol']}
        )
        if curr_data.get('is_base'):
            c.is_base = True
            c.save()

        # Rate (Mock rate for today)
        if 'rate' in curr_data:
            ExchangeRate.objects.get_or_create(
                currency=c,
                date=timezone.now().date(),
                defaults={'rate_to_base': curr_data['rate']}
            )

    # 3. Cities
    print(f"Loading {len(CITIES)} Cities...")
    for city_data in CITIES:
        City.objects.get_or_create(
            name=city_data['name'],
            country_code=city_data['country_code']
        )

    # 4. Ethnicities
    print(f"Loading {len(ETHNICITIES)} Ethnicities...")
    for eth_name in ETHNICITIES:
        Ethnicity.objects.get_or_create(name=eth_name)

    # 5. Dummy Clients (Preserve existing dev data logic)
    if Client.objects.count() == 0:
        print("Generating Dummy Clients...")
        # Get defaults
        default_city = City.objects.first()
        default_city_id = default_city.id if default_city else None
        # We need a city instance for certain FKs, but let's just leave it blank if None

        for i in range(5):
            Client.objects.create(
                first_name=f'Client{i}',
                last_name='Test',
                email=f'client{i}@test.com',
                phone=f'555-010{i}',
                origin=default_city
            )
        print("Created 5 Dummy Clients")

    # 6. Dummy Products
    if Product.objects.count() == 0:
        print("Generating Dummy Products...")
        p1 = Product.objects.create(
            name='Safari Adventure',
            country_code='KEN', days_count='10', unique_seq='001'
        )
        p2 = Product.objects.create(
            name='City Break',
            country_code='FRA', days_count='05', unique_seq='002'
        )
        print("Created Products")

        # 7. Inventory (Tours & Flights) - Required for Sales Generation
        print("Generating Inventory...")

        # Tour Instances
        start_date = timezone.now().date() + timedelta(days=30)
        TourInstance.objects.get_or_create(product=p1, start_date=start_date, defaults={'end_date': start_date + timedelta(days=10)})
        TourInstance.objects.get_or_create(product=p2, start_date=start_date, defaults={'end_date': start_date + timedelta(days=5)})

        # Flights
        ac, _ = Airline.objects.get_or_create(code='AC', defaults={'name': 'Air Canada'})
        yvr, _ = Airport.objects.get_or_create(code='YVR', defaults={'name': 'Vancouver Intl'})
        lhr, _ = Airport.objects.get_or_create(code='LHR', defaults={'name': 'Heathrow'})

        flight, _ = Flight.objects.get_or_create(
            airline=ac, flight_number='001',
            defaults={'departure_airport': yvr, 'arrival_airport': lhr, 'airline_name': 'Air Canada'}
        )

        from datetime import time
        if not FlightInstance.objects.filter(flight=flight, departure_date=start_date).exists():
             FlightInstance.objects.create(
                 flight=flight,
                 departure_date=start_date,
                 departure_time=time(10, 0),
                 arrival_time=time(18, 0)
             )

        print("Created Inventory")

    print("DB Init Complete.")

if __name__ == '__main__':
    run()
