from django.db import models
from django.db.models import Sum

class Product(models.Model):
    # Old fields
    name = models.CharField(max_length=200)
    # Replaced 'code' with components
    country_code = models.CharField(max_length=3, verbose_name="Country (3)")
    days_count = models.CharField(max_length=2, verbose_name="Days (2)")
    unique_seq = models.CharField(max_length=3, verbose_name="Unique Seq (3)")

    description = models.TextField(blank=True)

    @property
    def code(self):
        """Reconstruct: {Country}{Days}{Unique}"""
        return f"{self.country_code}{self.days_count}{self.unique_seq}".upper()

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        self.country_code = self.country_code.upper()
        self.unique_seq = self.unique_seq.upper()
        super().save(*args, **kwargs)

class TourInstance(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        FULL = 'FULL', 'Full'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='instances')
    start_date = models.DateField()
    end_date = models.DateField()

    # Auto-Generated
    instance_code = models.CharField(max_length=50, unique=True, blank=True)

    # New Field from Enhanced Import
    class Language(models.TextChoices):
        CHINESE = 'C', 'Chinese'
        MANDARIN = 'M', 'Mandarin'
        ENGLISH = 'E', 'English'
        OTHER = 'O', 'Other'

    language = models.CharField(max_length=2, choices=Language.choices, default=Language.MANDARIN)

    total_spots = models.PositiveIntegerField(default=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    def __str__(self):
        return f"{self.instance_code or 'New'}"

    def save(self, *args, **kwargs):
        if not self.instance_code and self.product and self.start_date:
            # Format: {ProductCode}{StartDate (DDMMMYY)}
            # Example: JPN0600111NOV26
            date_str = self.start_date.strftime('%d%b%y').upper()
            self.instance_code = f"{self.product.code}{date_str}"
        super().save(*args, **kwargs)

    @property
    def booked_spots(self):
        # Refactor: Count bookings that are marked as BOOKED
        return self.bookings.filter(status='BOOKED').count()

    @property
    def available_spots(self):
        return self.total_spots - self.booked_spots

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")

class TourBooking(models.Model):
    """
    Represents a specific unit of inventory (e.g. a 'Seat' or 'Room') on a TourInstance.
    This is what gets linked to an InvoiceItem.
    """
    class Type(models.TextChoices):
        SINGLE = 'SINGLE', 'Single Room'
        DOUBLE = 'DOUBLE', 'Double Room'
        UPGRADE = 'UPGRADE', 'Upgrade Class'
        INFANT = 'INFANT', 'Infant'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        BOOKED = 'BOOKED', 'Booked'
        HELD = 'HELD', 'Held'

    tour_instance = models.ForeignKey(TourInstance, on_delete=models.CASCADE, related_name='bookings')
    booking_id = models.CharField(max_length=50, unique=True, help_text="e.g. JPN06...-S-01")
    booking_type = models.CharField(max_length=20, choices=Type.choices, default=Type.DOUBLE)

    # New Field from Enhanced Import
    room_type = models.CharField(max_length=50, blank=True, help_text="Specific room info e.g. Twin, Single, Special")

    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Specific price for this booking unit")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    # Optional: link to who booked it (denormalization or convenience)
    # The source of truth is the InvoiceItem -> TourBooking link.

    def __str__(self):
        return f"{self.booking_id} ({self.booking_type})"

    def save(self, *args, **kwargs):
        # Auto-gen booking_id if not present would happen in the generator script,
        # but we can add safeguards here if needed.
        super().save(*args, **kwargs)
