from django.contrib import admin
from .models import Invoice, InvoiceItem, InvoiceNote

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

class InvoiceNoteInline(admin.StackedInline):
    model = InvoiceNote
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'client', 'sales_agent', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'sales_agent', 'created_at')
    inlines = [InvoiceItemInline, InvoiceNoteInline]
    readonly_fields = ('created_at',)

@admin.register(InvoiceNote)
class InvoiceNoteAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'author', 'created_at')
