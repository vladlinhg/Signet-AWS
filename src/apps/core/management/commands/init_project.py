from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.clients.models import City, Ethnicity
from apps.currencies.models import Currency, ExchangeRate
from apps.flights.models import Airline, Airport
from apps.core.initial_data import USERS, CURRENCIES, CITIES, ETHNICITIES, AIRLINES, AIRPORTS

User = get_user_model()

class Command(BaseCommand):
    help = 'Initialize Static Data (Users, Cities, Currencies, Airlines, Airports)'

    def handle(self, *args, **options):
        self.stdout.write("Initializing Project Static Data...")

        # 1. Users
        self.stdout.write(f"Loading {len(USERS)} Users...")
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

        # 2. Currencies
        self.stdout.write(f"Loading {len(CURRENCIES)} Currencies...")
        for curr_data in CURRENCIES:
            c, _ = Currency.objects.get_or_create(
                code=curr_data['code'],
                defaults={'name': curr_data['name'], 'symbol': curr_data['symbol']}
            )
            if curr_data.get('is_base'):
                c.is_base = True
                c.save()

            if 'rate' in curr_data:
                 ExchangeRate.objects.get_or_create(
                    currency=c,
                    date=timezone.now().date(),
                    defaults={'rate_to_base': curr_data['rate']}
                )

        # 3. Cities
        self.stdout.write(f"Loading {len(CITIES)} Cities...")
        for city_data in CITIES:
            City.objects.get_or_create(
                name=city_data['name'],
                country_code=city_data['country_code']
            )

        # 4. Ethnicities
        self.stdout.write(f"Loading {len(ETHNICITIES)} Ethnicities...")
        for eth_name in ETHNICITIES:
            Ethnicity.objects.get_or_create(name=eth_name)

        # 5. Airlines
        self.stdout.write(f"Loading {len(AIRLINES)} Airlines...")
        for al in AIRLINES:
            Airline.objects.get_or_create(code=al['code'], defaults={'name': al['name']})

        # 6. Airports
        self.stdout.write(f"Loading {len(AIRPORTS)} Airports...")
        for ap in AIRPORTS:
            Airport.objects.get_or_create(code=ap['code'], defaults={'name': ap['name']})

        self.stdout.write(self.style.SUCCESS('Static Data Initialized Successfully.'))
