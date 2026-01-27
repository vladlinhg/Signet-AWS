from django.contrib import admin
from .models import Flight, FlightTicket

class TicketInline(admin.TabularInline):
    model = FlightTicket
    extra = 1

@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ('code', 'flight_number', 'departure_airport', 'arrival_airport', 'departure_date')
    search_fields = ('code', 'flight_number', 'airline_code')
    inlines = [TicketInline]

@admin.register(FlightTicket)
class FlightTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_code', 'flight', 'seat_number', 'cabin_class')
    search_fields = ('ticket_code', 'flight__code')
