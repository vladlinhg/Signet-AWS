from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from apps.invoices.models import Invoice
from django.contrib.auth import get_user_model

User = get_user_model()

def is_manager(user):
    return user.is_authenticated and (user.role == 'MANAGER' or user.is_superuser)

@login_required
@user_passes_test(is_manager)
def manager_dashboard(request):
    """
    Unified Dashboard for Managers (Remastered).
    Features: Global Filters (Status, Currency, Time), Performance Analytics.
    """
    from apps.currencies.models import Currency

    # --- 1. Filter Parameters ---
    selected_currency_code = request.GET.get('currency', 'CAD')
    selected_statuses = request.GET.getlist('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Defaults
    available_currencies = Currency.objects.all()
    if not selected_statuses:
        selected_statuses = [
            Invoice.Status.INVOICED,
            Invoice.Status.PAID,
            Invoice.Status.DEPOSIT,
            # Invoice.Status.CANCELLED # Optional default
        ]

    # --- 2. Base Query (Global Scope) ---
    # Global Scope = Currency + Time (IGNORING Status Status)
    global_qs = Invoice.objects.filter(currency__code=selected_currency_code)

    if date_from:
        global_qs = global_qs.filter(created_at__date__gte=date_from)
    if date_to:
        global_qs = global_qs.filter(created_at__date__lte=date_to)

    # --- 3. Global Metrics (Header / Top) ---
    # "Total Revenue" shown in Header should be GLOBAL (Currency + Time only)
    global_wallet_total = global_qs.aggregate(s=Sum('total_amount'))['s'] or 0

    # --- 4. Filtered Scope (Applied Statuses) ---
    # Performance Stats and "Below Filter" metrics respect the Status checkboxes
    metric_qs = global_qs.filter(status__in=selected_statuses)

    # Filtered Wallet (If we want to show it, or just use Global in header?)
    # User said "everything underneath the global filter is the number after filtered"
    filtered_wallet = metric_qs.aggregate(s=Sum('total_amount'))['s'] or 0

    # 5. Performance Panel (Leaderboard) - FILTERED
    agent_stats_raw = metric_qs.values('sales_agent__username', 'sales_agent__email') \
        .annotate(total_invoices=Count('id'), total_revenue=Sum('total_amount')) \
        .order_by('-total_invoices')[:5]

    agent_stats = []
    for entry in agent_stats_raw:
        agent_stats.append({
            'username': entry['sales_agent__username'],
            'email': entry['sales_agent__email'],
            'total_invoices': entry['total_invoices'],
            'total_revenue': entry['total_revenue']
        })

    # 6. Global Recent Activity (Keep global or filtered? Usually global context is nice)
    recent_invoices = Invoice.objects.all().select_related('sales_agent', 'currency').order_by('-created_at')[:10]

    context = {
        # Metrics
        'global_wallet_total': global_wallet_total,
        'filtered_wallet': filtered_wallet,
        'agent_stats': agent_stats,
        'recent_invoices': recent_invoices,

        # Filter Context
        'available_currencies': available_currencies,
        'selected_currency_code': selected_currency_code,
        'available_statuses': Invoice.Status.values,
        'selected_statuses': selected_statuses,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'roles/manager/dashboard.html', context)
