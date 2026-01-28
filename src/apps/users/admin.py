from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ('username',)
    list_display = ('username', 'email', 'role', 'department', 'agent_profile')
    list_editable = ('role', 'department', 'agent_profile')
    list_filter = ('role', 'department', 'is_staff', 'is_active')
    readonly_fields = ('is_manager', 'last_login', 'date_joined')

    fieldsets = UserAdmin.fieldsets + (
        ('Signet Info', {'fields': ('role', 'department', 'agent_profile', 'is_manager')}),
    )
