from django.contrib import admin
from .models import Product, TourInstance

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')

@admin.register(TourInstance)
class TourInstanceAdmin(admin.ModelAdmin):
    list_display = ('product', 'start_date', 'total_spots', 'booked_spots', 'status')
    list_filter = ('status', 'start_date')
    readonly_fields = ('booked_spots',) # logic property
