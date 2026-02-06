from django.db import models
from django.db.models import Sum

class Product(models.Model):
    # Old fields
    name = models.CharField(max_length=200, null=True, blank=True)
    # Replaced 'code' with components
    country_code = models.CharField(max_length=3, verbose_name="Country (3)")
    days_count = models.CharField(max_length=2, verbose_name="Days (2)", null=True, blank=True)
    unique_seq = models.CharField(max_length=2, verbose_name="Unique Seq (2)")

    description = models.TextField(blank=True)

    @property
    def code(self):
        """Reconstruct: {Country}{Unique} e.g. JPNH4"""
        return f"{self.country_code}{self.unique_seq}".upper()

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
    # Auto-detected from tour_code
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Mandatory Tour Code
    tour_code = models.CharField(max_length=50, unique=True, help_text="Format: JPN26A06H4 (Country+YY+M+DD+Seq)")

    # New Field from Enhanced Import
    class Language(models.TextChoices):
        CHINESE = 'C', 'Cantonese'
        MANDARIN = 'M', 'Mandarin'
        ENGLISH = 'E', 'English'
        OTHER = 'O', 'Other'

    language = models.CharField(max_length=2, choices=Language.choices, default=Language.MANDARIN, blank=True, null=True)

    total_spots = models.PositiveIntegerField(default=20, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, blank=True)

    def __str__(self):
        return f"{self.tour_code}"

    def save(self, *args, **kwargs):
        # Auto-parse start_date from tour_code
        if self.tour_code and not self.start_date:
            import re
            import datetime
            # Regex: {XXX}{YY}{M}{DD}{ZZ}
            # M: 1-9, A, B, C
            match = re.match(r"^([A-Z]{3})(\d{2})([1-9ABC])(\d{2})([A-Z0-9]{2})$", self.tour_code.upper())
            if match:
                country, yy, m_char, dd, seq = match.groups()

                # Month Map
                month_map = {
                    'A': 10, 'B': 11, 'C': 12
                }
                # If digit 1-9
                if m_char.isdigit():
                    month = int(m_char)
                else:
                    month = month_map.get(m_char, 1) # Default to 1 if weird? Regex protects us.

                year = 2000 + int(yy) # Assumption 20XX
                day = int(dd)

                try:
                    self.start_date = datetime.date(year, month, day)
                except ValueError:
                    pass # Invalid date (e.g. Feb 30)

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
        TWIN = 'TWIN', 'Twin Room'
        UPGRADE = 'UPGRADE', 'Upgrade Class'
        INFANT = 'INFANT', 'Infant'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        BOOKED = 'BOOKED', 'Booked'
        HELD = 'HELD', 'Held'

    tour_instance = models.ForeignKey(TourInstance, on_delete=models.CASCADE, related_name='bookings')
    booking_id = models.CharField(max_length=50, unique=True, blank=True, help_text="e.g. JPN06...-S-01")
    booking_type = models.CharField(max_length=20, choices=Type.choices, default=Type.DOUBLE, blank=True, null=True)

    # New Field from Enhanced Import
    room_type = models.CharField(max_length=50, blank=True, help_text="Specific room info e.g. Twin, Single, Special")

    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Specific price for this booking unit")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE, blank=True)

    # Optional: link to who booked it (denormalization or convenience)
    # The source of truth is the InvoiceItem -> TourBooking link.

    def __str__(self):
        return f"{self.booking_id} ({self.booking_type})"

    def save(self, *args, **kwargs):
        # Auto-gen booking_id if not present
        if not self.booking_id and self.tour_instance:
            # Format: {TourCode}-{Lang}-{Serial}
            # Serial: 3 digits, sequential per tour instance
            tour_code = self.tour_instance.tour_code
            lang = self.tour_instance.language or 'M'

            # Simple Count + 1 (Note: Not concurrency safe but acceptable for current scope)
            # Filter all bookings for this instance to find max? Or just count?
            # Count might reuse if deleted. Ideally find max index.
            # Using count + 1 for now as per plan.
            existing_count = TourBooking.objects.filter(tour_instance=self.tour_instance).count()
            serial = existing_count + 1

            self.booking_id = f"{tour_code}-{lang}-{serial:03d}"

        super().save(*args, **kwargs)
