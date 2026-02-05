import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import User
from apps.clients.models import Client
from apps.tours.models import TourInstance
from apps.flights.models import Flight, FlightTicket
from apps.invoices.models import Invoice, InvoiceItem
from apps.currencies.models import Currency

class Command(BaseCommand):
    help = 'Generate dummy verified invoices for analytics.'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=10)

    def handle(self, *args, **options):
        count = options['count']
        print(f"Generating {count} dummy invoices...")

        clients = list(Client.objects.all())
        tours = list(TourInstance.objects.all())
        flights = list(Flight.objects.all())
        sales_reps = list(User.objects.filter(role=User.Role.SALES))

        if not (clients and tours and sales_reps):
            print("Missing base data (Clients, Tours, Sales Users). Run import_erp_data first.")
            return

        for i in range(count):
            # Random date in last 6 months
            days_ago = random.randint(0, 180)
            date_created = timezone.now() - timedelta(days=days_ago)

            client = random.choice(clients)
            sales_agent = random.choice(sales_reps)
            tour = random.choice(tours)
            flight = random.choice(flights) if flights else None

            # Assign Random Currency
            currency = None
            if Currency.objects.exists():
                currency = random.choice(list(Currency.objects.all()))

            # Random Status (Weighted)
            status = random.choices(
                [Invoice.Status.INVOICED, Invoice.Status.DEPOSIT, Invoice.Status.DRAFT, Invoice.Status.PAID],
                weights=[40, 30, 20, 10],
                k=1
            )[0]

            # Create Invoice
            invoice = Invoice.objects.create(
                sales_agent=sales_agent,
                status=status,
                currency=currency
            )
            # Fix created_at
            invoice.created_at = date_created
            invoice.save()

            # --- Add Ticket Items (1-3 Flights) ---
            num_flights = random.randint(1, 3)
            if flights:
                for _ in range(num_flights):
                    flight = random.choice(flights)
                    # Instance?
                    # We need a FlightInstance to create a ticket.
                    # Let's simplify and grab the first instance or create one on the fly if needed
                    # But init_db_content only made ONE instance.
                    # For dummy data, let's just reuse the first instance of that flight
                    instance = flight.instances.first()
                    if not instance: continue

                    seat = None
                    for _ in range(10):
                        candidate = f"{random.randint(10, 99)}{random.choice(['A', 'B', 'C', 'D', 'E', 'F'])}"
                        if not FlightTicket.objects.filter(flight=instance, seat_number=candidate).exists():
                            seat = candidate
                            break

                    if seat:
                        ft = FlightTicket.objects.create(
                            flight=instance,
                            seat_number=seat,
                            cabin_class='Economy',
                            bags=1,
                            client=client
                        )
                        price = random.choice([500, 800, 1200, 450])
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            client=client,
                            flight_ticket=ft,
                            description=f"Flight: {flight.code} Seat {seat}",
                            quantity=1,
                            unit_price=price
                        )

            # --- Add Tour Items (1-2 Tours) ---
            from apps.tours.models import TourBooking
            num_tours = random.randint(1, 2)
            for _ in range(num_tours):
                tour = random.choice(tours) # This is a TourInstance
                qty = random.randint(1, 4)
                price = random.choice([2500, 3000, 1800, 4500])

                # Create Booking
                import uuid
                booking = TourBooking.objects.create(
                    tour_instance=tour,
                    booking_id=f"{tour.instance_code}-{uuid.uuid4().hex[:6]}",
                    booking_type='DOUBLE',
                    price=price,
                    status='BOOKED'
                )

                InvoiceItem.objects.create(
                    invoice=invoice,
                    client=client,
                    tour_booking=booking, # Fixed field
                    description=f"Tour: {tour.product.name} ({tour.instance_code})",
                    quantity=qty,
                    unit_price=price
                )

            # Recalculate Total
            invoice.update_total()

        print(f"Successfully created {count} invoices.")
