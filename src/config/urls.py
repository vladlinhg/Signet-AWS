from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

from apps.core.views import import_data_view, wipe_data_confirm, generate_data_view
from engine.pages.sales.views import sales_dashboard
from engine.pages.marketing.views import marketing_dashboard
from engine.pages.accountant.views import accountant_dashboard
from engine.pages.manager.views import manager_dashboard
from engine.pages.router import dashboard_router

urlpatterns = [
    path('import/', import_data_view, name='import_data'),
    path('admin/wipe-data/', wipe_data_confirm, name='wipe_data'),
    path('admin/generate-data/', generate_data_view, name='generate_data'),
    
    # Custom Login
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/login/', RedirectView.as_view(url='/login/', permanent=False)),
    
    path('admin/', admin.site.urls),
    
    # --- Role Based Pages ---
    path('sales/dashboard/', sales_dashboard, name='sales_dashboard'),
    path('manager/dashboard/', manager_dashboard, name='manager_dashboard'),
    path('marketing/dashboard/', marketing_dashboard, name='marketing_dashboard'),
    path('accountant/dashboard/', accountant_dashboard, name='accountant_dashboard'),

    # --- Universal Redirects (Legacy Roots) ---
    path('sales/', RedirectView.as_view(pattern_name='sales_dashboard', permanent=False)),
    path('manager/', RedirectView.as_view(pattern_name='manager_dashboard', permanent=False)),
    path('marketing/', RedirectView.as_view(pattern_name='marketing_dashboard', permanent=False)),
    path('accountant/', RedirectView.as_view(pattern_name='accountant_dashboard', permanent=False)),

    # --- Entity Records ---
    # /invoices/view/<id>/ handled here
    path('invoices/', include('apps.invoices.urls')),
    path('clients/', include('apps.clients.urls')),
    path('flights/', include('apps.flights.urls')),
    path('tours/', include('apps.tours.urls')),
    
    # Global Entry
    path('dashboard/', dashboard_router, name='global_dashboard'),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
]
