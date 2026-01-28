import csv
import re
from datetime import datetime, time
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from apps.clients.models import Client, Family, PaymentMethod, TravelDocument, City, Ethnicity
from apps.tours.models import Product, TourInstance, TourBooking
from apps.invoices.models import Invoice, InvoiceItem, InvoiceNote
from apps.users.models import User
from apps.currencies.models import Currency
from apps.flights.models import Flight, FlightInstance, FlightTicket, Airline, Airport

class LegacyImporter:
    """
    Parses legacy booking CSV data.
    Supports two modes:
    1. preview(file): Returns parsed objects with conflict comparison.
    2. execute(row_data, action): Saves data based on user decision.
    """

    STATUS_MAP = {
        'Draft': Invoice.Status.DRAFT,
        'Deposited': Invoice.Status.DEPOSIT,
        'Invoiced': Invoice.Status.INVOICED,
        'Paid in Full': Invoice.Status.PAID,
        'Cancelled': Invoice.Status.CANCELLED,
        'Total Move': Invoice.Status.MOVED,
        'Split': Invoice.Status.SPLIT,
        'Penalty Completed': Invoice.Status.PENALTY
    }

    def __init__(self):
        # Cache common entities to reduce queries
        self.agent = User.objects.filter(role='SALES').first()
        if not self.agent:
            self.agent = User.objects.filter(is_superuser=True).first()
        self.cad = Currency.objects.filter(code='CAD').first()

    # --- Parsing Helpers ---

    def parse_name(self, raw_name):
        """Lam/William -> last_name, first_name"""
        if '/' in raw_name:
            ln, fn = raw_name.split('/', 1)
            return ln.strip(), fn.strip()
        return raw_name.strip(), ''

    def parse_tour_code(self, raw_code):
        """
        Input: JPN26206H4
        Product Code: JPN + H4 = JPNH4
        Instance Code: JPN26206H4
        """
        raw = raw_code.strip()
        if len(raw) < 5:
            return raw, raw # Fallback

        # Heuristic: First 3 + Last 2
        product_code = (raw[:3] + raw[-2:]).upper()
        return product_code, raw

    def parse_dates_from_code(self, code):
        """
        JPN26206H4 -> YY=26, M=?, DD=06
        """
        if len(code) < 8: return None, None
        try:
            yy = int(code[3:5])
            year = 2000 + yy
            m_char = code[5]
            if m_char.isdigit(): month = int(m_char)
            elif m_char.upper() == 'A': month = 10
            elif m_char.upper() == 'B': month = 11
            elif m_char.upper() == 'C': month = 12
            else: month = 1
            day = int(code[6:8])
            start = datetime(year, month, day).date()
            end = start + timezone.timedelta(days=10) # Default duration
            return start, end
        except:
            return None, None

    def parse_status_date(self, raw_str):
        match = re.search(r'(\d{2}/\d{2}/\d{4})$', raw_str)
        if match:
            date_str = match.group(1)
            status_part = raw_str.replace(date_str, '').strip()
            try:
                date = datetime.strptime(date_str, '%m/%d/%Y').date()
            except ValueError:
                date = timezone.now().date()
            status = self.STATUS_MAP.get(status_part, Invoice.Status.DRAFT)
            return status, date
        return Invoice.Status.DRAFT, timezone.now().date()

    # --- Core Logic: Flight ---

    def _get_or_create_flight(self, flight_str):
        """
        Parses: Pick Up CX0986 03/13/2030 YVR/HKG 01:00AM - 07:00AM
        Returns: FlightInstance object (saved)
        """
        if not flight_str: return None

        # Regex
        pattern = r'(?P<code>[A-Z0-9]{2}\d+)\s+(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<org>[A-Z]{3})/(?P<dst>[A-Z]{3})\s+(?P<dept>\d{1,2}:\d{2}[AP]M)\s*-\s*(?P<arr>\d{1,2}:\d{2}[AP]M)'
        match = re.search(pattern, flight_str)
        if not match: return None

        data = match.groupdict()
        full_code = data['code'] # CX0986
        airline_code = full_code[:2] # CX
        flight_num = full_code[2:]   # 0986

        try:
            date_obj = datetime.strptime(data['date'], '%m/%d/%Y').date()
            dept_time = datetime.strptime(data['dept'], '%I:%M%p').time()
            arr_time = datetime.strptime(data['arr'], '%I:%M%p').time()
        except:
            return None

        # 1. Airline
        airline, _ = Airline.objects.get_or_create(
            code=airline_code,
            defaults={'name': f"Airline {airline_code}"}
        )

        # 2b. Airports
        dep_airport, _ = Airport.objects.get_or_create(
            code=data['org'],
            defaults={'name': f"Airport {data['org']}"}
        )
        arr_airport, _ = Airport.objects.get_or_create(
            code=data['dst'],
            defaults={'name': f"Airport {data['dst']}"}
        )

        # 2. Flight (Route)
        flight_route, _ = Flight.objects.get_or_create(
            airline=airline,
            flight_number=flight_num,
            departure_airport=dep_airport,
            arrival_airport=arr_airport
        )

        # 3. Flight Instance
        instance, _ = FlightInstance.objects.get_or_create(
            flight=flight_route,
            departure_date=date_obj,
            defaults={
                'departure_time': dept_time,
                'arrival_time': arr_time
            }
        )
        return instance

    # --- Mode 1: Preview ---

    def preview(self, csv_file):
        """
        Parses CSV and returns list of dicts:
        {
            'status': 'NEW' | 'MATCH_FOUND',
            'data': raw_row_dict,
            'conflicts': { 'email': {'old': '...', 'new': '...'} }
        }
        """
        results = []
        decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file)

        for row in reader:
            # Normalize keys
            ln, fn = self.parse_name(row.get('Last/First Name', '') or f"{row.get('Last_Name')}/{row.get('First_Name')}")
            row['Last_Name'] = ln
            row['First_Name'] = fn

            # Check Match
            existing = Client.objects.filter(last_name__iexact=ln, first_name__iexact=fn).first()

            item = {
                'status': 'MATCH_FOUND' if existing else 'NEW',
                'data': row,
                'conflicts': {}
            }

            if existing:
                # Detect Conflicts for UI
                new_email = row.get('Contact_Email')
                if new_email and existing.email and new_email.lower() != existing.email.lower():
                    item['conflicts']['email'] = {'old': existing.email, 'new': new_email}

                new_phone = row.get('Contact_Phone')
                if new_phone and existing.phone and new_phone != existing.phone:
                    item['conflicts']['phone'] = {'old': existing.phone, 'new': new_phone}

            results.append(item)

        return results

    # --- Mode 2: Execute ---

    def execute(self, row, action='MERGE'):
        """
        action: 'MERGE', 'OVERWRITE', 'NEW', 'SKIP'
        """
        if action == 'SKIP': return

        # 1. Handle Client
        ln = row['Last_Name']
        fn = row['First_Name']

        client = None
        if action != 'NEW':
            client = Client.objects.filter(last_name__iexact=ln, first_name__iexact=fn).first()

        if not client:
            # Create NEW
            client = Client.objects.create(
                first_name=fn,
                last_name=ln
            )
            # Family
            fam_name = f"The {ln} Family"
            fam, _ = Family.objects.get_or_create(name=fam_name)
            client.family = fam
            client.save()
            if not fam.payment_methods.exists():
                PaymentMethod.objects.create(family=fam, method_type='CC', details='Legacy Import')

        # Apply Data (Merge vs Overwrite)
        self._apply_client_data(client, row, overwrite=(action=='OVERWRITE'))

        # 2. Product & Tour
        prod_code, inst_code = self.parse_tour_code(row.get('Tour Code/Name') or row.get('Tour_Code', ''))

        # Split JPNH4 -> JPN + H4 (as requested)
        cntry = prod_code[:3]
        seq = prod_code[3:]

        product, _ = Product.objects.get_or_create(
            unique_seq=seq,
            country_code=cntry,
            defaults={'name': f"Imported {prod_code}", 'days_count': '10'}
        )

        # Update Description
        tour_desc = row.get('Tour_Description', '').strip()
        if tour_desc:
             product.description = tour_desc
             product.save(update_fields=['description'])

        start, end = self.parse_dates_from_code(inst_code)

        tour_instance, _ = TourInstance.objects.get_or_create(
            instance_code=inst_code,
            defaults={
                'product': product,
                'start_date': start or timezone.now().date(),
                'end_date': end or timezone.now().date(),
                'language': row.get('Tour_Lang', 'M'),
                'total_spots': 40
            }
        )

        # 3. Invoice & Booking
        inv_num = row.get('Invoice_No') or row.get('BK#')
        # Keep original number, check duplicate?
        # Assuming unique for now or getting existing
        invoice, created_inv = Invoice.objects.get_or_create(
            invoice_number=str(inv_num),
            defaults={
                 'sales_agent': self.agent,
                 'currency': self.cad,
                 'status': Invoice.Status.DRAFT
            }
        )

        if created_inv:
             status, date = self.parse_status_date(row.get('Status_Date') or row.get('Status/Date', ''))
             invoice.status = status
             invoice.created_at = date
             invoice.save()

        # Booking
        booking_id = f"{inst_code}-{inv_num}-{client.pk}"
        price_val = Decimal(row.get('Price', '0') or '0')

        booking, _ = TourBooking.objects.get_or_create(
            booking_id=booking_id,
            defaults={
                'tour_instance': tour_instance,
                'status': TourBooking.Status.BOOKED,
                'room_type': row.get('Room_Type', 'Twin'),
                'price': price_val
            }
        )
        # Note: If TourBooking model doesn't have 'client', we rely on InvoiceItem.
        # But logically Booking IS for a client.
        # I'll enable 'client' in defaults, assuming schema supports it.

        # 4. Invoice Items
        if not InvoiceItem.objects.filter(invoice=invoice, description__contains=inst_code, client=client).exists():
            price = Decimal(row.get('Price', '0') or '0')
            desc = f"{inst_code} - {product.name}"

            meals = row.get('Meals')
            if meals: desc += f" ({meals})"

            InvoiceItem.objects.create(
                invoice=invoice,
                client=client,
                tour_booking=booking,
                description=desc,
                quantity=1,
                unit_price=price
            )

        # 5. Extras (Discount)
        disc = Decimal(row.get('Discount_Amount', '0') or '0')
        if disc > 0 and not InvoiceItem.objects.filter(invoice=invoice, unit_price=-disc).exists():
             InvoiceItem.objects.create(
                invoice=invoice,
                client=client,
                description="Concession/Discount",
                quantity=1,
                unit_price=-disc
            )

        # 6. Flights
        flt_str = row.get('Flights')
        flight_inst = self._get_or_create_flight(flt_str)
        if flight_inst:
            if not FlightTicket.objects.filter(client=client, flight=flight_inst).exists():
                FlightTicket.objects.create(
                    client=client,
                    flight=flight_inst,
                    ticket_code=f"TKT-{inv_num}-{client.pk}", # Renamed from ticket_number
                    # status='CONFIRMED', # Removed: Field does not exist
                    cabin_class='Economy'
                )

        # Updates
        invoice.update_total()
        pd = Decimal(row.get('Payment_Amount', '0') or '0')
        if pd > 0:
            invoice.amount_paid = pd
            invoice.save()


    def _apply_client_data(self, client, row, overwrite=False):
        # Helper to set field if empty OR overwrite is True
        def set_val(attr, val):
            if not val: return
            curr = getattr(client, attr)
            if not curr or overwrite:
                setattr(client, attr, val)

        set_val('email', row.get('Contact_Email'))
        set_val('phone', row.get('Contact_Phone'))

        # Gender
        title = row.get('Title', '').upper()
        if 'MR' in title: set_val('gender', 'M')
        elif 'MS' in title or 'MRS' in title: set_val('gender', 'F')

        # DOB
        dob = row.get('DOB')
        if dob:
            try:
                date = datetime.strptime(dob, '%m/%d/%Y').date()
                if not client.birth_date or overwrite:
                    client.birth_date = date
            except: pass

        # Dietary
        meals = row.get('Meals')
        if meals and meals not in ['N/A', '']:
             if not client.dietary_restrictions or overwrite:
                 client.dietary_restrictions = meals

        client.save()

        # Passport (Always Add if new)
        ppt = row.get('Passport')
        if ppt and not TravelDocument.objects.filter(client=client, doc_number=ppt).exists():
            exp = None
            if row.get('Passport_Exp'):
                try: exp = datetime.strptime(row.get('Passport_Exp'), '%m/%d/%Y').date()
                except: pass

            TravelDocument.objects.create(
                client=client,
                doc_type='PASSPORT',
                doc_number=ppt,
                expiry_date=exp or timezone.now().date()
            )
