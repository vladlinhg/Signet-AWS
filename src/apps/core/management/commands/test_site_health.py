from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class Command(BaseCommand):
    help = 'Smoke tests key URLs to ensure 200 OK.'

    def handle(self, *args, **options):
        client = Client()
        
        # 1. Login as Admin
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@test.com', 'adminpass')
        
        self.stdout.write("Logging in as admin...")
        login = client.login(username='admin', password='adminpass')
        if not login:
            self.stdout.write(self.style.ERROR("Login failed."))
            return

        # 2. Define URL Patterns to Test
        # We need IDs that exist. Assuming init_db_content ran.
        urls = [
            '/',
            '/sales/dashboard/',
            '/manager/dashboard/',
            '/marketing/dashboard/',
            '/accountant/dashboard/',
            # Admin
            '/admin/',
            # Entities (assuming ID 1 exists, usually fails if DB empty)
        ]
        
        # Add dynamic entity URLs only if objects exist
        from apps.invoices.models import Invoice
        from apps.clients.models import Client as ClientModel
        from apps.flights.models import Flight
        from apps.tours.models import TourInstance
        
        if Invoice.objects.exists():
            urls.append(reverse('invoice_detail', args=[Invoice.objects.first().pk]))
        if ClientModel.objects.exists():
            urls.append(reverse('client_detail', args=[ClientModel.objects.first().pk]))
        if Flight.objects.exists():
            urls.append(reverse('flight_detail', args=[Flight.objects.first().pk]))
        if TourInstance.objects.exists():
            urls.append(reverse('tour_detail', args=[TourInstance.objects.first().pk]))

        self.stdout.write(f"Testing {len(urls)} URLs...")
        
        failures = 0
        for url in urls:
            try:
                resp = client.get(url)
                if resp.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f"[OK] {url}"))
                elif resp.status_code == 302:
                    self.stdout.write(self.style.SUCCESS(f"[Redirect] {url} -> {resp.url}"))
                else:
                    self.stdout.write(self.style.ERROR(f"[FAIL] {url} - Status: {resp.status_code}"))
                    failures += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[ERR] {url} - {e}"))
                failures += 1

        if failures > 0:
            self.stdout.write(self.style.ERROR(f"\nCompleted with {failures} failures."))
            # check_html_links.py can be run here too
        else:
            self.stdout.write(self.style.SUCCESS("\nAll critical URLs are accessible."))
