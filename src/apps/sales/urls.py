from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_router, name='dashboard'),
    path('accountant/', views.accountant_dashboard, name='accountant_dashboard'),
    path('sales/', views.sales_dashboard, name='sales_dashboard'),
    path('marketing/', views.marketing_dashboard, name='marketing_dashboard'),
    path('invoice/<int:pk>/audit/', views.invoice_audit_detail, name='invoice_audit_detail'),
]
