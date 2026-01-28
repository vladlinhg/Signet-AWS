from django.db import models

class Family(models.Model):
    name = models.CharField(max_length=200, help_text="e.g. 'The Smith Family'")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Families"

    def __str__(self):
        return self.name

class City(models.Model):
    name = models.CharField(max_length=100)
    country_code = models.CharField(max_length=3, blank=True, help_text="ISO 3-letter code if applicable")

    class Meta:
        verbose_name_plural = "Cities"
        ordering = ['name']

    def __str__(self):
        return self.name

class Ethnicity(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Ethnicities"
        ordering = ['name']

    def __str__(self):
        return self.name

class Address(models.Model):
    street_number = models.CharField(max_length=20)
    street_name = models.CharField(max_length=200)
    unit_number = models.CharField(max_length=20, blank=True)
    floor = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.street_number} {self.street_name}, {self.city}"

class Client(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'X', 'Other'

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    # Relationships
    family = models.ForeignKey(Family, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name='residents')

    # Details
    class Language(models.TextChoices):
        ENGLISH = 'EN', 'English'
        MANDARIN = 'ZH', 'Mandarin'
        CANTONESE = 'MX', 'Cantonese'

    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.OTHER)
    preferred_language = models.CharField(max_length=2, choices=Language.choices, default=Language.MANDARIN)

    # Refactored to FKs
    origin = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name='residents')
    ethnicity = models.ForeignKey(Ethnicity, on_delete=models.SET_NULL, null=True, blank=True, related_name='clients')

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    # Medical / Dietary
    dietary_restrictions = models.TextField(blank=True, help_text="JSON or text list of restrictions")
    allergies = models.TextField(blank=True, help_text="JSON or text list of allergies")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.birth_date and self.birth_date > timezone.now().date():
            raise ValidationError("Birth date cannot be in the future.")

class PaymentMethod(models.Model):
    class Type(models.TextChoices):
        CREDIT_CARD = 'CC', 'Credit Card'
        BANK_TRANSFER = 'BANK', 'Bank Transfer'
        CASH = 'CASH', 'Cash'
        OTHER = 'OTHER', 'Other'

    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=10, choices=Type.choices, default=Type.CREDIT_CARD)
    details = models.CharField(max_length=255, help_text="e.g. 'Visa ending 4242' or Account Number")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_method_type_display()} - {self.details}"

class TravelDocument(models.Model):
    class Type(models.TextChoices):
        PASSPORT = 'PASSPORT', 'Passport'
        VISA = 'VISA', 'Visa'
        PR_CARD = 'PR_CARD', 'PR Card'
        OTHER = 'OTHER', 'Other'

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=20, choices=Type.choices)
    doc_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    issuing_country = models.CharField(max_length=100, default='Unknown')
    file_attachment = models.FileField(upload_to='documents/', blank=True, null=True)

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.client}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.expiry_date and self.expiry_date < timezone.now().date():
            raise ValidationError("Document has already expired.")
