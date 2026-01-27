from django.contrib import admin
from .models import Flight

@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ('airline', 'flight_number', 'pnr_code', 'departure_time')
    search_fields = ('pnr_code', 'ticket_number')
