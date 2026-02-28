import logging
from apps.invoices.models import Invoice
from apps.clients.models import Client

logger = logging.getLogger(__name__)

def generate_payload_diff(data: dict) -> list:
    """
    Takes the normalized dictionary payload and compares it to the Database.
    Returns a list of 'blocks' ready for the interactive HTML diff view.
    """
    diff_blocks = []
    
    # 1. Invoice Block
    inv_lookup = data.get('invoice', {}).get('lookup_key', {})
    inv_fields = data.get('invoice', {}).get('fields', {})
    if inv_lookup:
        booking_no = inv_lookup.get('booking_number')
        block = {
            'entity_type': 'Booking Invoice',
            'identifier': booking_no,
            'data': inv_fields,
            'status': 'NEW',
            'conflicts': {}
        }
        
        existing = Invoice.objects.filter(**inv_lookup).first()
        if existing:
            block['status'] = 'MATCH_FOUND'
            
            # Simple field compare (e.g sales_user_username vs existing.sales_user.username)
            # Not fully deep because of foreign keys, but enough for basic discrepancy tracking.
            if existing.grand_total and 'grand_total' in inv_fields:
                if str(existing.grand_total) != str(inv_fields['grand_total']):
                    block['conflicts']['Grand Total'] = {'old': str(existing.grand_total), 'new': str(inv_fields['grand_total'])}
                    
        diff_blocks.append(block)
        
    # 2. Clients
    for client in data.get('clients', []):
        lookup = client.get('lookup_key', {})
        fields = client.get('fields', {})
        name = lookup.get('name')
        
        block = {
            'entity_type': 'Client / Passenger',
            'identifier': name,
            'data': fields,
            'status': 'NEW',
            'conflicts': {}
        }
        
        existing = Client.objects.filter(**lookup).first()
        if existing:
            block['status'] = 'MATCH_FOUND'
            if existing.phone and 'phone' in fields and existing.phone != fields['phone']:
                block['conflicts']['Phone'] = {'old': existing.phone, 'new': fields['phone']}
            if existing.email and 'email' in fields and existing.email != fields['email']:
                block['conflicts']['Email'] = {'old': existing.email, 'new': fields['email']}
                
        diff_blocks.append(block)
        
    # Extensible to Flights, Items, etc by the user later via the same pattern.
    return diff_blocks
