from django.test import TestCase, Client as TestClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.invoices.models import Invoice, InvoiceItem
from apps.currencies.models import Currency
from apps.clients.models import Client, Family
from apps.flights.models import Flight, FlightInstance, FlightTicket, Airport, Airline

User = get_user_model()

class DetailedDebugTests(TestCase):
    def setUp(self):
        self.marketing = User.objects.create_user(username='market', password='pw', role='MARKETING')
        self.client_user = TestClient()
        self.client_user.login(username='market', password='pw')
        self.currency = Currency.objects.create(code='CAD', symbol='$')
        self.family = Family.objects.create(name="Fam")
        self.client = Client.objects.create(first_name="A", last_name="B", family=self.family)

        # Create minimal invoice to verify Tab Logic
        self.inv = Invoice.objects.create(
            status=Invoice.Status.PAID,
            currency=self.currency,
            sales_agent=self.marketing,
            created_at=timezone.now()
        )
        # Add Normal Item
        InvoiceItem.objects.create(invoice=self.inv, client=self.client, description="Item 1", unit_price=10.00, quantity=1)

        # Create Flight Dependencies
        self.airport1 = Airport.objects.create(code="YVR", name="Vancouver")
        self.airport2 = Airport.objects.create(code="LHR", name="London")
        self.airline = Airline.objects.create(name="Air Canada", code="AC")

        # Create Flight
        self.flight = Flight.objects.create(
            airline=self.airline,
            flight_number="123",
            departure_airport=self.airport1,
            arrival_airport=self.airport2
        )

        # Create Flight Instance
        self.flight_instance = FlightInstance.objects.create(
            flight=self.flight,
            departure_date=timezone.now().date(),
            departure_time=timezone.now().time(),
            arrival_time=timezone.now().time()
        )

        # Create Ticket
        FlightTicket.objects.create(client=self.client, flight=self.flight_instance, ticket_code="TKT123", cabin_class="Economy")

    def test_customer_tab_crash(self):
        """Reproduce 500 Error on Customer Tab"""
        try:
            response = self.client_user.get('/marketing/dashboard/', {'tab': 'customers', 'currency': 'CAD'})
            if response.status_code != 200:
                print(f"FAILED (Customers): {response.status_code}")
                # Print exception if possible
            else:
                ctx = response.context
                print(f"SUCCESS (Customers). Active Customers: {ctx.get('active_customers')}")
        except Exception as e:
            print(f"EXCEPTION (Customers): {e}")
            raise e

    def test_flight_tab_crash(self):
        """Reproduce potential crash on Flight Tab and check counts"""
        try:
            response = self.client_user.get('/marketing/dashboard/', {'tab': 'flights', 'currency': 'CAD'})
            if response.status_code != 200:
                print(f"FAILED (Flights): {response.status_code}")
            else:
                ctx = response.context
                tickets = ctx.get('tickets_sold')
                revenue = ctx.get('flight_revenue')
                print(f"SUCCESS (Flights). Tickets Sold: {tickets}, Revenue: {revenue}")

                # Verification
                if tickets != 1:
                     print("ERROR: Flight Ticket Count should be 1 (Fallback Logic)")
                else:
                     print("VERIFIED: Flight Ticket Count is 1")
        except Exception as e:
            print(f"EXCEPTION (Flights): {e}")
            raise e

    def test_interactive_links(self):
        """Verify dashboard contains Admin Links for items"""
        # 1. Invoice Tab
        resp = self.client_user.get('/marketing/dashboard/', {'tab': 'invoices', 'currency': 'CAD'})
        self.assertContains(resp, f'/admin/invoices/invoice/{self.inv.id}/change/')

        # 2. Customer Tab
        resp = self.client_user.get('/marketing/dashboard/', {'tab': 'customers', 'currency': 'CAD'})
        self.assertTrue('recent_customers' in resp.context)
        # Check for Client Link
        self.assertContains(resp, f'/admin/clients/client/{self.client.id}/change/')

        # 3. Flight Tab
        resp = self.client_user.get('/marketing/dashboard/', {'tab': 'flights', 'currency': 'CAD'})
        # Should have recent_tickets
        self.assertTrue(resp.context.get('recent_tickets') is not None)
        # Check for Ticket Link (need ticket ID)
        ticket = FlightTicket.objects.first()
        self.assertContains(resp, f'/admin/flights/flightticket/{ticket.id}/change/')
