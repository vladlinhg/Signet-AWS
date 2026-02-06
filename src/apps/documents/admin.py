from django.contrib import admin
from django.utils.html import format_html
from .models import SupportingDocument

@admin.register(SupportingDocument)
class SupportingDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'file_preview')
    search_fields = ('title', 'description')
    readonly_fields = ('file_preview',)

    def file_preview(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank" class="button">Download / Preview</a>', obj.file.url)
        return "No File"
    file_preview.short_description = "Preview"
    file_preview.allow_tags = True
