from django.contrib import admin
from .models import Invoice, InvoiceItem, InvoiceNote, AddonService, Coupon

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

class InvoiceNoteInline(admin.StackedInline):
    model = InvoiceNote
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'sales_agent', 'status', 'total_amount', 'language', 'created_at')
    list_filter = ('status', 'sales_agent', 'language', 'created_at')
    inlines = [InvoiceItemInline, InvoiceNoteInline]
    readonly_fields = ('created_at',)

@admin.register(InvoiceNote)
class InvoiceNoteAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'author', 'created_at')

@admin.register(AddonService)
class AddonServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'default_price')
    search_fields = ('title',)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'amount', 'status', 'expiry_date')
    list_filter = ('status',)
    search_fields = ('code',)
