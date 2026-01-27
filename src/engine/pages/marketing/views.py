from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from apps.invoices.models import Invoice, InvoiceItem
from apps.currencies.models import Currency, ExchangeRate
from django.contrib.auth import get_user_model

User = get_user_model()

def is_marketing_or_manager(user):
    return user.is_authenticated and (user.role in ['MARKETING', 'MANAGER'] or user.is_superuser)

@login_required
@user_passes_test(is_marketing_or_manager)
def marketing_dashboard(request):
    """
    Analytics Dashboard.
    Supports currency toggle via ?currency=CODE
    """
    # 1. Currency Logic
    target_currency_code = request.GET.get('currency', 'CAD')
    target_currency = get_object_or_404(Currency, code=target_currency_code)
    
    # Get Rate (Base -> Target)
    # Simplified: Find latest rate. In real app, we'd convert each transaction by its date.
    # Here we assume all totals are in BASE (CAD) and we convert the final aggregate.
    # 1. Global Wallet (All Verified Sales)
    wallet_data = Invoice.objects.filter(status=Invoice.Status.VERIFIED) \
        .values('currency__code', 'currency__symbol') \
        .annotate(total=Sum('total_amount')) \
        .order_by('currency__code')
        
    # Rate Logic for Charts (Approximate to Chosen Currency)
    rate = 1.0
    if not target_currency.is_base:
        latest_rate = ExchangeRate.objects.filter(currency=target_currency).first()
        if latest_rate and latest_rate.rate_to_base:
            # rate_to_base is Foreign -> Base. 
            # To go Base -> Foreign (Chart is in Base Sum), we divide.
            rate = 1 / float(latest_rate.rate_to_base)
    
    # 2. Monthly Sales (Verified Only)
    sales_qs = Invoice.objects.filter(status=Invoice.Status.VERIFIED)
    monthly_data = sales_qs.annotate(month=TruncMonth('created_at')).values('month').annotate(total=Sum('total_amount')).order_by('month')
    
    chart_labels = []
    chart_values = []
    for entry in monthly_data:
        if entry['month']:
            chart_labels.append(entry['month'].strftime('%b %Y'))
            # Convert
            val = float(entry['total']) * rate
            chart_values.append(round(val, 2))

    # 3. Top Products
    # We need InvoiceItems -> TourInstance -> Product
    top_products_qs = InvoiceItem.objects.filter(invoice__status=Invoice.Status.VERIFIED).values('tour_instance__product__name').annotate(revenue=Sum('unit_price')).order_by('-revenue')[:5]
    
    prod_labels = []
    prod_values = []
    for entry in top_products_qs:
        name = entry['tour_instance__product__name']
        if name:
            prod_labels.append(name)
            val = float(entry['revenue']) * rate
            prod_values.append(round(val, 2))

    context = {
        'wallet_data': wallet_data,
        'currencies': Currency.objects.all(),
        'current_currency': target_currency,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'prod_labels': prod_labels,
        'prod_values': prod_values,
    }
    return render(request, 'roles/marketing/dashboard.html', context)
