from django.test import TestCase, Client as TestClient
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.tours.models import Product
from apps.clients.models import Client
from apps.flights.models import Flight
import json

User = get_user_model()

class ImportInteractiveTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.manager = User.objects.create_user(username='mgr', password='pwd', role='MANAGER')
        self.client.force_login(self.manager)

    def test_client_duplicate_detection(self):
        Client.objects.create(first_name='John', last_name='Doe', email='old@ex.com')
        csv_content = b"first,last,email,phone\nJohn,Doe,new@ex.com,555\nJane,Doe,jane@ex.com,555"
        file = SimpleUploadedFile("clients.csv", csv_content, content_type="text/csv")
        
        response = self.client.post('/import/', {
            'import_type': 'clients',
            'file': file
        })
        
        # DEBUG BLOCK
        if 'form' in response.context and response.context['form'].errors:
            print("FOrm Error:", response.context['form'].errors)
        if 'messages' in response.context:
            for m in response.context['messages']:
                print("Msg:", m.message)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/import_preview.html', "Failed to render preview.")
        
        preview_data = response.context['preview_data']
        self.assertEqual(len(preview_data), 2)
