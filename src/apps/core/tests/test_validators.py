from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from apps.tours.models import Product, TourInstance
from apps.clients.models import Client

class ValidatorTest(TestCase):
    def test_tour_dates(self):
        prod = Product.objects.create(name="Test", country_code="TST", days_count="05", unique_seq="999")
        # End before Start -> Should duplicate
        tour = TourInstance(
            product=prod,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() - timedelta(days=1)
        )
        with self.assertRaises(ValidationError):
            tour.clean()

    def test_client_birthday(self):
        # Future birthday -> Fail
        client = Client(
            first_name="Baby", 
            last_name="Doe",
            birth_date=timezone.now().date() + timedelta(days=365)
        )
        with self.assertRaises(ValidationError):
            client.clean()
