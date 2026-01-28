from django.test import TestCase, Client as TestClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from apps.invoices.models import Invoice, InvoiceItem
from apps.currencies.models import Currency
from apps.clients.models import Client, Family
from apps.tours.models import Product, TourInstance, TourBooking
from datetime import timedelta

User = get_user_model()

class MarketingDashboardTests(TestCase):
    def setUp(self):
        # Users
        self.marketing = User.objects.create_user(username='market', password='pw', role='MARKETING')
        self.client_user = TestClient()
        self.client_user.login(username='market', password='pw')

        # Currencies
        self.cad = Currency.objects.create(code='CAD', name='Canadian Dollar', symbol='$', is_base=True)
        self.usd = Currency.objects.create(code='USD', name='US Dollar', symbol='U', is_base=False)

        # Clients
        self.fam = Family.objects.create(name="Test Fam")
        self.c1 = Client.objects.create(first_name="A", last_name="B", family=self.fam)

        # Products
        self.prod = Product.objects.create(name="Tour A", unique_seq="SEQ1", country_code="JPN")
        self.ti = TourInstance.objects.create(product=self.prod, start_date=timezone.now().date(), end_date=timezone.now().date(), instance_code="JPNSEQ1")

        # Invoices
        # 1. CAD, PAID
        self.inv_cad = Invoice.objects.create(
            currency=self.cad,
            status=Invoice.Status.PAID,
            total_amount=Decimal('100.00'),
            created_at=timezone.now(),
            sales_agent=self.marketing
        )
        self.bk1 = TourBooking.objects.create(booking_id="BK1", tour_instance=self.ti, price=100)
        InvoiceItem.objects.create(invoice=self.inv_cad, client=self.c1, description="Tour A", unit_price=100, tour_booking=self.bk1)

        # 2. USD, PAID
        self.inv_usd = Invoice.objects.create(
            currency=self.usd,
            status=Invoice.Status.PAID,
            total_amount=Decimal('50.00'),
            created_at=timezone.now(),
            sales_agent=self.marketing
        )
        InvoiceItem.objects.create(invoice=self.inv_usd, client=self.c1, description="Tour A USD", unit_price=50)

        # 3. CAD, DRAFT (Should be excluded by default or if filtered)
        self.inv_draft = Invoice.objects.create(
            currency=self.cad,
            status=Invoice.Status.DRAFT,
            total_amount=Decimal('999.00'),
            created_at=timezone.now(),
            sales_agent=self.marketing
        )

    def test_dashboard_strict_currency(self):
        """Test that selecting CAD only shows CAD invoices"""
        response = self.client_user.get('/marketing/dashboard/', {'currency': 'CAD'})
        ctx = response.context

        # Check logic: Should sum 100.00 (CAD Paid), ignore USD, ignore Draft (if default filter excludes draft)
        # Note: Plan says user multi-selects status. If none selected, maybe default to "Active" (Paid/Invoiced)?
        # Let's assume default is verified/paid.

        # Find the metric "total_revenue"
        # We need to inspect how view passes data.
        pass

    def test_dashboard_status_filter(self):
        """Test manually selecting DRAFT status"""
        response = self.client_user.get('/marketing/dashboard/', {'currency': 'CAD', 'status': ['DRAFT']})
        # Should see 999.00
        pass
