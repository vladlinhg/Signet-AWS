from django.test import TestCase, Client as TestClient
from django.contrib.auth import get_user_model
from apps.invoices.models import Invoice, InvoiceItem
from apps.clients.models import Client
from apps.flights.models import Flight, FlightInstance, FlightTicket
from apps.tours.models import TourBooking, TourInstance, Product
from django.utils import timezone

User = get_user_model()

class SalesConsoleFixTest(TestCase):
    def setUp(self):
        self.password = 'testpass123'
        self.sales_user = User.objects.create_user(
            username='sales_test', email='sales@test.com', password=self.password, role='SALES'
        )
        self.client_user = TestClient()
        self.client_user.login(username='sales_test', password=self.password)

        # Setup Data
        self.client = Client.objects.create(first_name="John", last_name="Doe", email="john@test.com")
        self.invoice = Invoice.objects.create(sales_agent=self.sales_user)
        self.invoice_item = InvoiceItem.objects.create(
            invoice=self.invoice,
            client=self.client,
            description="Test Item",
            unit_price=100,
            quantity=1
        )

    def test_sales_dashboard_tabs(self):
        """Test all tabs in sales dashboard to ensure no 500 errors."""
        tabs = ['invoices', 'clients', 'flights', 'tours']
        for tab in tabs:
            print(f"Testing Sales Tab: {tab}")
            response = self.client_user.get('/sales/dashboard/', {'tab': tab})
            if response.status_code != 200:
                print(f"FAILED Tab {tab}: {response.status_code}")
                # Print Traceback if needed, but standard test runner will show it
            self.assertEqual(response.status_code, 200, f"Tab '{tab}' returned {response.status_code}")
