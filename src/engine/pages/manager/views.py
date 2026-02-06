from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum, F
from apps.invoices.models import Invoice, InvoicePayment, InvoiceItem
from apps.currencies.models import Currency
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from engine.services.global_filter import GlobalFilterService

User = get_user_model()

def is_manager(user):
    return user.is_authenticated and (user.role == 'MANAGER' or user.is_superuser)

@login_required
@user_passes_test(is_manager)
def manager_dashboard(request):
    # --- 1. Global Filter Service (Centralized) ---
    filter_service = GlobalFilterService(request)
    filter_context = filter_service.get_context()

    # Extract needed values
    selected_statuses = filter_context['selected_statuses']
    selected_currency_code = filter_context['selected_currency_code']
    start_date = filter_context['start_date']
    end_date = filter_context['end_date']
    calc_mode = filter_context['calc_mode']

    # 2. Querysets
    # Manager sees ALL invoices matching criteria (or scoped to permissions if needed later)
    invoices = Invoice.objects.filter(currency__code=selected_currency_code)

    # Apply Status Filter? Manager usually sees all, but Global Filter includes Status.
    # User Request: "Revenue ... despite status".
    # We remove the status filter from the base queryset so that Revenue and Activity List include all invoices (Cancelled, Draft, etc).
    # if selected_statuses:
    #     invoices = invoices.filter(status__in=selected_statuses)

    if start_date:
        invoices = invoices.filter(created_at__date__gte=start_date)
    if end_date:
        invoices = invoices.filter(created_at__date__lte=end_date)

    # 3. Total Revenue Calculation (COHORT LOGIC)
    total_revenue = 0
    if calc_mode == 'actual':
        # COHORT ACTUAL: Sum Payments linked to Invoices CREATED in this period.
        # Ignore Payment Date. Ignore Status.
        payments = InvoicePayment.objects.filter(invoice__in=invoices)
        total_revenue = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # COHORT ANTICIPATED: Sum Items linked to Invoices CREATED in this period.
        # Invoices are already filtered by date (Created At)
        items = InvoiceItem.objects.filter(invoice__in=invoices)

        # Optimization: Aggregate DB side like Marketing
        total_revenue = items.aggregate(s=Sum(F('unit_price') * F('quantity')))['s'] or 0


    # 4. Global Activity Table (Recent)
    # Filter by currency to keep context relevant
    recent_invoices = invoices\
        .select_related('sales_agent', 'currency')\
        .prefetch_related('items', 'items__client', 'payments')\
        .order_by('-created_at')

    activity_data = []
    # Limit to 500 for infinite scroll support
    for inv in recent_invoices[:500]:
        # Client Details from First Item
        first_item = inv.items.first()
        client = first_item.client if first_item else None

        client_name = "N/A"
        client_phone = ""
        client_email = ""

        if client:
            # Format: Mr./Mrs. Lastname/Firstname
            title = "Mr." if client.gender == 'M' else "Mrs."
            if client.gender == 'X': title = ""
            client_name = f"{title} {client.last_name}/{client.first_name}".strip()
            client_phone = client.phone
            client_email = client.email

        desc = first_item.description if first_item else "No Items"

        # Calculate Row Value based on Mode
        if calc_mode == 'actual':
            # Sum of payments
            row_value = sum(p.amount for p in inv.payments.all())
        else:
            # Anticipated: Sum of items
            # Recalculating item sum per invoice.
            # Could pre-annotate query, but simple loop is fine for 50 items.
            row_value = sum(item.unit_price * item.quantity for item in inv.items.all())

        activity_data.append({
            'id': inv.id,
            'booking_number': inv.booking_number,
            'client_id': client.id if client else None,
            'client_name': client_name,
            'phone': client_phone,
            'email': client_email,
            'description': desc,
            'amount_display': row_value, # Dynamic Value
            'status': inv.get_status_display(),
            'agent': inv.sales_agent.username
        })

    # 5. Agent Performance
    # Filter by Currency & Mode
    # Simplified: Top Agents by Invoice Count (in this currency, this period)
    agent_stats_qs = invoices.values('sales_agent__username')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:5]

    agent_stats = list(agent_stats_qs)

    context = {
        # Standard Filter Context
        **filter_context,

        'dashboard_title': 'Manager Overview',
        'dashboard_subtitle': 'Global activity, agent performance, and financial oversight.',

        'total_revenue': total_revenue,
        'activity_data': activity_data,
        'agent_stats': agent_stats,
    }
    return render(request, 'roles/manager/dashboard.html', context)
