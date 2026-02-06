from django.contrib import admin
from .models import Flight, FlightTicket, Airline, FlightInstance, Airport

@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')

class TicketInline(admin.TabularInline):
    model = FlightTicket
    extra = 1

@admin.register(Airline)
class AirlineAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ('code', 'airline', 'flight_number', 'departure_airport', 'arrival_airport')
    search_fields = ('airline__code', 'flight_number', 'departure_airport')
    # inlines = [TicketInline] - tickets now on Instance

@admin.register(FlightInstance)
class FlightInstanceAdmin(admin.ModelAdmin):
    list_display = ('flight_code', 'flight', 'departure_date', 'departure_time')
    list_filter = ('departure_date',)
    readonly_fields = ('flight_code',)
    inlines = [TicketInline]

@admin.register(FlightTicket)
class FlightTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_code', 'flight', 'seat_number', 'cabin_class')
    search_fields = ('ticket_code', 'flight__flight_code')
    readonly_fields = ('ticket_code',)
