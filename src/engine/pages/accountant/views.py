from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from apps.invoices.models import Invoice
from django.contrib.auth import get_user_model

User = get_user_model()

def is_accountant(user):
    return user.is_authenticated and (user.role == 'ACCOUNTANT' or user.is_superuser)

@login_required
@user_passes_test(is_accountant)
def accountant_dashboard(request):
    """
    Main dashboard for the Accountant (Remastered).
    Features: Global Filters (Status, Currency, Time), Status Breakdown.
    """
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from apps.currencies.models import Currency

    # --- 1. Filter Parameters ---
    selected_currency_code = request.GET.get('currency', 'CAD')
    selected_statuses = request.GET.getlist('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Defaults
    available_currencies = Currency.objects.all()
    if not selected_statuses:
        # Default Filter: Active statuses + Cancelled?
        # User wants to enable Cancelled by default if they select it,
        # but what is the initial land state?
        # Let's include everything commonly relevant.
        selected_statuses = [
            Invoice.Status.INVOICED,
            Invoice.Status.PAID,
            Invoice.Status.DEPOSIT,
            Invoice.Status.DRAFT,
            Invoice.Status.CANCELLED # Included for visibility as per recent request?
            # Or maybe let user select it.
        ]

    # --- 2. Base Query (Global Scope) ---
    # Global Scope = Currency + Date (IGNORING Status)
    global_qs = Invoice.objects.all().select_related('currency', 'sales_agent')
    global_qs = global_qs.filter(currency__code=selected_currency_code)

    if date_from:
        global_qs = global_qs.filter(created_at__date__gte=date_from)
    if date_to:
        global_qs = global_qs.filter(created_at__date__lte=date_to)

    # --- 3. Global Metrics (Header / Top) ---
    global_revenue = global_qs.aggregate(s=Sum('total_amount'))['s'] or 0
    global_invoice_count = global_qs.count()

    # --- 4. Status Breakdown ---
    # Breakdown of the Global Scope so user sees the distribution available
    status_counts = global_qs.values('status').annotate(count=Count('id')).order_by('status')
    status_map = {item['status']: item['count'] for item in status_counts}

    # --- 5. Filtered Scope (Applied Statuses) ---
    filtered_qs = global_qs.filter(status__in=selected_statuses).order_by('-created_at', '-total_amount')

    # --- 6. Filtered Metrics (Table Area) ---
    filtered_revenue = filtered_qs.aggregate(s=Sum('total_amount'))['s'] or 0
    filtered_invoice_count = filtered_qs.count()

    context = {
        # Data
        'invoices': filtered_qs,
        'status_map': status_map,

        # Metrics
        'global_revenue': global_revenue,
        'global_invoice_count': global_invoice_count,
        'filtered_revenue': filtered_revenue,
        'filtered_invoice_count': filtered_invoice_count,

        # Filter Context
        'available_currencies': available_currencies,
        'selected_currency_code': selected_currency_code,
        'available_statuses': Invoice.Status.values,
        'selected_statuses': selected_statuses,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'roles/accountant/dashboard.html', context)
