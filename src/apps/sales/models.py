from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.clients.models import Client
from apps.tours.models import TourInstance
from apps.flights.models import FlightTicket
from apps.currencies.models import Currency

class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted for Audit'
        NEEDS_FIX = 'NEEDS_FIX', 'Needs Fix'
        VERIFIED = 'VERIFIED', 'Verified'
        PAID = 'PAID', 'Paid'

    invoice_number = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='invoices')
    sales_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales_invoices')
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)

    def update_total(self):
        """Recalculates total_amount based on items."""
        total = sum(item.get_total() for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Simple Auto-Gen: INV-{Year}-{Count+1}
            # A real system might use a sequence table or UUID
            count = Invoice.objects.count() + 1
            self.invoice_number = f"INV-{timezone.now().year}-{count:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.client} ({self.get_status_display()})"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Links
    tour_instance = models.ForeignKey(TourInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_items')
    flight_ticket = models.ForeignKey(FlightTicket, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_items')

    def get_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.description} (x{self.quantity})"

class InvoiceNote(models.Model):
    """
    Audit trail for communication between Accountant and Sales.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note by {self.author} on {self.created_at}"
