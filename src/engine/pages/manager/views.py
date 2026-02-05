from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from apps.invoices.models import Invoice, InvoicePayment, InvoiceItem
from apps.currencies.models import Currency
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def is_manager(user):
    return user.is_authenticated and (user.role == 'MANAGER' or user.is_superuser)

@login_required
@user_passes_test(is_manager)
def manager_dashboard(request):
    # 1. Filters
    # Currency (Global Filter)
    selected_currency_code = request.GET.get('currency', 'CAD')
    available_currencies = Currency.objects.all()

    # Calculation Mode (Anticipated vs Actual)
    calc_mode = request.GET.get('mode', 'anticipated') # 'anticipated' or 'actual'

    # Date Filter
    range_type = request.GET.get('range', 'year')
    today = timezone.now().date()
    start_date = today

    if range_type == 'week':
        start_date = today - timedelta(days=7)
    elif range_type == 'month':
        start_date = today - timedelta(days=30)
    elif range_type == 'quarter':
        start_date = today - timedelta(days=90)
    elif range_type == 'year':
        start_date = today - timedelta(days=365)

    # 2. Querysets
    # Global Scope: Filter by Currency & Date
    # Note: If calc_mode is actual, we filter payments by currency.
    # Invoices have a currency field. Payments rely on Invoice currency usually?
    # Or assuming payments match invoice currency.

    invoices = Invoice.objects.filter(
        currency__code=selected_currency_code,
        created_at__date__gte=start_date
    )

    # 3. Total Revenue Calculation
    total_revenue = 0
    if calc_mode == 'actual':
        # Sum of 'InvoicePayment' where invoice is in the filtered list
        # We assume payments are in the same currency as invoice.
        payments = InvoicePayment.objects.filter(
            invoice__currency__code=selected_currency_code,
            date__gte=start_date
        )
        total_revenue = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Sum of 'InvoiceItem' (Anticipated)
        items = InvoiceItem.objects.filter(invoice__in=invoices)
        total_revenue = sum(item.get_total() for item in items)


    # 4. Global Activity Table (Recent 50)
    # Filter by currency to keep context relevant? Or true global?
    # User said "Global Activity", but usually implies "relevant to what I'm looking at".
    # Let's filter by currency to avoid mixing symbols.
    recent_invoices = Invoice.objects.filter(currency__code=selected_currency_code)\
        .select_related('sales_agent', 'currency')\
        .prefetch_related('items', 'items__client', 'payments')\
        .order_by('-created_at')

    activity_data = []
    for inv in recent_invoices:
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

        # Payments Total
        pay_total = sum(p.amount for p in inv.payments.all())

        activity_data.append({
            'id': inv.id,
            'booking_number': inv.booking_number,
            'client_id': client.id if client else None,
            'client_name': client_name,
            'phone': client_phone,
            'email': client_email,
            'description': desc,
            'payments_total': pay_total,
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
        'total_revenue': total_revenue,
        'mode': calc_mode,
        'range': range_type,
        'activity_data': activity_data,
        'agent_stats': agent_stats,

        # Filters
        'available_currencies': available_currencies,
        'selected_currency_code': selected_currency_code,
    }
    return render(request, 'roles/manager/dashboard.html', context)
