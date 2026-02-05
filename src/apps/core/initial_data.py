from django.utils.translation import gettext_lazy as _

# Users Configuration
# Roles: SALES, MANAGER, ACCOUNTANT, MARKETING, IT_ADMIN
DEFAULT_PASSWORD = "pass123"

USERS = [
    # Admin
    {"username": "it_admin", "email": "it@erp.com", "role": "IT_ADMIN", "password": DEFAULT_PASSWORD, "is_superuser": True},

    # Management
    {"username": "manager1", "email": "mgr@erp.com", "role": "MANAGER", "password": DEFAULT_PASSWORD},

    # Accounts
    {"username": "accountant1", "email": "acc@erp.com", "role": "ACCOUNTANT", "password": DEFAULT_PASSWORD},

    # Sales
    {"username": "sales1", "email": "s1@erp.com", "role": "SALES", "password": DEFAULT_PASSWORD},
    {"username": "sales2", "email": "s2@erp.com", "role": "SALES", "password": DEFAULT_PASSWORD},
    {"username": "sales3", "email": "s3@erp.com", "role": "SALES", "password": DEFAULT_PASSWORD},

    # Marketing
    {"username": "market1", "email": "mkt@erp.com", "role": "MARKETING", "password": DEFAULT_PASSWORD},
]

# Currencies
CURRENCIES = [
    {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$", "is_base": True},
    {"code": "USD", "name": "US Dollar", "symbol": "$", "rate": 1.35},
    {"code": "EUR", "name": "Euro", "symbol": "€", "rate": 1.50},
    {"code": "GBP", "name": "British Pound", "symbol": "£", "rate": 1.70},
    {"code": "JPY", "name": "Japanese Yen", "symbol": "¥", "rate": 0.009},
    {"code": "CNY", "name": "Chinese Yuan", "symbol": "¥", "rate": 0.19},
]

# Cities (Common Origins/Destinations)
CITIES = [
    {"name": "Vancouver", "country_code": "CAN"},
    {"name": "Toronto", "country_code": "CAN"},
    {"name": "Montreal", "country_code": "CAN"},
    {"name": "New York", "country_code": "USA"},
    {"name": "Los Angeles", "country_code": "USA"},
    {"name": "San Francisco", "country_code": "USA"},
    {"name": "London", "country_code": "GBR"},
    {"name": "Paris", "country_code": "FRA"},
    {"name": "Tokyo", "country_code": "JPN"},
    {"name": "Hong Kong", "country_code": "HKG"},
    {"name": "Shanghai", "country_code": "CHN"},
    {"name": "Beijing", "country_code": "CHN"},
    {"name": "Taipei", "country_code": "TWN"},
    {"name": "Sydney", "country_code": "AUS"},
]

# Ethnicities
ETHNICITIES = [
    "Caucasian",
    "Asian",
    "Black/African",
    "Hispanic/Latino",
    "Middle Eastern",
    "Indigenous",
    "Pacific Islander",
    "South Asian",
    "Southeast Asian",
    "Mixed",
    "Other",
]

AIRLINES = [
    {'code': 'AC', 'name': 'Air Canada'},
    {'code': 'WS', 'name': 'WestJet'},
    {'code': 'DL', 'name': 'Delta Airlines'},
    {'code': 'CX', 'name': 'Cathay Pacific'},
    {'code': 'UA', 'name': 'United Airlines'},
]

AIRPORTS = [
    {'code': 'YVR', 'name': 'Vancouver Intl'},
    {'code': 'YYZ', 'name': 'Toronto Pearson'},
    {'code': 'LHR', 'name': 'London Heathrow'},
    {'code': 'HKG', 'name': 'Hong Kong Intl'},
    {'code': 'NRT', 'name': 'Narita Intl'},
    {'code': 'LAX', 'name': 'Los Angeles Intl'},
]
