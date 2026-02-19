import logging
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.clients.models import Client
from apps.tours.models import TourInstance, TourBooking, Product
from apps.invoices.models import Invoice, InvoiceItem, InvoicePayment, Coupon
from apps.flights.models import Flight, FlightInstance, FlightTicket, Airport, Airline

logger = logging.getLogger(__name__)
User = get_user_model()

class BookingImporterService:
    """
    Takes parsed data dict from PDFParserService and creates/updates Django entities.
    """

    def __init__(self, parsed_data, user=None):
        self.data = parsed_data
        self.user = user  # The user performing the import

    @transaction.atomic
    def import_booking(self):
        """
        Main execution method.
        """
        header = self.data.get('header', {})
        passengers = self.data.get('passengers', [])
        flights = self.data.get('flights', [])
        financials = self.data.get('financials', {})

        booking_number = header.get('booking_number')
        if not booking_number:
            raise ValueError("No Booking Number found in header.")

        # 1. Resolve Agent
        agent_username = header.get('agent_username')
        sales_agent = self.user
        if agent_username:
            try:
                # Try to find agent by matching username loosely
                sales_agent = User.objects.filter(username__icontains=agent_username).first() or self.user
            except Exception:
                pass

        # 2. Get/Create Invoice (The Hub)
        # Fixed: Use 'created_at' instead of 'invoice_date'
        invoice, created = Invoice.objects.get_or_create(
            booking_number=booking_number,
            defaults={
                'sales_agent': sales_agent,
                'status': Invoice.Status.DRAFT,
                'created_at': datetime.now()
            }
        )

        # 3. Handle Passengers (Clients)
        client_objects = []
        for p_data in passengers:
            client = self._get_or_create_client(p_data)
            client_objects.append(client)

            # Future: Link Client to Invoice Items

        # 4. Handle Tour
        tour_code = header.get('tour_code')
        tour_instance = None
        if tour_code:
            tour_instance = self._get_or_create_tour(tour_code)

            # Create TourBooking record
            TourBooking.objects.get_or_create(
                invoice=invoice,
                tour_instance=tour_instance,
                defaults={
                    'status': 'CONFIRMED'
                }
            )

        # 5. Handle Flights
        for f_data in flights:
            flight_inst = self._get_or_create_flight(f_data)

            # Create Tickets for each passenger
            for client in client_objects:
                FlightTicket.objects.get_or_create(
                    flight=flight_inst,
                    client=client,
                    defaults={
                        'pnr': f_data.get('pnr', ''),
                        'ticket_code': f"{flight_inst.flight_code}-{client.id}" # Temp unique
                    }
                )

        # 6. Handle Financials
        # Payments
        for pay in financials.get('payments', []):
            # Create InvoicePayment
            raw_type = pay.get('type', 'Deposit').upper()
            if 'BALANCE' in raw_type:
                p_type = InvoicePayment.PaymentType.BALANCE
            else:
                p_type = InvoicePayment.PaymentType.DEPOSIT

            # Fixed: Use 'date' instead of 'payment_date'
            InvoicePayment.objects.get_or_create(
                invoice=invoice,
                amount=pay['amount'],
                defaults={
                    'date': datetime.now().date(),
                    'payment_type': p_type,
                    'description': f"Imported Payment: {pay.get('raw_line', '')}"
                }
            )

        # Coupons
        for coupon_data in financials.get('coupons', []):
            code = coupon_data.get('code')
            amount = coupon_data.get('amount')
            if code:
                c, _ = Coupon.objects.get_or_create(
                    code=code,
                    defaults={
                        'amount': amount,
                        'status': Coupon.Status.USED
                    }
                )
                c.invoice_used = invoice
                c.save()

        return invoice

    def _get_or_create_client(self, p_data):
        # Fuzzy match by Name + DOB
        name = p_data.get('name', '')
        parts = name.split(',')
        last_name = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else "Unknown"

        dob_str = p_data.get('dob')
        birth_date = None
        if dob_str:
            try:
                birth_date = datetime.strptime(dob_str, "%b %d %Y").date()
            except ValueError:
                pass

        qs = Client.objects.filter(last_name__iexact=last_name, first_name__iexact=first_name)
        if birth_date:
            qs = qs.filter(birth_date=birth_date)

        client = qs.first()
        if not client:
            gender_map = {'Mr': 'M', 'Mrs': 'F', 'Ms': 'F', 'Miss': 'F'}
            gender = gender_map.get(p_data.get('title'), 'X')

            client = Client.objects.create(
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                gender=gender,
                passport_number=p_data.get('passport', '')
            )
        return client

    def _get_or_create_tour(self, tour_code):
        tour = TourInstance.objects.filter(tour_code=tour_code).first()
        if not tour:
            country_code = tour_code[:3]
            product, _ = Product.objects.get_or_create(
                country_code=country_code,
                unique_seq="01",
                defaults={'name': f"Auto-Imported {country_code} Tour"}
            )
            tour = TourInstance.objects.create(
                product=product,
                tour_code=tour_code,
            )
        return tour

    def _get_or_create_flight(self, f_data):
        code = f_data.get('code')
        date_str = f_data.get('date')

        dep_date = None
        if date_str:
            try:
                dep_date = datetime.strptime(date_str, "%m/%d/%Y").date()
            except:
                pass

        airline_code = code[:2]
        flight_num = code[2:]

        airline, _ = Airline.objects.get_or_create(code=airline_code, defaults={'name': airline_code})

        route = f_data.get('route', '')
        dep_code, arr_code = "XXX", "XXX"
        if '/' in route:
            dep_code, arr_code = route.split('/')

        dep_airport, _ = Airport.objects.get_or_create(code=dep_code)
        arr_airport, _ = Airport.objects.get_or_create(code=arr_code)

        flight_def, _ = Flight.objects.get_or_create(
            airline=airline,
            flight_number=flight_num,
            defaults={
                'departure_airport': dep_airport,
                'arrival_airport': arr_airport
            }
        )

        instance, _ = FlightInstance.objects.get_or_create(
            flight=flight_def,
            departure_date=dep_date,
            defaults={
                'flight_code': f"{code}-{dep_date}"
            }
        )
        return instance
