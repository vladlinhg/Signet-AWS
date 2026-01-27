from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Invoice, InvoiceNote

def is_accountant_or_manager(user):
    return user.is_authenticated and (user.role in ['ACCOUNTANT', 'MANAGER'] or user.is_superuser)

@login_required
def dashboard_router(request):
    user = request.user
    if user.role == 'SALES':
        return redirect('sales_dashboard')
    elif user.role == 'MARKETING':
        return redirect('marketing_dashboard')
    elif user.role in ['ACCOUNTANT', 'MANAGER'] or user.is_superuser:
        return redirect('accountant_dashboard')
    else:
        # Fallback for Sales or others
        return redirect('admin:index')

@login_required
@user_passes_test(is_accountant_or_manager)
def accountant_dashboard(request):
    """
    Main dashboard for the Accountant.
    Shows 'Submitted' invoices (Priority) and recent 'Verified' ones.
    """
    # Priority: Submitted invoices needing audit
    audit_queue = Invoice.objects.filter(status=Invoice.Status.SUBMITTED).order_by('created_at')
    
    # Secondary: Needs fix (waiting on sales) or Draft (monitoring)
    # For MVP, mostly focus on Audit Queue
    
    # Stats
    context = {
        'audit_queue': audit_queue,
        'verified_count': Invoice.objects.filter(status=Invoice.Status.VERIFIED).count(),
        'pending_count': audit_queue.count(),
    }
    return render(request, 'sales/dashboard.html', context)

@login_required
@user_passes_test(is_accountant_or_manager)
def invoice_audit_detail(request, pk):
    """
    Detailed view to audit an invoice.
    Allows Approve (Verify) or Reject (Needs Fix).
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        note_content = request.POST.get('note')
        
        if action == 'approve':
            invoice.status = Invoice.Status.VERIFIED
            invoice.save()
            messages.success(request, f"Invoice {invoice.invoice_number} Verified.")
            return redirect('accountant_dashboard')
            
        elif action == 'reject':
            if not note_content:
                messages.error(request, "You must provide a note when requesting fixes.")
            else:
                invoice.status = Invoice.Status.NEEDS_FIX
                invoice.save()
                # Create Note
                InvoiceNote.objects.create(
                    invoice=invoice,
                    author=request.user,
                    content=note_content
                )
                messages.warning(request, f"Invoice returned to Sales with note.")
                return redirect('accountant_dashboard')

    context = {
        'invoice': invoice,
    }
    return render(request, 'sales/audit_detail.html', context)

# --- Marketing / Manager Analytics ---

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from apps.currencies.models import Currency, ExchangeRate
import json

# --- Sales Dashboard ---

@login_required
def sales_dashboard(request):
    """
    Dedicated dashboard for Sales Agents.
    Shows: Wallet (My Sales), Recent Invoices, Quick Actions.
    """
    user = request.user
    # 1. Wallet Logic: Group My Verified Sales by Currency
    # We want: [{'currency': 'USD', 'total': 5000}, {'currency': 'CAD', 'total': 2000}]
    wallet_data = Invoice.objects.filter(sales_agent=user, status=Invoice.Status.VERIFIED) \
        .values('currency__code', 'currency__symbol') \
        .annotate(total=Sum('total_amount')) \
        .order_by('currency__code')
    
    # 2. Pending Count
    pending_count = Invoice.objects.filter(sales_agent=user, status__in=[Invoice.Status.DRAFT, Invoice.Status.NEEDS_FIX]).count()
    
    # 3. Recent Invoices
    recent_invoices = Invoice.objects.filter(sales_agent=user).order_by('-created_at')[:10]

    context = {
        'wallet_data': wallet_data,
        'pending_count': pending_count,
        'recent_invoices': recent_invoices,
    }
    return render(request, 'sales/sales_dashboard.html', context)


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
    rate = 1.0
    if not target_currency.is_base:
        # Check ExchangeRate model: Base -> Target? 
        # My model is `rate_to_base` (Foreign -> Base). 
        # So to go Base -> Foreign, we divide by rate_to_base.
        # Example: USD rate_to_base = 0.75 (1 USD = 0.75 CAD)
        # So 1 CAD = 1 / 0.75 USD = 1.33 USD
        latest_rate = ExchangeRate.objects.filter(currency=target_currency).first()
        if latest_rate:
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
    from apps.sales.models import InvoiceItem
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
        'currencies': Currency.objects.all(),
        'current_currency': target_currency,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'prod_labels': prod_labels,
        'prod_values': prod_values,
    }
    return render(request, 'sales/marketing/dashboard.html', context)
