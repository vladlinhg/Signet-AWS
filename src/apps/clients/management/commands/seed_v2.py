import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from apps.clients.models import Client, Family, Address, PaymentMethod
from apps.tours.models import TourInstance, TourBooking
from apps.invoices.models import Invoice, InvoiceItem
from apps.users.models import User
from apps.currencies.models import Currency

fake = Faker()

class Command(BaseCommand):
    help = 'Seeds v2 data for Families, Addresses, Tour Bookings, and Invoices'

    def handle(self, *args, **options):
        self.stdout.write('Starting Seed v2...')

        # 0. Ensure Sales Agents exist
        agent = User.objects.filter(role='SALES').first()
        if not agent:
            self.stdout.write(self.style.WARNING('No Sales Agent found. Creating default...'))
            agent = User.objects.create_user('sales1', 'sales1@example.com', 'password', role='SALES')

        # 1. Create Addresses
        self.stdout.write('Creating Addresses...')
        addresses = []
        for _ in range(10):
            addr = Address.objects.create(
                street_number=fake.building_number(),
                street_name=fake.street_name(),
                city=fake.city(),
                province=fake.state_abbr(),
                postal_code=fake.postcode(),
                country=fake.country()
            )
            addresses.append(addr)

        # 2. Create Families and Map/Create Clients
        self.stdout.write('Creating Families & Clients...')

        # Helper to get or create clients
        clients = list(Client.objects.all())
        if len(clients) < 50:
            for _ in range(50 - len(clients)):
                clients.append(Client.objects.create(
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    email=fake.email(),
                    phone=fake.phone_number()
                ))

        families = []
        # Group clients into families
        last_names = set(c.last_name for c in clients)

        for lname in last_names:
            fam = Family.objects.create(name=f"The {lname} Family")
            families.append(fam)

            # Find clients with this last name
            members = [c for c in clients if c.last_name == lname]
            # Assign Address and Family
            fam_addr = random.choice(addresses)
            for m in members:
                m.family = fam
                m.address = fam_addr
                m.gender = random.choice(['M', 'F', 'X'])
                m.save()

            # Create Payment Method for Family
            PaymentMethod.objects.create(
                family=fam,
                method_type=random.choice(['CC', 'BANK']),
                details=f"Visa ending {random.randint(1000, 9999)}"
            )

        # 3. Create Tour Bookings
        self.stdout.write('Creating Tour Bookings...')
        instances = TourInstance.objects.all()
        all_bookings = []

        for instance in instances:
            # Check if bookings already exist to avoid duplicates if re-run
            if instance.bookings.exists():
                all_bookings.extend(list(instance.bookings.all()))
                continue

            # Create 20 seats
            # 10 Single
            for i in range(1, 11):
                bk = TourBooking.objects.create(
                    tour_instance=instance,
                    booking_id=f"{instance.instance_code}-S-{i:02d}",
                    booking_type='SINGLE',
                    price=Decimal('2000.00'),
                    status='AVAILABLE'
                )
                all_bookings.append(bk)
            # 10 Double
            for i in range(1, 11):
                bk = TourBooking.objects.create(
                    tour_instance=instance,
                    booking_id=f"{instance.instance_code}-D-{i:02d}",
                    booking_type='DOUBLE',
                    price=Decimal('1500.00'),
                    status='AVAILABLE'
                )
                all_bookings.append(bk)

        # 3b. Create Flights and Tickets
        self.stdout.write('Creating Flights and Tickets...')
        from apps.flights.models import Flight, FlightTicket
        import datetime

        flights = []
        routes = [
            ('YVR', 'NRT', 'AC'), ('LHR', 'JFK', 'BA'), ('TPE', 'LAX', 'BR'),
            ('SYD', 'DXB', 'EK'), ('SIN', 'HND', 'SQ')
        ]

        # Create some flights
        for i in range(10):
            origin, dest, airline = random.choice(routes)
            flight = Flight.objects.create(
                airline_code=airline,
                flight_number=f"{random.randint(10, 999):03d}",
                departure_date=timezone.now().date() + datetime.timedelta(days=random.randint(10, 60)),
                departure_airport=origin,
                arrival_airport=dest,
                departure_time=datetime.time(random.randint(0, 23), random.randint(0, 59)),
                arrival_time=datetime.time(random.randint(0, 23), random.randint(0, 59))
            )
            flights.append(flight)

            # Create tickets for this flight
            for row in range(1, 6):
                for seat_letter in ['A', 'B', 'C']:
                    FlightTicket.objects.create(
                        flight=flight,
                        seat_number=f"{row}{seat_letter}",
                        cabin_class=random.choice(['Economy', 'Business']),
                        ticket_code=f"{flight.code}{row}{seat_letter}"
                    )

        # 4. Generate Invoices
        self.stdout.write('Generating Invoices...')

        cad, _ = Currency.objects.get_or_create(code='CAD', defaults={'symbol': '$', 'name': 'Canadian Dollar', 'is_base': True})

        for _ in range(20):
            fam = random.choice(families)
            method = fam.payment_methods.first()
            if not method: continue

            # Create Invoice
            invoice = Invoice.objects.create(
                payment_method=method,
                sales_agent=agent,
                status=random.choice(['DRAFT', 'VERIFIED', 'PAID']),
                total_amount=0,
                currency=cad
            )

            # Add Items for random members of the family
            members = fam.members.all()
            if not members.exists(): continue

            travelers = random.sample(list(members), k=random.randint(1, min(len(members), 4)))

            all_flight_tickets = list(FlightTicket.objects.filter(invoice_items__isnull=True))

            for traveler in travelers:
                # 50% chance for Tour
                if random.choice([True, False]):
                    avail_booking = next((b for b in all_bookings if b.status == 'AVAILABLE'), None)
                    if avail_booking:
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            client=traveler,
                            description=f"Tour: {avail_booking.booking_id}",
                            quantity=1,
                            unit_price=avail_booking.price,
                            tour_booking=avail_booking
                        )
                        avail_booking.status = 'BOOKED'
                        avail_booking.save()

                # 50% chance for Flight
                if random.choice([True, False]) and all_flight_tickets:
                    ticket = all_flight_tickets.pop(0)
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        client=traveler,
                        description=f"Flight: {ticket.flight.code} Seat {ticket.seat_number}",
                        quantity=1,
                        unit_price=Decimal(random.randint(500, 2000)),
                        flight_ticket=ticket
                    )

            invoice.update_total()

        self.stdout.write(self.style.SUCCESS(f'Seed v2 Complete! Created/Updated data.'))
