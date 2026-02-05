from django.core.management.base import BaseCommand
from django.db import transaction
from apps.invoices.models import Invoice, InvoiceItem, InvoicePayment
from apps.tours.models import Product, TourInstance, TourBooking
from apps.flights.models import Flight, FlightInstance, FlightTicket
from apps.clients.models import Client, TravelGroup

class Command(BaseCommand):
    help = 'Smart Wipe: Deletes business data but preserves static configuration (Users, Cities, etc.)'

    def handle(self, *args, **options):
        self.stdout.write("Starting Smart Wipe...")

        with transaction.atomic():
            # Deletion Order (Child -> Parent)

            # 1. Financials
            InvoicePayment.objects.all().delete()
            InvoiceItem.objects.all().delete()
            Invoice.objects.all().delete()
            self.stdout.write("  - Deleted Invoices & Payments")

            # 2. Bookings & Tickets
            TourBooking.objects.all().delete()
            FlightTicket.objects.all().delete()
            self.stdout.write("  - Deleted Bookings & Tickets")

            # 3. Inventory instances
            TourInstance.objects.all().delete()
            # FlightInstance? Assuming Flight model structure.
            # If FlightInstance exists separately, delete it.
            # Based on previous context, Flight has instances?
            # In init_db_content I saw FlightInstance.
            if FlightInstance.objects.exists():
                FlightInstance.objects.all().delete()
            self.stdout.write("  - Deleted Inventory instances")

            # 4. Products & Routes
            Product.objects.all().delete()
            # Flight routes might be considered "Inventory" to generate?
            # User said "Everything except airlines/airports". So Flight (Routes) should appear in generator?
            # Yes, Generate Data Phase 3: Flight Routes.
            Flight.objects.all().delete()
            self.stdout.write("  - Deleted Products & Flight Routes")

            # 5. Clients
            Client.objects.all().delete()
            TravelGroup.objects.all().delete()
            self.stdout.write("  - Deleted Clients & Travel Groups")

        self.stdout.write(self.style.SUCCESS('Successfully wiped business data.'))
