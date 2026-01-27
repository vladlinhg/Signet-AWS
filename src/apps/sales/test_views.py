from django.test import TestCase
from django.urls import reverse
from apps.users.models import User
from apps.sales.models import Invoice
from apps.clients.models import Client

class DashboardViewTest(TestCase):
    def setUp(self):
        # Users
        self.accountant = User.objects.create_user(username='acc', password='pw', role=User.Role.ACCOUNTANT)
        self.sales = User.objects.create_user(username='sales', password='pw', role=User.Role.SALES)
        self.manager = User.objects.create_user(username='mgr', password='pw', role=User.Role.MANAGER)
        
        # Data
        self.erp_client = Client.objects.create(first_name="Test", last_name="Client")
        self.invoice = Invoice.objects.create(
            client=self.erp_client, 
            sales_agent=self.sales,
            invoice_number="INV-001",
            status=Invoice.Status.SUBMITTED
        )

    def test_dashboard_access(self):
        # Accountant can access
        self.client.login(username='acc', password='pw')
        response = self.client.get(reverse('accountant_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "INV-001") # Should see the invoice

    def test_sales_cannot_access_dashboard(self):
        self.client.login(username='sales', password='pw')
        response = self.client.get(reverse('accountant_dashboard'))
        # Should redirect to login or 403 depending on implementation?
        # @user_passes_test usually redirects to login if False
        self.assertEqual(response.status_code, 302) 

    def test_audit_action_approve(self):
        self.client.login(username='acc', password='pw')
        url = reverse('invoice_audit_detail', args=[self.invoice.pk])
        
        # Post approve
        response = self.client.post(url, {'action': 'approve'})
        self.assertRedirects(response, reverse('accountant_dashboard'))
        
        # Check DB
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.VERIFIED)

    def test_audit_action_reject(self):
        self.client.login(username='acc', password='pw')
        url = reverse('invoice_audit_detail', args=[self.invoice.pk])
        
        # Post reject without note -> Should fail/message?
        # My view implementation adds a message but might stay on page (200)
        
        # Post reject WITH note
        response = self.client.post(url, {'action': 'reject', 'note': 'Wrong price'})
        self.assertRedirects(response, reverse('accountant_dashboard'))
        
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.NEEDS_FIX)
        self.assertTrue(self.invoice.notes.filter(content='Wrong price').exists())
