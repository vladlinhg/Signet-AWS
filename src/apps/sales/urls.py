from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.accountant_dashboard, name='accountant_dashboard'),
    path('invoice/<int:pk>/audit/', views.invoice_audit_detail, name='invoice_audit_detail'),
]
