import logging
from apps.tours.models import Product, TourInstance
from apps.flights.models import Airline, Airport, Flight
from apps.clients.models import Client

logger = logging.getLogger(__name__)

def import_level_1(data: dict, diff_tracker: dict):
    """ Primary Dependents (Tour Instances, Flights, Clients) """
    
    # 1. Tour Instance
    ti_data = data.get('tour_instance')
    if ti_data:
        lookup = ti_data['lookup_key']
        fields = ti_data['fields']
        
        # Resolve product foreign key
        prod_lookup = fields.pop('product_lookup_key')
        product = Product.objects.get(**prod_lookup)
        fields['product'] = product
        
        TourInstance.objects.update_or_create(**lookup, defaults=fields)

    # 1.5 Travel Group
    inv_data = data.get('invoice', {})
    bk = inv_data.get('lookup_key', {}).get('booking_number', 'Unknown')
    created_at = inv_data.get('fields', {}).get('created_at', '')
    
    from apps.clients.models import TravelGroup
    tg_name = f"Booking {bk} Group"
    tg_notes = f"Clients traveling together. Booking: {bk}. Booking Date: {created_at}."
    
    travel_group, _ = TravelGroup.objects.update_or_create(
        name=tg_name,
        defaults={'notes': tg_notes}
    )

    # 2. Clients
    for client_block in data.get('clients', []):
        lookup = client_block['lookup_key']
        fields = client_block['fields']
        
        # Remove nested relational data from fields since update_or_create won't accept lists
        fields.pop('travel_documents', None)
        fields.pop('flight_tickets', None)
        fields.pop('health_plan', None)
        
        # Attach explicitly to the newly created Travel Group (Feedback Item 6)
        fields['travel_group'] = travel_group
        
        # update_or_create helps merge phone/email updates securely
        _, created = Client.objects.update_or_create(**lookup, defaults=fields)
        if created:
            diff_tracker["created"]["clients"] += 1
        else:
            diff_tracker["updated"]["clients"] += 1
            
    # 3. Base Flights
    # The parser gives us Airlines, Airports, and Flights individually
    for apt in data.get('airports', []):
        Airport.objects.update_or_create(**apt['lookup_key'], defaults=apt['fields'])
        
    for al in data.get('airlines', []):
        Airline.objects.update_or_create(**al['lookup_key'], defaults=al['fields'])
        
    for f in data.get('flights', []):
        lookup = f['lookup_key']
        fields = f['fields']
        
        try:
            airline = Airline.objects.get(code=lookup.get('airline_code'))
            dep_airport = Airport.objects.get(code=lookup.get('departure_airport_iata'))
            arr_airport = Airport.objects.get(code=lookup.get('arrival_airport_iata'))
            
            Flight.objects.update_or_create(
                airline=airline,
                flight_number=fields.get('flight_number'),
                defaults={
                    'departure_airport': dep_airport,
                    'arrival_airport': arr_airport
                }
            )
        except Exception as e:
            print(f"Skipped Flight creation for {lookup}: {e}")
