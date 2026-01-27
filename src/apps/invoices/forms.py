from django import forms
from .models import Invoice, InvoiceItem
from apps.clients.models import Client
from apps.currencies.models import Currency

class InvoiceForm(forms.ModelForm):
    """
    Form for Sales Agents to create a new Invoice.
    """
    class Meta:
        model = Invoice
        fields = ['client', 'currency'] # sales_agent is auto-set
        widgets = {
            'client': forms.Select(attrs={'class': 'mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md'}),
            'currency': forms.Select(attrs={'class': 'mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional: Filter clients or order them
        self.fields['client'].queryset = Client.objects.all().order_by('name')
        if Currency.objects.exists():
             self.fields['currency'].initial = Currency.objects.filter(is_base=True).first()
