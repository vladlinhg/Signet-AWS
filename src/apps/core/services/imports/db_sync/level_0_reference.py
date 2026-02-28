import logging
from django.contrib.auth import get_user_model
from apps.tours.models import Product
from apps.flights.models import Airline, Airport

logger = logging.getLogger(__name__)

def import_level_0(data: dict):
    """ Independent Reference Data (Users, Airlines, Airports, Products) """
    User = get_user_model()
    
    # 1. Users (Sales Agent)
    sales_username = data.get('invoice', {}).get('fields', {}).get('sales_user_username')
    if sales_username:
        user, created = User.objects.get_or_create(username=sales_username)
        if created:
            user.is_active = False # newly created via system, wait for manual activation
            user.save()

    # 1b. Users (Authors from Logs)
    for note in data.get('invoice_notes', []):
        author_data = note.get('author')
        if author_data:
            uname = author_data['lookup_key']['username']
            user, created = User.objects.get_or_create(username=uname)
            if created:
                user.is_active = False
                user.save()

    # 2. Product
    product_data = data.get('product')
    if product_data:
        lookup = product_data['lookup_key']
        fields = product_data['fields']
        Product.objects.update_or_create(**lookup, defaults=fields)

    # 3. Airlines
    for airline in data.get('airlines', []):
        lookup = airline['lookup_key']
        fields = airline['fields']
        Airline.objects.update_or_create(**lookup, defaults=fields)

    # 4. Airports
    for airport in data.get('airports', []):
        lookup = airport['lookup_key']
        fields = airport['fields']
        Airport.objects.update_or_create(**lookup, defaults=fields)
