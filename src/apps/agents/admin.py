from django.contrib import admin
from .models import Agency, Agent
from apps.clients.admin import TravelDocumentInline

@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'business_number')
    search_fields = ('name', 'email')

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'agency', 'email')
    list_filter = ('agency', 'department')
    search_fields = ('first_name', 'last_name', 'email', 'agency__name')
    inlines = [TravelDocumentInline]
