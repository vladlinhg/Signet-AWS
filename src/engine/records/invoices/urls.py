from django.urls import path
from engine.records.invoice import views
from engine.pages.sales import views as sales_views

# Note: The 'sales_dashboard' is now in engine.pages.sales, 
# but we might keep the /sales/ entry point or just have simple /invoice/ URLs?
# User requested: "/role/page" or "/entities/page".
# So:
# /sales/dashboard/ -> handled by config/urls.py
# /invoices/new/ -> handled here?
# Let's map entity actions here.

urlpatterns = [
    # Invoice Actions
    path('new/', views.create_invoice, name='create_invoice'),
    path('invoice/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoice/<int:pk>/edit/', views.invoice_update, name='invoice_update'),
    path('invoice/<int:pk>/audit/', views.invoice_audit_detail, name='invoice_audit_detail'),
    
    # Legacy Router (if needed)
    # path('dashboard/', sales_views.dashboard_router, name='dashboard_router'),
]
