import logging
from django.contrib.auth import get_user_model
from apps.tours.models import TourInstance, TourBooking
from apps.flights.models import Flight, FlightInstance
from apps.invoices.models import Invoice

logger = logging.getLogger(__name__)

def import_level_2(data: dict, diff_tracker: dict):
    """ Secondary Dependents (Flight Instances, Tour Bookings, Invoices) """
    
    # 1. Flight Instances
    for client_block in data.get('clients', []):
        for ticket in client_block.get('flight_tickets', []):
            flt_inst_data = ticket.get('flight_instance_lookup')
            if flt_inst_data:
                code = flt_inst_data.get('flight_code')
                dep_date = flt_inst_data.get('departure_date')
                if code:
                    num = code.split('-')[0][2:] 
                    try:
                        flight = Flight.objects.get(flight_number=num)
                        FlightInstance.objects.update_or_create(
                            flight_code=code,
                            defaults={
                                'flight': flight,
                                'departure_date': dep_date
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to link FlightInstance {code}: {e}")

    # 2. Tour Bookings
    for tb_block in data.get('tour_bookings', []):
        lookup = tb_block['lookup_key']
        fields = tb_block['fields']
        
        # Resolve TourInstance
        ti_lookup = fields.pop('tour_instance_lookup')
        try:
            ti = TourInstance.objects.get(**ti_lookup)
            fields['tour_instance'] = ti
            
            _, created = TourBooking.objects.update_or_create(**lookup, defaults=fields)
            if created:
                diff_tracker["created"]["tour_bookings"] += 1
            else:
                diff_tracker["updated"]["tour_bookings"] += 1
        except Exception as e:
            logger.warning(f"Failed to link TourBooking {lookup}: {e}")

    # 3. Invoice (The Core Ledger)
    inv_data = data.get('invoice')
    if inv_data:
        lookup = inv_data['lookup_key']
        fields = inv_data['fields']
        
        # Resolve Sales Agent User 
        sales_username = fields.pop('sales_user_username', None)
        if sales_username:
            sales_user = get_user_model().objects.filter(username=sales_username).first()
            if sales_user:
                fields['sales_agent'] = sales_user
                
        # Resolve Currency
        currency_code = fields.pop('currency', None)
        if currency_code:
            from apps.currencies.models import Currency
            currency_obj, _ = Currency.objects.get_or_create(code=currency_code)
            fields['currency'] = currency_obj
                
        _, created = Invoice.objects.update_or_create(**lookup, defaults=fields)
        if created:
            diff_tracker["created"]["invoices"] += 1
        else:
            diff_tracker["updated"]["invoices"] += 1
