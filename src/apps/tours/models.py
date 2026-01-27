from django.db import models
from django.db.models import Sum

class Product(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class TourInstance(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        FULL = 'FULL', 'Full'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='instances')
    start_date = models.DateField()
    end_date = models.DateField()
    total_spots = models.PositiveIntegerField(default=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    def __str__(self):
        return f"{self.product.name} ({self.start_date})"

    @property
    def booked_spots(self):
        # Imports here to avoid circular dependencies if referenced back
        # Ideally this is an aggregation query
        # For now, let's assume InvoiceItem will have a related name 'invoice_items' or similar
        return self.invoice_items.exclude(invoice__status='CANCELLED').aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def available_spots(self):
        return self.total_spots - self.booked_spots
