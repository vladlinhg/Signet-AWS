from django.db import models

class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True, help_text="ISO 4217 Code (e.g. USD)")
    symbol = models.CharField(max_length=5, help_text="Currency Symbol (e.g. $)")
    name = models.CharField(max_length=50, help_text="Full Name (e.g. US Dollar)")
    is_base = models.BooleanField(default=False, help_text="Is this the base reporting currency? (Usually CAD)")

    def __str__(self):
        return self.code

class ExchangeRate(models.Model):
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates')
    date = models.DateField(help_text="Effective rate date")
    rate_to_base = models.DecimalField(max_digits=10, decimal_places=4, help_text="Conversion rate to Base Currency")

    class Meta:
        unique_together = ('currency', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.currency.code} : {self.rate_to_base} ({self.date})"
