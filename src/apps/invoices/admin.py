from django.contrib import admin
from django.utils.html import format_html
from .models import Invoice, InvoiceItem, InvoiceNote, AddonService, Coupon, InvoicePayment

class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 0

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

class InvoiceNoteInline(admin.StackedInline):
    model = InvoiceNote
    extra = 0

class SupportingDocumentInline(admin.TabularInline):
    model = Invoice.supporting_documents.through
    extra = 1
    verbose_name = "Attached Document"
    verbose_name_plural = "Attached Documents"
    show_change_link = True  # Adds "Change" (Edit) button

    readonly_fields = ('preview_link',)

    def preview_link(self, obj):
        # The object here is the "Through" model instance
        # It links Invoice (invoice_id) and SupportingDocument (supportingdocument_id)
        if obj.pk and obj.supportingdocument.file:
             return format_html('<a href="{}" target="_blank">Preview/Download</a>', obj.supportingdocument.file.url)
        return "-"
    preview_link.short_description = "Preview"

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('booking_number', 'invoice_number', 'sales_agent', 'status', 'total_amount', 'amount_paid', 'balance', 'created_at')
    list_filter = ('status', 'sales_agent', 'language', 'created_at')
    # Replaced filter_horizontal with inline for better CRUD (Edit/Delete buttons)
    inlines = [InvoiceItemInline, InvoicePaymentInline, SupportingDocumentInline, InvoiceNoteInline]
    inlines = [InvoiceItemInline, InvoicePaymentInline, SupportingDocumentInline, InvoiceNoteInline]
    readonly_fields = ()

    # Filter horizontal removed
    exclude = ('supporting_documents',)

@admin.register(InvoiceNote)
class InvoiceNoteAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'author', 'created_at')

@admin.register(AddonService)
class AddonServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'default_price')
    search_fields = ('title',)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'coupon_type', 'amount', 'status', 'expiry_date')
    list_filter = ('status', 'coupon_type')
    search_fields = ('code',)
