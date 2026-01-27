from django.test import TestCase, Client as TestClient
from django.contrib.auth import get_user_model
from apps.tours.models import Product
from apps.flights.models import Flight
from apps.invoices.models import Invoice

User = get_user_model()

class WipeDataTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.it_admin = User.objects.create_user(username='admin', password='pwd', role='IT_ADMIN')
        self.manager = User.objects.create_user(username='mgr', password='pwd', role='MANAGER')
        
        # Create Dummy Data
        Product.objects.create(name="Test", country_code="TST", days_count=5, unique_seq='001')
        from django.utils import timezone
        Flight.objects.create(
            code="TESTFLIGHT", 
            airline_code="TS", 
            flight_number="001", 
            departure_date=timezone.now().date(),
            departure_airport="YVR",
            arrival_airport="YYZ"
        )

    def test_permission(self):
        # Manager denied
        self.client.force_login(self.manager)
        response = self.client.get('/admin/wipe-data/')
        # redirect to admin login
        self.assertNotEqual(response.status_code, 200) 

        # IT Admin allow
        self.client.force_login(self.it_admin)
        response = self.client.get('/admin/wipe-data/')
        self.assertEqual(response.status_code, 200)

    def test_wipe_logic(self):
        self.client.force_login(self.it_admin)
        
        response = self.client.post('/admin/wipe-data/', {
            'confirm_string': 'WRONG',
            'manager_code': 'MGR-APPROVE'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Product.objects.exists())
        self.assertIn('confirm_string', response.context['form'].errors)

        # 2. Wrong Code
        response = self.client.post('/admin/wipe-data/', {
            'confirm_string': 'DELETE-ALL-DATA',
            'manager_code': 'WRONG'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Product.objects.exists())
        self.assertIn('manager_code', response.context['form'].errors)

        # 3. Success
        response = self.client.post('/admin/wipe-data/', {
            'confirm_string': 'DELETE-ALL-DATA',
            'manager_code': 'MGR-APPROVE'
        }, follow=True)
        
        self.assertFalse(Product.objects.exists())
        self.assertFalse(Flight.objects.exists())
        self.assertContains(response, "All business data has been wiped.")
