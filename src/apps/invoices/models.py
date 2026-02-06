from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.clients.models import Client, PaymentMethod
from apps.tours.models import TourBooking
from apps.flights.models import FlightTicket
from apps.currencies.models import Currency

class AddonService(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    default_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.title

class Coupon(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        USED = 'USED', 'Used'
        EXPIRED = 'EXPIRED', 'Expired'

    code = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Numeric value only")
    expiry_date = models.DateField(null=True, blank=True)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='coupons')
    invoice_used = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_coupons')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    date_used = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code

class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft (No Deposit)'
        DEPOSIT = 'DEPOSIT', 'Deposit Paid'
        INVOICED = 'INVOICED', 'Invoiced'
        PAID = 'PAID', 'Paid in Full'
        CANCELLED = 'CANCELLED', 'Cancelled'
        MOVED = 'MOVED', 'Moved'
        SPLIT = 'SPLIT', 'Split'
        PENALTY = 'PENALTY', 'Penalty'

    class Language(models.TextChoices):
        ENGLISH = 'EN', 'English'
        MANDARIN = 'ZH', 'Mandarin'
        CANTONESE = 'MX', 'Cantonese'

    class Tag(models.TextChoices):
        AUDIT_SUBMITTED = 'AUDIT_SUBMITTED', 'Audit Submitted'
        VERIFIED = 'VERIFIED', 'Verified'
        NEEDS_FIX = 'NEEDS_FIX', 'Needs Fix'
        CLARIFY = 'CLARIFY', 'Clarify'

    booking_number = models.CharField(max_length=50, unique=True, help_text="Mandatory Booking Reference")
    invoice_number = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="Generated when status is INVOICED or PAID")

    sales_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales_invoices', verbose_name="Sales")
    external_agent = models.ForeignKey('agents.Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_invoices', verbose_name="Agency")

    created_at = models.DateTimeField(default=timezone.now)
    created_time = models.TimeField(default='00:00:00')
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.MANDARIN)
    tag = models.CharField(max_length=20, choices=Tag.choices, null=True, blank=True)
    group_no = models.CharField(max_length=50, blank=True)
    has_flight_intinerary = models.BooleanField(default=False, help_text="Client itinerary must be confirmed (flight info required)")

    supporting_documents = models.ManyToManyField('documents.SupportingDocument', blank=True, related_name='invoices')
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)

    @property
    def total_amount(self):
        return sum(item.get_total() for item in self.items.all())

    @property
    def amount_paid(self):
        return sum(payment.amount for payment in self.payments.all())

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    def save(self, *args, **kwargs):
        if not self.booking_number:
             # Auto-Gen Booking Number: BK-{Year}-{Random}
             import uuid
             year = timezone.now().year
             self.booking_number = f"BK-{year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking_number} ({self.get_status_display()})"

class InvoicePayment(models.Model):
    class PaymentType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit'
        FULL_PAYMENT = 'FULL_PAYMENT', 'Full Payment'
        PAYMENT = 'PAYMENT', 'Payment'

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_type} - {self.amount}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    # Refactor: Client is mandatory here now
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)

    description = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Links
    # Refactor: tour_instance replaced by tour_booking
    tour_booking = models.ForeignKey(TourBooking, on_delete=models.SET_NULL, null=True, blank=True)
    flight_ticket = models.ForeignKey(FlightTicket, on_delete=models.SET_NULL, null=True, blank=True)
    addon_service = models.ForeignKey(AddonService, on_delete=models.SET_NULL, null=True, blank=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    total_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def get_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.description} ({self.total_price})"

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
