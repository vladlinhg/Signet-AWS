from django.contrib import admin
from .models import Product, TourInstance, TourBooking

@admin.register(TourBooking)
class TourBookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'tour_instance', 'status', 'booking_type')
    list_filter = ('status', 'tour_instance')
    search_fields = ('booking_id',)
    readonly_fields = ('booking_id',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')

@admin.register(TourInstance)
class TourInstanceAdmin(admin.ModelAdmin):
    list_display = ('tour_code', 'product', 'start_date', 'total_spots', 'booked_spots', 'status')
    list_filter = ('status', 'start_date')
    readonly_fields = ('booked_spots', 'start_date') # start_date is auto-detected
    search_fields = ('tour_code',)
