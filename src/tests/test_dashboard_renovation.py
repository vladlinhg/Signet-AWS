from django.test import TestCase, Client as TestClient
from django.contrib.auth import get_user_model
from apps.invoices.models import Invoice
from apps.currencies.models import Currency
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class DashboardRenovationTest(TestCase):
    def setUp(self):
        # Users
        self.accountant = User.objects.create_user(username='acc_test', password='password', role='ACCOUNTANT')
        self.manager = User.objects.create_user(username='mgr_test', password='password', role='MANAGER')
        self.sales = User.objects.create_user(username='sales_test', password='password', role='SALES')

        # Clients
        self.acc_client = TestClient()
        self.acc_client.login(username='acc_test', password='password')

        self.mgr_client = TestClient()
        self.mgr_client.login(username='mgr_test', password='password')

        # Data
        self.cad = Currency.objects.create(code='CAD', symbol='$')
        self.usd = Currency.objects.create(code='USD', symbol='U$')

        # Invoices
        # 1. Paid CAD (Active)
        self.inv1 = Invoice.objects.create(
            invoice_number='INV-001', sales_agent=self.sales, currency=self.cad,
            status=Invoice.Status.PAID, total_amount=1000
        )
        # 2. Draft CAD (Active but maybe hidden by default in some views, but Accountant should see if filtered)
        self.inv2 = Invoice.objects.create(
            invoice_number='INV-002', sales_agent=self.sales, currency=self.cad,
            status=Invoice.Status.DRAFT, total_amount=500
        )
        # 3. Cancelled CAD (Active) - Updated to be included in Global Count
        self.inv3 = Invoice.objects.create(
            invoice_number='INV-003', sales_agent=self.sales, currency=self.cad,
            status=Invoice.Status.CANCELLED, total_amount=2000
        )
        # 4. Paid USD (Different Currency)
        self.inv4 = Invoice.objects.create(
            invoice_number='INV-004', sales_agent=self.sales, currency=self.usd,
            status=Invoice.Status.PAID, total_amount=100
        )

    def test_accountant_dashboard_renovation(self):
        """Verify Accountant Dashboard Global Filters & Logic."""
        # 1. Default View
        resp = self.acc_client.get('/accountant/dashboard/')
        self.assertEqual(resp.status_code, 200)

        # Check Context Keys for Split Metrics
        self.assertIn('global_revenue', resp.context)
        self.assertIn('filtered_revenue', resp.context)

        # 1a. Global Scope (Header) - Should include ALL CAD invoices (Paid, Draft, Cancelled)
        # 1000 + 500 + 2000 = 3500
        self.assertEqual(resp.context['global_revenue'], 3500)
        self.assertEqual(resp.context['global_invoice_count'], 3)

        # 1b. Filtered Scope (Table) - Defaults to [INVOICED, PAID, DEPOSIT, DRAFT, CANCELLED] if configured,
        # or maybe just active. Let's assume our code sets default to ALL relevant including Cancelled.
        # If default includes Cancelled: 3500. If excluded: 1500.
        # In views.py we set default to include Invoice.Status.CANCELLED.
        # So Filtered should essentially equal Global if no specific status is unchecked.
        self.assertEqual(resp.context['filtered_revenue'], 3500)

        # 2. Filter Explicitly (Exclude Cancelled)
        # e.g. Status = [PAID, DRAFT]
        resp = self.acc_client.get('/accountant/dashboard/', {
            'currency': 'CAD',
            'status': [Invoice.Status.PAID, Invoice.Status.DRAFT]
        })
        # Global should remain 3500 (It overlooks status)
        self.assertEqual(resp.context['global_revenue'], 3500)

        # Filtered should be 1500 (1000+500)
        self.assertEqual(resp.context['filtered_revenue'], 1500)
        self.assertEqual(resp.context['filtered_invoice_count'], 2)

    def test_manager_dashboard_renovation(self):
        """Verify Manager Dashboard Renovation."""
        # 1. Default View (CAD)
        resp = self.mgr_client.get('/manager/dashboard/')
        self.assertEqual(resp.status_code, 200)

        # Global Wallet: Should match ALL CAD (ignores status filter) = 3500
        self.assertEqual(resp.context['global_wallet_total'], 3500)

        # Agent Stats: Filtered.
        # Default Filter in Manager View includes [INVOICED, PAID, DEPOSIT] (Excludes Cancelled/Draft?)
        # Let's check views.py... yes, default list: [INVOICED, PAID, DEPOSIT]
        # So Filtered should ONLY contain Inv1 (PAID, 1000). Inv2 is Draft, Inv3 is Cancelled.

        # Check Agent Stats
        stats = resp.context['agent_stats']
        agent_stat = next(s for s in stats if s['username'] == 'sales_test')
        self.assertEqual(agent_stat['total_invoices'], 1)
        self.assertEqual(agent_stat['total_revenue'], 1000)

        # 2. Filter to Include Cancelled
        resp = self.mgr_client.get('/manager/dashboard/', {
            'currency': 'CAD',
            'status': [Invoice.Status.PAID, Invoice.Status.CANCELLED]
        })
        # Global Wallet stays 3500
        self.assertEqual(resp.context['global_wallet_total'], 3500)

        # Agent Stats should now reflect 3000 (1000 + 2000)
        stats = resp.context['agent_stats']
        agent_stat = next(s for s in stats if s['username'] == 'sales_test')
        self.assertEqual(agent_stat['total_revenue'], 3000)
