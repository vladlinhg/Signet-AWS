from django.contrib import admin
from .models import Client, TravelDocument, City, Ethnicity, Address, TravelGroup

@admin.register(TravelGroup)
class TravelGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

class TravelDocumentInline(admin.StackedInline):
    model = TravelDocument
    extra = 0

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('street_number', 'street_name', 'city', 'country')

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'country_code')
    search_fields = ('name',)

@admin.register(Ethnicity)
class EthnicityAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(TravelDocument)
class TravelDocumentAdmin(admin.ModelAdmin):
    list_display = ('client', 'doc_type', 'doc_number', 'expiry_date')
    search_fields = ('client__first_name', 'client__last_name', 'doc_number')
    list_filter = ('doc_type', 'expiry_date')

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'origin', 'ethnicity')
    search_fields = ('first_name', 'last_name', 'email')
    inlines = [TravelDocumentInline]
