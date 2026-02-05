from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncMonth
from apps.invoices.models import Invoice, InvoiceItem, InvoicePayment
from apps.currencies.models import Currency
from apps.clients.models import Client
from apps.flights.models import FlightTicket
from django.contrib.auth import get_user_model

User = get_user_model()

def is_marketing_or_manager(user):
    return user.is_authenticated and (user.role in ['MARKETING', 'MANAGER'] or user.is_superuser)

@login_required
@user_passes_test(is_marketing_or_manager)
def marketing_dashboard(request):
    """
    Marketing Analytics "Command Center"
    Refactored for New Schema (Booking Number, InvoicePayment, TravelGroup).
    """
    # --- 1. Filter Parameters ---
    selected_statuses = request.GET.getlist('status')
    if not selected_statuses:
        selected_statuses = [Invoice.Status.PAID, Invoice.Status.DEPOSIT, Invoice.Status.INVOICED]

    # Currency
    selected_currency_code = request.GET.get('currency', 'CAD')

    # Date Range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Tab
    active_tab = request.GET.get('tab', 'invoices')

    # --- 2. Build Base QuerySet ---
    base_qs = Invoice.objects.filter(
        currency__code=selected_currency_code,
        status__in=selected_statuses
    )

    if date_from:
        base_qs = base_qs.filter(created_at__date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(created_at__date__lte=date_to)

    context = {
        'active_tab': active_tab,
        'selected_statuses': selected_statuses,
        'selected_currency_code': selected_currency_code,
        'date_from': date_from,
        'date_to': date_to,
        'available_currencies': Currency.objects.filter(invoice__isnull=False).distinct(),
        'available_statuses': Invoice.Status.values,
    }

    # TAB 1: INVOICES (Revenue)
    if active_tab == 'invoices':
        # Metrics: Use Payments for Actual Revenue (since total_amount is property)
        # OR use InvoicePayment objects filtered by these invoices
        payments_qs = InvoicePayment.objects.filter(invoice__in=base_qs)

        aggregates = payments_qs.aggregate(total_rev=Sum('amount'))
        total_rev = aggregates['total_rev'] or 0

        count = base_qs.count()
        avg_val = total_rev / count if count > 0 else 0

        # Chart: Revenue by Month (using Payments)
        chart_qs = payments_qs.annotate(month=TruncMonth('date')).values('month').annotate(val=Sum('amount')).order_by('month')

        context.update({
            'total_revenue': total_rev,
            'invoice_count': count,
            'avg_invoice_value': avg_val,
            'recent_invoices': base_qs.select_related('sales_agent').prefetch_related('payments').order_by('-created_at')[:50],
            'chart_labels': [x['month'].strftime('%Y-%m') for x in chart_qs if x['month']],
            'chart_values': [float(x['val']) for x in chart_qs if x['month']]
        })

    # TAB 2: CUSTOMERS
    elif active_tab == 'customers':
        # Clients in these invoices
        client_qs = Client.objects.filter(invoiceitem__invoice__in=base_qs).distinct()
        active_count = client_qs.count()
        recent_customers = client_qs.order_by('-created_at')[:10]

        # Chart: Active Customers by Month (Invoice Date)
        # Count unique clients per month based on Invoice Created At
        growth_qs = base_qs.annotate(month=TruncMonth('created_at'))\
            .values('month')\
            .annotate(cnt=Count('items__client', distinct=True))\
            .order_by('month')

        context.update({
            'active_customers': active_count,
            'recent_customers': recent_customers,
            'chart_labels': [x['month'].strftime('%Y-%m') for x in growth_qs if x['month']],
            'chart_values': [x['cnt'] for x in growth_qs if x['month']]
        })

    # TAB 3: PRODUCTS (Tours)
    elif active_tab == 'products':
        items_qs = InvoiceItem.objects.filter(invoice__in=base_qs, tour_booking__isnull=False)

        seats_sold = items_qs.count()
        # Revenue from Items: unit_price * quantity (Aggregation needs ExpressionWrapper if computed)
        # InvoiceItem has unit_price field? Yes.
        # But total is property. Let's aggregate unit_price (approx for single items)
        # or iterate if volume is low. For dashboard, let's try F expression.
        product_rev = items_qs.aggregate(s=Sum(F('unit_price') * F('quantity')))['s'] or 0

        # Top Products
        # Group by Product Name
        top_products = items_qs.values(
            'tour_booking__tour_instance__product__name'
        ).annotate(
            sold=Count('id'),
            rev=Sum(F('unit_price') * F('quantity'))
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
        # Flight Items or Ticket objects
        flight_items = InvoiceItem.objects.filter(
            invoice__in=base_qs
        ).filter(Q(description__icontains='Flight') | Q(flight_ticket__isnull=False))

        flight_rev = flight_items.aggregate(s=Sum(F('unit_price') * F('quantity')))['s'] or 0
        tickets_sold = flight_items.count()

        # Top Flight Descriptions (e.g. "Flight: AC098")
        top_items = flight_items.values('description').annotate(
            c=Count('id'),
            r=Sum(F('unit_price') * F('quantity'))
        ).order_by('-r')[:10]

        context.update({
            'tickets_sold': tickets_sold,
            'flight_revenue': flight_rev,
            'top_items': top_items
        })

    return render(request, 'roles/marketing/dashboard.html', context)
