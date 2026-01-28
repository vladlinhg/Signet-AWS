import csv
import re
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from apps.clients.models import Client, Family, Address, PaymentMethod, TravelDocument
from apps.tours.models import Product, TourInstance, TourBooking
from apps.invoices.models import Invoice, InvoiceItem, InvoiceNote
from apps.users.models import User
from apps.currencies.models import Currency
from apps.flights.models import Flight, FlightTicket

class LegacyImporter:
    """
    Parses legacy booking CSV data and creates corresponding entities.
    Data format: BK#, Last/First Name, Tour Code/Name, Tour Arrival-Departure, Agency, Sales Rep, Status/Date
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
        self.agent = User.objects.filter(role='SALES').first()
        self.cad = Currency.objects.get(code='CAD') if Currency.objects.filter(code='CAD').exists() else None

    def _import_flights(self, client, flights_str):
        """
        Parses flight string: PNR: OQUZWX; Pick Up CX0986...
        Creates Flight and FlightTicket.
        """
        if not flights_str or not flights_str.strip():
            return

        # Extract PNR
        pnr_match = re.search(r'PNR:\s*([A-Z0-9]+)', flights_str)
        pnr = pnr_match.group(1) if pnr_match else ''

        # Extract Segments
        segments = re.split(r'[;\n]', flights_str)

        for seg in segments:
            seg = seg.strip()
            if not seg or 'PNR:' in seg: continue

            # Regex for segment details
            pattern = r'(?P<type>Pick Up|Send Off)?\s*(?P<code>[A-Z0-9]{2,3}\d+)\s+(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<org>[A-Z]{3})/(?P<dst>[A-Z]{3})\s+(?P<dept>\d{1,2}:\d{2}[AP]M)\s*-\s*(?P<arr>\d{1,2}:\d{2}[AP]M)'
            match = re.search(pattern, seg)
            if match:
                data = match.groupdict()

                # Parse Date/Time
                try:
                    date_obj = datetime.strptime(data['date'], '%m/%d/%Y').date()
                    dept_time = datetime.strptime(data['dept'], '%I:%M%p').time()
                    arr_time = datetime.strptime(data['arr'], '%I:%M%p').time()
                except ValueError:
                    continue

                # Parse Code
                flt_code = data['code']
                airline = flt_code[:2]
                number = flt_code[2:]

                # Create/Get Flight
                flight = Flight.objects.filter(
                    airline_code=airline,
                    flight_number=number,
                    departure_date=date_obj,
                    departure_airport=data['org']
                ).first()

                if not flight:
                    flight = Flight.objects.create(
                        airline_code=airline,
                        flight_number=number,
                        departure_date=date_obj,
                        departure_airport=data['org'],
                        arrival_airport=data['dst'],
                        departure_time=dept_time,
                        arrival_time=arr_time
                    )

                # Create Ticket
                if not FlightTicket.objects.filter(client=client, flight=flight).exists():
                    FlightTicket.objects.create(
                        client=client,
                        flight=flight,
                        pnr=pnr,
                        seat_number="TBA",
                        cabin_class='Economy'
                    )

    def parse_name(self, raw_name):
        """Lam/William -> last_name, first_name"""
        if '/' in raw_name:
            ln, fn = raw_name.split('/', 1)
            return ln.strip(), fn.strip()
        return raw_name.strip(), ''

    def parse_tour_code(self, raw_code):
        if '/' in raw_code:
            code, name = raw_code.split('/', 1)
            return code.strip(), name.strip()
        return raw_code.strip(), "Legacy Tour"

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

    def parse_dates(self, date_range_str):
        try:
            start_str, end_str = date_range_str.split('-')
            start = datetime.strptime(start_str.strip(), '%m/%d/%Y').date()
            end = datetime.strptime(end_str.strip(), '%m/%d/%Y').date()
            return start, end
        except:
            return None, None

    def import_csv(self, file_path):
        count = 0
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.process_row(row)
                count += 1
        return count

    def decode_tour_code(self, code):
        if len(code) < 8:
            return None, None
        try:
            yy = code[3:5]
            m_char = code[5]
            dd = code[6:8]
            year = 2000 + int(yy)
            if m_char.isdigit(): month = int(m_char)
            elif m_char.upper() == 'A': month = 10
            elif m_char.upper() == 'B': month = 11
            elif m_char.upper() == 'C': month = 12
            else: month = 1
            day = int(dd)
            start_date = datetime(year, month, day).date()
            end_date = start_date + timezone.timedelta(days=10)
            return start_date, end_date
        except:
            return None, None

    def search_match_candidate(self, first, last):
        return Client.objects.filter(first_name__iexact=first, last_name__iexact=last).first()

    def enrich_client(self, client, row):
        dob_str = row.get('DOB')
        if dob_str and not client.birth_date:
            try:
                client.birth_date = datetime.strptime(dob_str, '%m/%d/%Y').date()
            except: pass

        title = row.get('Title', '').upper()
        if not client.gender:
            if 'MR' in title: client.gender = 'M'
            elif 'MS' in title or 'MRS' in title: client.gender = 'F'

        email = row.get('Contact_Email')
        phone = row.get('Contact_Phone')
        if email and ('example.com' in client.email or not client.email):
            client.email = email
        if phone and (client.phone == '555-0000' or not client.phone):
            client.phone = phone
        client.save()

        ppt_num = row.get('Passport')
        if ppt_num:
            if not TravelDocument.objects.filter(client=client, doc_number=ppt_num).exists():
                exp_date = None
                if row.get('Passport_Exp'):
                    try:
                        exp_date = datetime.strptime(row.get('Passport_Exp'), '%m/%d/%Y').date()
                    except: pass
                TravelDocument.objects.create(
                    client=client,
                    doc_type='PASSPORT',
                    doc_number=ppt_num,
                    expiry_date=exp_date or timezone.now().date()
                )

    def process_row(self, row):
        # 0. Normalization
        if 'BK#' in row and not row.get('Invoice_No'):
            row['Invoice_No'] = row['BK#']
        if 'Last/First Name' in row and not row.get('Last_Name'):
             ln, fn = self.parse_name(row['Last/First Name'])
             row['Last_Name'] = ln
             row['First_Name'] = fn
        if 'Tour Code/Name' in row and not row.get('Tour_Code'):
             code, name = self.parse_tour_code(row['Tour Code/Name'])
             row['Tour_Code'] = code
        if 'Status/Date' in row and not row.get('Status_Date'):
             row['Status_Date'] = row['Status/Date']

        # 1. Parse Client
        last_name = row.get('Last_Name', '').strip()
        first_name = row.get('First_Name', '').strip()

        client = self.search_match_candidate(first_name, last_name)
        if not client:
             client = Client.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=f"{first_name.lower()}.{last_name.lower()}@legacy.com",
                phone='555-0000'
             )
             fam_name = f"The {last_name} Family"
             family = Family.objects.filter(name=fam_name).first()
             if not family: family = Family.objects.create(name=fam_name)
             client.family = family
             client.save()
             if not family.payment_methods.exists():
                 PaymentMethod.objects.create(family=family, method_type='CC', details='Legacy Import')

        self.enrich_client(client, row)

        # 2. Parse Tour & Dates
        tour_code = row.get('Tour_Code', '')
        start_date = None
        end_date = None
        if 'Tour Arrival-Departure' in row:
             start_date, end_date = self.parse_dates(row['Tour Arrival-Departure'])
        decoded_start, decoded_end = self.decode_tour_code(tour_code)
        if decoded_start:
            start_date = decoded_start
            if not end_date: end_date = decoded_end

        product, _ = Product.objects.get_or_create(
             unique_seq="LEG",
             defaults={'name': 'Legacy Imported Product', 'country_code': 'WLD', 'days_count': '10'}
        )

        lang_map = {'C': 'C', 'M': 'M', 'E': 'E'}
        lang_code = lang_map.get(row.get('Tour_Lang', 'M'), 'M')

        instance, _ = TourInstance.objects.get_or_create(
            instance_code=tour_code,
            defaults={
                'product': product,
                'start_date': start_date or timezone.now().date(),
                'end_date': end_date or timezone.now().date(),
                'total_spots': 50,
                'language': lang_code
            }
        )

        # 3. Create Booking
        inv_no = row.get('Invoice_No')
        booking_id = f"{tour_code}-{inv_no}-{client.pk}"
        room_type = row.get('Room_Type', '')
        price_val = Decimal(row.get('Price', '0') or '0')
        if price_val == 0 and 'BK#' in row:
             price_val = Decimal('2000.00')

        booking, _ = TourBooking.objects.get_or_create(
            booking_id=booking_id,
            defaults={
                'tour_instance': instance,
                'status': TourBooking.Status.BOOKED,
                'price': price_val,
                'room_type': room_type
            }
        )

        # 4. Create/Find Invoice
        status, date = self.parse_status_date(row.get('Status_Date', ''))
        invoice = Invoice.objects.filter(invoice_number=f"LEG-{inv_no}").first()
        if not invoice:
            payment_method = client.family.payment_methods.first()
            invoice = Invoice.objects.create(
                invoice_number=f"LEG-{inv_no}",
                payment_method=payment_method,
                sales_agent=self.agent,
                status=status,
                total_amount=0,
                currency=self.cad,
                created_at=date
            )
            Invoice.objects.filter(pk=invoice.pk).update(created_at=date)

        if not InvoiceItem.objects.filter(invoice=invoice, tour_booking=booking).exists():
            # Create items
            # Consolidate Price. If Price=0, use 2000.
            # If Multi-pax (items>0), check if we should add another?
            # Design: One item per passenger.

            meals = row.get('Meals', '')
            tour_desc = row.get('Tour_Description', '').strip()
            item_desc = f"{tour_code} - {tour_desc} - {room_type} ({meals})" if tour_desc else f"{tour_code} - {room_type} ({meals})"

            InvoiceItem.objects.create(
                invoice=invoice,
                client=client,
                description=item_desc,
                quantity=1,
                unit_price=price_val,
                tour_booking=booking
            )
            invoice.update_total()

        # 5. Process Extras
        disc_amt = Decimal(row.get('Discount_Amount', '0') or '0')
        if disc_amt > 0:
            if not InvoiceItem.objects.filter(invoice=invoice, description="Concession/Discount", unit_price=-disc_amt).exists():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    client=client,
                    description="Concession/Discount",
                    quantity=1,
                    unit_price=-disc_amt,
                    tour_booking=None
                )
                invoice.update_total()

        pay_amt = Decimal(row.get('Payment_Amount', '0') or '0')
        if pay_amt == 0 and status == Invoice.Status.PAID:
            pay_amt = invoice.total_amount

        if pay_amt > 0:
            if pay_amt > invoice.amount_paid:
                invoice.amount_paid = pay_amt
                invoice.save(update_fields=['amount_paid'])

            pay_type = row.get('Payment_Type')
            if pay_type and not InvoiceNote.objects.filter(invoice=invoice, content__contains=f"Payment Method: {pay_type}").exists():
                 InvoiceNote.objects.create(
                     invoice=invoice,
                     author=self.agent,
                     content=f"Payment Method: {pay_type}"
                 )

        # 6. Process Flights
        self._import_flights(client, row.get('Flights'))
