from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, time
import random
import uuid

# Models
from apps.tours.models import Product, TourInstance, TourBooking
from apps.flights.models import Airline, Airport, Flight, FlightInstance, FlightTicket
from apps.clients.models import Client, TravelGroup, City, Ethnicity, PaymentMethod
from apps.invoices.models import Invoice, InvoiceItem, InvoicePayment, Coupon
from apps.currencies.models import Currency
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Generate Business Data (Products, Inventory, Clients, Financials)'

    def handle(self, *args, **options):
        self.stdout.write("Starting Data Generation...")

        # 1. Products & Inventory
        self.generate_products_and_inventory()

        # 2. Clients
        self.generate_clients()

        # 3. Bookings & Financials
        self.generate_transactions()

        self.stdout.write(self.style.SUCCESS('Data Generation Complete.'))

    def generate_products_and_inventory(self):
        self.stdout.write("- Generating Products & Inventory...")

        # Products
        p1 = Product.objects.create(name='Safari Adventure', country_code='KEN', days_count='10', unique_seq='001')
        p2 = Product.objects.create(name='European Escape', country_code='FRA', days_count='12', unique_seq='002')
        p3 = Product.objects.create(name='Asian Odyssey', country_code='JPN', days_count='14', unique_seq='003')

        # Tour Instances (Future)
        start_dates = [timezone.now().date() + timedelta(days=i*15) for i in range(1, 4)]
        self.tour_instances = []
        for p in [p1, p2, p3]:
            for d in start_dates:
                ti = TourInstance.objects.create(product=p, start_date=d, end_date=d + timedelta(days=int(p.days_count)))
                self.tour_instances.append(ti)

        # Flights Routes & Instances
        # Require Airports/Airlines from Static Data
        yvr = Airport.objects.filter(code='YVR').first()
        lhr = Airport.objects.filter(code='LHR').first()
        nrt = Airport.objects.filter(code='NRT').first()
        ac = Airline.objects.filter(code='AC').first()

        if yvr and lhr and ac:
            f1 = Flight.objects.create(airline=ac, flight_number='098', departure_airport=yvr, arrival_airport=lhr)
            # Create instances for next 3 months
            self.flight_instances = []
            for i in range(5):
                d = timezone.now().date() + timedelta(days=i*7 + 10)
                fi = FlightInstance.objects.create(
                    flight=f1, departure_date=d, departure_time=time(12,0), arrival_time=time(20,0)
                )
                self.flight_instances.append(fi)
        else:
            self.flight_instances = []
            self.stdout.write(self.style.WARNING("  ! Missing Static Data (Airports/Airlines). Skipping Flight Generation."))

    def generate_clients(self):
        self.stdout.write("- Generating Clients...")

        cities = list(City.objects.all())
        ethnicities = list(Ethnicity.objects.all())

        if not cities:
            cities = [City.objects.create(name='Default City', country_code='DEF')]

        self.clients = []
        self.travel_groups = []

        # Generate 15 Clients
        base_names = [
            ('John', 'Doe', 'M'), ('Jane', 'Smith', 'F'), ('Bob', 'Jones', 'M'),
            ('Alice', 'Wong', 'F'), ('Charlie', 'Brown', 'M'), ('Diana', 'Prince', 'F'),
            ('Evan', 'Li', 'M'), ('Fiona', 'Chen', 'F'), ('George', 'Martin', 'M'),
            ('Hannah', 'Montana', 'F')
        ]

        for i in range(15):
            first, last, gender = random.choice(base_names)
            # Unique-ify
            last = f"{last}{i}"

            # Create Travel Group
            # Naming Logic: "First Client Full Name Travel Partners"
            # Since this client is the first (and only initially)
            tg_name = f"{first} {last} Travel Partners"
            tg = TravelGroup.objects.create(name=tg_name)
            self.travel_groups.append(tg)

            # Create Payment Method for Group
            pm = PaymentMethod.objects.create(
                travel_group=tg,
                method_type=random.choice(PaymentMethod.Type.values),
                details=f"Card ending {random.randint(1000,9999)}"
            )

            client = Client.objects.create(
                first_name=first,
                last_name=last,
                gender=gender,
                email=f"{first.lower()}.{last.lower()}@example.com",
                phone=f"555-01{i:02d}",
                origin=random.choice(cities) if cities else None,
                travel_group=tg
            )
            self.clients.append(client)

    def generate_transactions(self):
        self.stdout.write("- Generating Transactions (Invoices)...")

        sales_agents = list(User.objects.filter(role='SALES'))
        if not sales_agents:
            sales_agents = [User.objects.first()] # Fallback to admin

        currencies = list(Currency.objects.all())

        # Create 20 Invoices
        for i in range(20):
            client = random.choice(self.clients)
            agent = random.choice(sales_agents)
            # Bias towards CAD (80% chance)
            if currencies:
                cad = next((c for c in currencies if c.code == 'CAD'), currencies[0])
                currency = cad if random.random() < 0.8 else random.choice(currencies)
            else:
                currency = None

            # 1. Invoice
            # Booking Number auto-generated by model save
            # Status
            status = random.choice([Invoice.Status.INVOICED, Invoice.Status.PAID, Invoice.Status.DEPOSIT, Invoice.Status.DRAFT])

            # Bias towards recent dates (80% within last 14 days)
            days_ago = random.randint(0, 14) if random.random() < 0.8 else random.randint(15, 60)

            invoice = Invoice.objects.create(
                sales_agent=agent,
                status=status,
                currency=currency,
                created_at = timezone.now() - timedelta(days=days_ago)
            )

            # If status is Invoiced/Paid, generate invoice_number
            if status in [Invoice.Status.INVOICED, Invoice.Status.PAID]:
                invoice.invoice_number = f"INV-{invoice.booking_number}" # Simple logic for demo
                invoice.save()

            total_val = 0

            # 2. Items
            # Tour Booking
            if self.tour_instances:
                ti = random.choice(self.tour_instances)
                price = random.randint(2000, 5000)

                # Create Booking
                tb = TourBooking.objects.create(
                    tour_instance=ti,
                    booking_id=f"B-{uuid.uuid4().hex[:6]}",
                    price=price,
                    status='BOOKED'
                )

                InvoiceItem.objects.create(
                    invoice=invoice,
                    client=client,
                    description=f"Tour: {ti.product.name}",
                    quantity=random.randint(1, 2),
                    unit_price=price,
                    tour_booking=tb
                )
                total_val += price

            # Flight Ticket
            if self.flight_instances:
                fi = random.choice(self.flight_instances)
                price = random.randint(500, 1500)

                ft = FlightTicket.objects.create(
                    flight=fi,
                    client=client,
                    seat_number="TBA"
                )

                InvoiceItem.objects.create(
                    invoice=invoice,
                    client=client,
                    description=f"Flight: {fi.flight.code}",
                    quantity=1,
                    unit_price=price,
                    flight_ticket=ft
                )
                total_val += price

            # 3. Payments
            # Payment Method from Client's Group
            pm = client.travel_group.payment_methods.first()

            if status == Invoice.Status.PAID:
                InvoicePayment.objects.create(
                    invoice=invoice,
                    amount=total_val, # Approx
                    payment_type=InvoicePayment.PaymentType.FULL_PAYMENT,
                    payment_method=pm,
                    description="Full Payment"
                )
            elif status == Invoice.Status.DEPOSIT:
                InvoicePayment.objects.create(
                    invoice=invoice,
                    amount=total_val * 0.3, # 30%
                    payment_type=InvoicePayment.PaymentType.DEPOSIT,
                    payment_method=pm,
                    description="Deposit"
                )
            elif status == Invoice.Status.INVOICED:
                 # Maybe a partial payment or none?
                 pass

        self.stdout.write(f"  - Generated 20 Invoices.")
