from django.contrib import admin
from .models import Client, TravelDocument

class TravelDocumentInline(admin.StackedInline):
    model = TravelDocument
    extra = 0

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone')
    search_fields = ('first_name', 'last_name', 'email')
    inlines = [TravelDocumentInline]
