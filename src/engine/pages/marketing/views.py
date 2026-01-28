from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncMonth
from apps.invoices.models import Invoice, InvoiceItem
from apps.currencies.models import Currency, ExchangeRate
from apps.clients.models import Client
from apps.flights.models import Flight, FlightTicket
from apps.tours.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()

def is_marketing_or_manager(user):
    return user.is_authenticated and (user.role in ['MARKETING', 'MANAGER'] or user.is_superuser)

@login_required
@user_passes_test(is_marketing_or_manager)
def marketing_dashboard(request):
    """
    Marketing Analytics "Command Center"
    Filters: Status (Multi), Currency (Strict), Time Range.
    Tabs: Invoice, Customer, Product, Flight.
    """
    # --- 1. Filter Parameters ---
    # Status: Default to 'real' revenue if empty
    selected_statuses = request.GET.getlist('status')
    if not selected_statuses:
        selected_statuses = [Invoice.Status.PAID, Invoice.Status.DEPOSIT, Invoice.Status.INVOICED, Invoice.Status.VERIFIED]

    # Currency: Default to CAD or first available
    selected_currency_code = request.GET.get('currency', 'CAD')

    # Date Range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Tab
    active_tab = request.GET.get('tab', 'invoices')

    # --- 2. Build Base QuerySet ---
    # Strict Filter: Only this currency, within dates, with these statuses
    base_qs = Invoice.objects.filter(
        currency__code=selected_currency_code,
        status__in=selected_statuses
    )

    if date_from:
        base_qs = base_qs.filter(created_at__date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(created_at__date__lte=date_to)

    # --- 3. Compute Stats Per Tab ---
    context = {
        'active_tab': active_tab,
        'selected_statuses': selected_statuses,
        'selected_currency_code': selected_currency_code,
        'date_from': date_from,
        'date_to': date_to,
        'available_currencies': Currency.objects.filter(invoice__isnull=False).distinct(), # Only used
        'available_statuses': [c[0] for c in Invoice.Status.choices],
    }

    # TAB 1: INVOICES (Revenue)
    if active_tab == 'invoices':
        # Metrics
        aggregates = base_qs.aggregate(
            total_rev=Sum('total_amount'),
            count=Count('id')
        )
        total_rev = aggregates['total_rev'] or 0
        count = aggregates['count'] or 0
        avg_val = total_rev / count if count > 0 else 0

        # Chart: Revenue by Month
        chart_qs = base_qs.annotate(month=TruncMonth('created_at')).values('month').annotate(val=Sum('total_amount')).order_by('month')

        context.update({
            'total_revenue': total_rev,
            'invoice_count': count,
            'avg_invoice_value': avg_val,
            'recent_invoices': base_qs.select_related('payment_method__family').order_by('-created_at')[:50],
            'chart_labels': [x['month'].strftime('%Y-%m') for x in chart_qs if x['month']],
            'chart_values': [float(x['val']) for x in chart_qs if x['month']]
        })

    # TAB 2: CUSTOMERS
    elif active_tab == 'customers':
        # Clients in these invoices (Fix: Use 'invoiceitem' not 'invoice_items')
        client_qs = Client.objects.filter(invoiceitem__invoice__in=base_qs).distinct()

        # New Clients (created within range? or just active?)
        # Let's count Active Travelers (unique clients in period)
        active_count = client_qs.count()

        # Recent Customers (for list)
        # Using client_qs might be slow if large, but filtered by invoice period is good.
        # Order by created_at desc (newest first)
        recent_customers = client_qs.order_by('-created_at')[:10]

        # Chart: New Clients by Month (Membership date) OR Active by Month
        # Let's show Active (Clients on invoices in that month)
        growth_qs = base_qs.annotate(month=TruncMonth('created_at')).values('month').annotate(cnt=Count('items__client', distinct=True)).order_by('month')

        context.update({
            'active_customers': active_count,
            'recent_customers': recent_customers,
            'top_families': [], # TODO: Complex Agg
            'chart_labels': [x['month'].strftime('%Y-%m') for x in growth_qs if x['month']],
            'chart_values': [x['cnt'] for x in growth_qs if x['month']]
        })

    # TAB 3: PRODUCTS (Tours)
    elif active_tab == 'products':
        # InvoiceItem -> TourBooking -> TourInstance -> Product
        # Filter items in base_qs
        items_qs = InvoiceItem.objects.filter(invoice__in=base_qs, tour_booking__isnull=False)

        # Metrics
        seats_sold = items_qs.count()
        product_rev = items_qs.aggregate(s=Sum('total_price'))['s'] or 0

        # Top Products
        # Group by ID and Name so we can link to it
        top_products = items_qs.values(
            'tour_booking__tour_instance__product__id',
            'tour_booking__tour_instance__product__name'
        ).annotate(
            sold=Count('id'),
            rev=Sum('total_price')
        ).order_by('-rev')[:10]

        context.update({
            'seats_sold': seats_sold,
            'product_revenue': product_rev,
            'top_products': top_products,
            'chart_labels': [x['tour_booking__tour_instance__product__name'] for x in top_products],
            'chart_values': [float(x['rev']) for x in top_products]
        })

    # TAB 4: FLIGHTS
    elif active_tab == 'flights':
        # Enhanced Logic:
        # 1. InvoiceItems (explicit flights or description match)
        flight_items = InvoiceItem.objects.filter(
            invoice__in=base_qs
        ).filter(description__icontains='TKT')

        # 2. FlightTickets (direct model)
        relevant_clients = Client.objects.filter(invoiceitem__invoice__in=base_qs).distinct()
        tickets_qs = FlightTicket.objects.filter(client__in=relevant_clients)

        # Metrics
        if flight_items.exists():
             # If we have items, use them for revenue
             flight_rev = flight_items.aggregate(s=Sum('total_price'))['s'] or 0
             tickets_sold = flight_items.count() # Use explicit item count
        else:
             # Fallback
             flight_rev = 0
             tickets_sold = tickets_qs.count()

        # Item List: Prioritize Linkable Objects (Tickets)
        # Even if we have invoice items, "Description" grouping prevents linking.
        # User wants "clickable" tickets.
        # So we prefer listing specific Tickets if available.
        if tickets_qs.exists():
            # List actual tickets
            # We need ID to link.
            recent_tickets = tickets_qs.select_related('flight__flight__airline').order_by('-id')[:10]
            # Transform to dict for template compat or pass QuerySet
            # Let's pass objects and handle in template (safer for linking)
            top_items = []
            context['recent_tickets'] = recent_tickets # New key for template
        else:
             # Fallback: Top Descriptions from Items (Unlinkable or link all to search?)
             # Just list descriptions as before
             top_items = flight_items.values('description').annotate(c=Count('id'), r=Sum('total_price')).order_by('-r')[:10]
             context['recent_tickets'] = None

        context.update({
            'tickets_sold': tickets_sold,
            'flight_revenue': flight_rev,
            'top_items': top_items # Kept for fallback compatibility
        })

    return render(request, 'roles/marketing/dashboard.html', context)
