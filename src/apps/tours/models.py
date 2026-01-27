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
        return self.invoice_items.exclude(invoice__status='CANCELLED').aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def available_spots(self):
        return self.total_spots - self.booked_spots

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")

