from django.contrib import admin
from .models import Currency, ExchangeRate

class ExchangeRateInline(admin.TabularInline):
    model = ExchangeRate
    extra = 1

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol', 'is_base')
    inlines = [ExchangeRateInline]
