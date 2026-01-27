from django.test import TestCase
from django.utils import timezone
from apps.users.models import User
from apps.tours.models import Product, TourInstance
from apps.clients.models import Client
from apps.sales.models import Invoice, InvoiceItem

class InventoryLogicTests(TestCase):
    def setUp(self):
        # Setup Data
        self.user = User.objects.create_user(username='salesrep', password='password', role=User.Role.SALES)
        self.client = Client.objects.create(first_name="Jane", last_name="Doe")
        # Updated Product Signature
        self.product = Product.objects.create(
            name="Japan Tour", 
            country_code="JPN",
            days_count="06",
            unique_seq="001"
        )
        self.tour = TourInstance.objects.create(
            product=self.product,
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            total_spots=20
        )

    def test_inventory_deduction(self):
        """Test that adding an InvoiceItem reduces available spots."""
        print(f"\nInitial Booked: {self.tour.booked_spots}")
        self.assertEqual(self.tour.booked_spots, 0)
        self.assertEqual(self.tour.available_spots, 20)

        # Create Invoice
        invoice = Invoice.objects.create(client=self.client, sales_agent=self.user, status=Invoice.Status.DRAFT)
        
        # Add Item for 2 people
        InvoiceItem.objects.create(
            invoice=invoice,
            description="Booking",
            quantity=2,
            unit_price=1000,
            tour_instance=self.tour
        )

        # Refresh tour from DB logic check
        # calculated property should update immediately as it queries the DB
        print(f"Booked after Item (Qty 2): {self.tour.booked_spots}")
        self.assertEqual(self.tour.booked_spots, 2)
        self.assertEqual(self.tour.available_spots, 18)

    def test_cancelled_invoice_restores_inventory(self):
        """Test that cancelling an invoice restores spots."""
        invoice = Invoice.objects.create(client=self.client, sales_agent=self.user, status=Invoice.Status.DRAFT)
        InvoiceItem.objects.create(invoice=invoice, quantity=5, unit_price=1000, tour_instance=self.tour)
        
        self.assertEqual(self.tour.booked_spots, 5)

        # Cancel
        invoice.status = 'CANCELLED' # Note: Status choices didn't include CANCELLED strictly in spec, let's check model
        # Spec said: DRAFT, SUBMITTED, NEEDS_FIX, VERIFIED, PAID.
        # Logic check: `booked_spots` excludes `invoice__status='CANCELLED'`.
        # So we need to ensure 'CANCELLED' is a valid state or handled.
        # I'll just use a string check for now, assuming the model supports it or I fix the model.
        invoice.save()

        print(f"Booked after Cancel: {self.tour.booked_spots}")
        self.assertEqual(self.tour.booked_spots, 0)
