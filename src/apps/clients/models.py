from django.db import models

class Client(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.birth_date and self.birth_date > timezone.now().date():
            raise ValidationError("Birth date cannot be in the future.")

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
    file_attachment = models.FileField(upload_to='documents/', blank=True, null=True)

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.client}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.expiry_date and self.expiry_date < timezone.now().date():
            raise ValidationError("Document has already expired.")
