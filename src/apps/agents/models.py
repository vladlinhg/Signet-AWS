from django.db import models
from apps.clients.models import Client, Address

class Agency(models.Model):
    name = models.CharField(max_length=200)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    business_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Agent(Client):
    """
    Agent inherits from Client (Customer).
    Has additional business info and Agency link.
    """
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='agents')
    department = models.CharField(max_length=100, blank=True)
    employee_number = models.CharField(max_length=50, blank=True)
    sin_number = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = 'Agent'
        verbose_name_plural = 'Agents'
