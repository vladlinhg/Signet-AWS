import logging
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from apps.tours.models import TourBooking
from apps.flights.models import FlightInstance, FlightTicket
from apps.clients.models import Client, TravelDocument
from apps.invoices.models import Invoice, InvoiceItem, InvoicePayment, InvoiceNote
from apps.documents.models import SupportingDocument

logger = logging.getLogger(__name__)

def import_level_3(data: dict, diff_tracker: dict, file_bytes: bytes = None, filename: str = None):
    """ Tertiary Glue (Tickets, Docs, InvoiceItems) """
    
    # We need the root invoice to attach ledger items to
    inv_data = data.get('invoice')
    if not inv_data:
        return
    invoice = Invoice.objects.get(**inv_data['lookup_key'])
    
    # 1. Travel Documents & Flight Tickets
    for client_block in data.get('clients', []):
        client = Client.objects.get(**client_block['lookup_key'])
        
        # Documents (Passports)
        for doc in client_block.get('travel_documents', []):
            TravelDocument.objects.update_or_create(
                client=client, 
                doc_number=doc['doc_number'], 
                defaults=doc
            )
            
        # Flight Tickets
        for ticket_block in client_block.get('flight_tickets', []):
            
            flt_inst_data = ticket_block.pop('flight_instance_lookup', None)
            ticket_block.pop('client_lookup', None) # Removing meta-dictionary so Django ORM doesn't crash
            if flt_inst_data:
                flt_inst = FlightInstance.objects.get(**flt_inst_data)
                ticket_block['flight'] = flt_inst
            ticket_block['client'] = client
            
            ticket_code = ticket_block.get('ticket_code')
            if ticket_code:
                FlightTicket.objects.update_or_create(
                    ticket_code=ticket_code,
                    defaults=ticket_block
                )

    # 2. Rebuild the Ledger
    # To prevent phantom elements from PDF amendments, we destroy the old layout
    deleted_items = InvoiceItem.objects.filter(invoice=invoice).delete()[0]
    deleted_pmts = InvoicePayment.objects.filter(invoice=invoice).delete()[0]
    InvoiceNote.objects.filter(invoice=invoice).delete() # Logs can be rebuilt safely
    
    diff_tracker["deleted"]["items"] += deleted_items
    diff_tracker["deleted"]["payments"] += deleted_pmts

    # A. Invoice Items
    for item_data in data.get('invoice_items', []):
        fields = item_data['fields']
        fields['invoice'] = invoice
        if 'currency' in fields:
            fields.pop('currency')
        
        # Resolve Lookups
        tb_lookup = item_data.get('tour_booking_lookup')
        if tb_lookup:
            fields['tour_booking'] = TourBooking.objects.filter(**tb_lookup).first()
            
        ft_lookup = item_data.get('flight_ticket_lookup')
        if ft_lookup:
            fields['flight_ticket'] = FlightTicket.objects.filter(**ft_lookup).first()
            
        meta_client = item_data.get('meta', {}).get('client_lookup')
        if meta_client:
            fields['client'] = Client.objects.filter(**meta_client).first()
            
        meta_cat = item_data.get('meta', {}).get('category')
        if meta_cat == 'discount':
            from apps.invoices.models import Coupon
            import uuid
            c_code = f"DISC-{uuid.uuid4().hex[:6].upper()}"
            coupon_amt = abs(fields.get('unit_price', 0))
            coupon, _ = Coupon.objects.update_or_create(
                code=c_code,
                defaults={
                    'coupon_type': Coupon.Type.DISCOUNT,
                    'amount': coupon_amt,
                    'status': Coupon.Status.USED,
                    'invoice_used': invoice
                }
            )
            fields['coupon'] = coupon
            
        InvoiceItem.objects.create(**fields)
        diff_tracker["created"]["items"] += 1

    # B. Payments
    for pmt in data.get('payments', []):
        fields = pmt['fields']
        fields['invoice'] = invoice
        
        if 'type' in fields:
            fields['payment_type'] = fields.pop('type')
        if 'currency' in fields:
            fields.pop('currency')
            
        description_notes = pmt.get('meta', {}).get('remark', '')
        fields['description'] = description_notes
        InvoicePayment.objects.create(**fields)
        
    # C. Invoice Notes (Logs)
    for note in data.get('invoice_notes', []):
        fields = note['fields']
        fields['invoice'] = invoice
        
        author_data = note.get('author')
        if author_data:
            uname = author_data['lookup_key']['username']
            fields['author'] = get_user_model().objects.get(username=uname)
            
        InvoiceNote.objects.create(**fields)
        
    # 3. Create Supporting Document (If file provided)
    if file_bytes and filename:
        clean_inv_no = invoice.booking_number
        upload_dt = now().strftime('%Y%m%d%H%M')
        title = f"EIP-{clean_inv_no}-{upload_dt}"
        ext = filename.split('.')[-1]
        sys_file_name = f"{title}.{ext}"
        
        # The User invoking this sync should be tracked here
        uploader = "System"
        user_data = inv_data.get('fields', {}).get('sales_user_username')
        if user_data:
             uploader = user_data
             
        desc = f"Invoice {clean_inv_no} uploaded by {uploader} at {now().isoformat()}"
        
        f_content = ContentFile(file_bytes, name=sys_file_name)
        
        sup_doc, created = SupportingDocument.objects.update_or_create(
            title=title,
            defaults={
                'description': desc,
                'file': f_content
            }
        )
        
        # Attach to invoice M2M
        invoice.supporting_documents.add(sup_doc)
        diff_tracker["updated"]["invoices"] += 1
