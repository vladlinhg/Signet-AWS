from django.core.management.base import BaseCommand
from apps.clients.models import City, Ethnicity
from apps.flights.models import Airport, Airline

class Command(BaseCommand):
    help = 'Seeds reference data for Cities, Ethnicities, Airports, Airlines, Currencies, and Users.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Reference Data...")

        # 1. Hometown Cities
        cities_data = {
            "metro_vancouver": [
                "Vancouver", "Richmond", "Burnaby", "Surrey", "Coquitlam",
                "New Westminster", "North Vancouver", "West Vancouver", "Delta",
                "Langley", "Port Coquitlam", "Port Moody", "Maple Ridge"
            ],
            "canada_other": [
                "Toronto", "Mississauga", "Brampton", "Markham", "Scarborough",
                "Ottawa", "Montreal", "Laval", "Calgary", "Edmonton",
                "Winnipeg", "Hamilton", "Kitchener", "Waterloo", "Guelph",
                "London (ON)", "Victoria", "Nanaimo", "Kelowna", "Kamloops",
                "Prince George"
            ],
            "international": [
                "Hong Kong", "Shanghai", "Beijing", "Shenzhen", "Guangzhou",
                "Taipei", "Kaohsiung", "Seoul", "Busan", "Tokyo", "Osaka",
                "Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad",
                "Lahore", "Karachi", "Dhaka", "Manila", "Cebu",
                "Ho Chi Minh City", "Hanoi", "Bangkok", "Jakarta",
                "London", "Manchester", "Paris", "Berlin", "Frankfurt",
                "Rome", "Milan", "Madrid", "Barcelona", "Amsterdam",
                "Tehran", "Dubai", "Abu Dhabi", "Cairo", "Johannesburg",
                "Los Angeles", "San Francisco", "Seattle", "New York City",
                "Chicago", "Mexico City", "São Paulo"
            ]
        }

        for category, city_list in cities_data.items():
            country = "CA" if category in ["metro_vancouver", "canada_other"] else ""
            for city_name in city_list:
                City.objects.get_or_create(
                    name=city_name,
                    defaults={'country_code': country}
                )
        self.stdout.write(f"Seeded {City.objects.count()} Cities.")

        # 2. Ethnicity
        ethnicity_data = {
            "broad_categories": [
                "Indigenous (First Nations, Métis, Inuit)", "White / European",
                "East Asian", "South Asian", "Southeast Asian", "Middle Eastern",
                "African", "Latin American", "Mixed / Multiple Ethnicities",
                "Other", "Prefer not to say"
            ],
            "detailed_options": [
                "Chinese", "Indian", "Punjabi", "Pakistani", "Filipino",
                "Korean", "Japanese", "Vietnamese", "Iranian / Persian",
                "Arab", "Jewish", "Ukrainian", "Russian", "Polish",
                "Italian", "German", "French", "British", "Irish",
                "Mexican", "Brazilian", "Colombian", "Nigerian",
                "Ethiopian"
            ]
        }

        all_ethnicities = set(ethnicity_data["broad_categories"] + ethnicity_data["detailed_options"])
        for eth_name in all_ethnicities:
            Ethnicity.objects.get_or_create(name=eth_name)
        self.stdout.write(f"Seeded {Ethnicity.objects.count()} Ethnicities.")

        # 3. Frequent Airports
        airports_data = {
            "primary": [
                { "code": "YVR", "name": "Vancouver International Airport" },
                { "code": "YXX", "name": "Abbotsford International Airport" }
            ],
            "canada_nearby": [
                { "code": "YYJ", "name": "Victoria International Airport" },
                { "code": "YCD", "name": "Nanaimo Airport" },
                { "code": "YKA", "name": "Kamloops Airport" },
                { "code": "YLW", "name": "Kelowna International Airport" }
            ],
            "us_cross_border": [
                { "code": "BLI", "name": "Bellingham International Airport" },
                { "code": "SEA", "name": "Seattle–Tacoma International Airport" },
                { "code": "PAE", "name": "Paine Field (Everett)" }
            ],
            "international_hubs": [
                { "code": "HKG", "name": "Hong Kong International Airport" },
                { "code": "ICN", "name": "Incheon International Airport" },
                { "code": "NRT", "name": "Tokyo Narita International Airport" },
                { "code": "HND", "name": "Tokyo Haneda Airport" },
                { "code": "LAX", "name": "Los Angeles International Airport" },
                { "code": "SFO", "name": "San Francisco International Airport" },
                { "code": "ORD", "name": "Chicago O'Hare International Airport" },
                { "code": "JFK", "name": "John F. Kennedy International Airport" },
                { "code": "LHR", "name": "London Heathrow Airport" },
                { "code": "FRA", "name": "Frankfurt Airport" }
            ]
        }

        for category, airport_list in airports_data.items():
            for airport in airport_list:
                Airport.objects.get_or_create(
                    code=airport["code"],
                    defaults={'name': airport["name"]}
                )
        self.stdout.write(f"Seeded {Airport.objects.count()} Airports.")

        # 4. Airlines
        airlines = [
            {"code": "AC", "name": "Air Canada"},
            {"code": "BR", "name": "EVA Air"},
            {"code": "CI", "name": "China Airlines"},
            {"code": "CX", "name": "Cathay Pacific"},
            {"code": "NH", "name": "All Nippon Airways"},
            {"code": "JL", "name": "Japan Airlines"},
            {"code": "CZ", "name": "China Southern Airlines"},
            {"code": "MU", "name": "China Eastern Airlines"},
        ]
        for al in airlines:
            Airline.objects.get_or_create(code=al["code"], defaults={'name': al["name"]})
        self.stdout.write("Seeded Airlines.")

        # 5. Currencies
        currencies_data = [
            {"code": "CAD", "symbol": "$", "name": "Canadian Dollar", "rate": 1.00},
            {"code": "USD", "symbol": "$", "name": "US Dollar", "rate": 0.75},
            {"code": "EUR", "symbol": "€", "name": "Euro", "rate": 0.68},
            {"code": "GBP", "symbol": "£", "name": "British Pound", "rate": 0.58},
            {"code": "CHF", "symbol": "CHF", "name": "Swiss Franc", "rate": 0.51},
            {"code": "AUD", "symbol": "$", "name": "Australian Dollar", "rate": 0.49},
            {"code": "NZD", "symbol": "$", "name": "New Zealand Dollar", "rate": 0.46},
            {"code": "CNY", "symbol": "¥", "name": "Chinese Yuan", "rate": 0.20},
            {"code": "TWD", "symbol": "NT$", "name": "New Taiwan Dollar", "rate": 0.045},
            {"code": "JPY", "symbol": "¥", "name": "Japanese Yen", "rate": 0.0091},
            {"code": "KRW", "symbol": "₩", "name": "South Korean Won", "rate": 0.00068},
            {"code": "HKD", "symbol": "$", "name": "Hong Kong Dollar", "rate": 0.11},
            {"code": "THB", "symbol": "฿", "name": "Thai Baht", "rate": 0.025},
            {"code": "PHP", "symbol": "₱", "name": "Philippine Peso", "rate": 0.017},
            {"code": "INR", "symbol": "₹", "name": "Indian Rupee", "rate": 0.012},
            {"code": "VND", "symbol": "₫", "name": "Vietnamese Dong", "rate": 0.00034},
            {"code": "IDR", "symbol": "Rp", "name": "Indonesian Rupiah", "rate": 0.00039},
            {"code": "SGD", "symbol": "$", "name": "Singapore Dollar", "rate": 0.27},
            {"code": "MYR", "symbol": "RM", "name": "Malaysian Ringgit", "rate": 0.27},
            {"code": "MXN", "symbol": "$", "name": "Mexican Peso", "rate": 0.18},
        ]

        from apps.currencies.models import Currency, ExchangeRate
        for curr in currencies_data:
            c, _ = Currency.objects.update_or_create(
                code=curr['code'],
                defaults={'name': curr['name'], 'symbol': curr['symbol'], 'is_base': (curr['code'] == 'CAD')}
            )
            # Seed Initial Rate
            ExchangeRate.objects.get_or_create(
                currency=c,
                date='2026-01-01',
                defaults={'rate_to_base': curr['rate']}
            )
        self.stdout.write(f"Seeded {len(currencies_data)} Currencies.")

        # 6. Users
        users_data = [
            {"username": "manager1", "role": "MANAGER", "email": "mgr@erp.com"},
            {"username": "accountant1", "role": "ACCOUNTANT", "email": "acc@erp.com"},
            {"username": "sales1", "role": "SALES", "email": "s1@erp.com"},
            {"username": "sales2", "role": "SALES", "email": "s2@erp.com"},
            {"username": "sales3", "role": "SALES", "email": "s3@erp.com"},
            {"username": "market1", "role": "MARKETING", "email": "mkt@erp.com"},
            {"username": "it_admin", "role": "IT_ADMIN", "email": "it@erp.com"},
        ]

        from apps.users.models import User
        from django.core.management import call_command

        for u_data in users_data:
            user, created = User.objects.update_or_create(
                username=u_data['username'],
                defaults={'role': u_data['role'], 'email': u_data['email'], 'is_active': True}
            )
            if created:
                user.set_password('pass123')
                user.save()
        self.stdout.write(f"Seeded {len(users_data)} Users.")

        # 7. Permissions
        self.stdout.write("Setting up Permissions...")
        call_command('setup_permissions')
