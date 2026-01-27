from django.urls import path
from engine.records.invoices.views import invoice_detail, invoice_audit_detail

urlpatterns = [
    # Read-Only View (Edit via Admin)
    path('view/<int:pk>/', invoice_detail, name='invoice_detail'),
    
    # Audit Workflow (Accountant)
    path('audit/<int:pk>/', invoice_audit_detail, name='invoice_audit_detail'),
]
