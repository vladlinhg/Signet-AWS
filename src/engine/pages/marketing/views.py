from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncMonth
from apps.invoices.models import Invoice, InvoiceItem, InvoicePayment
from apps.currencies.models import Currency
from apps.clients.models import Client
from apps.flights.models import FlightTicket
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime
from datetime import timedelta
from engine.services.global_filter import GlobalFilterService

User = get_user_model()

def is_marketing_or_manager(user):
    return user.is_authenticated and (user.role in ['MARKETING', 'MANAGER', 'SALES'] or user.is_superuser)

@login_required
@user_passes_test(is_marketing_or_manager)
def marketing_dashboard(request):
    """
    Marketing Analytics "Command Center"
    Enhanced with Scatter Charts, Departure-based Passenger Counts, and Product Distribution.
    """
    # --- 1. Global Filter Service (Centralized Logic) ---
    filter_service = GlobalFilterService(request)
    filter_context = filter_service.get_context()

    # Extract needed values for QuerySets
    selected_statuses = filter_context['selected_statuses']
    selected_currency_code = filter_context['selected_currency_code']
    start_date = filter_context['start_date']
    end_date = filter_context['end_date']
    calc_mode = filter_context['calc_mode']

    # --- 2. Base QuerySets ---

    # A. Financial QuerySet (COHORT MODEL: Anchored to Invoice Creation)
    # Status Agnostic for Revenue. Only filter by Currency and Creation Date.
    inv_qs = Invoice.objects.filter(
        currency__code=selected_currency_code
    )
    if start_date:
        inv_qs = inv_qs.filter(created_at__date__gte=start_date)
    if end_date:
        inv_qs = inv_qs.filter(created_at__date__lte=end_date)

    # B. Passenger QuerySet (Based on DEPARTURE DATE - TourInstance.start_date)
    # We look for InvoiceItems -> Linked to TourBooking -> Linked to TourInstance
    passenger_qs = InvoiceItem.objects.filter(
        invoice__status__in=selected_statuses, # Only confirmed/paid bookings?
        tour_booking__isnull=False
    )
    if start_date:
        passenger_qs = passenger_qs.filter(tour_booking__tour_instance__start_date__gte=start_date)
    if end_date:
        passenger_qs = passenger_qs.filter(tour_booking__tour_instance__start_date__lte=end_date)


    # --- 3. Metrics Calculation ---

    # 3.1 Financial Metrics (Revenue)
    total_revenue = 0
    trend_data = []

    if calc_mode == 'actual':
        # Use Payments for Actual Revenue
        payments_qs = InvoicePayment.objects.filter(invoice__in=inv_qs)
        total_revenue = payments_qs.aggregate(Sum('amount'))['amount__sum'] or 0

        # Trend: Payment Date
        # Trend: Invoice Creation Date (Align with User's Manual Backdating)
        revenue_trend = payments_qs.values('invoice__created_at__date')\
            .annotate(total=Sum('amount'))\
            .order_by('invoice__created_at__date')

        for entry in revenue_trend:
            d = entry['invoice__created_at__date']
            if d:
                trend_data.append({
                    'x': d.strftime('%Y-%m-%d'),
                    'y': float(entry['total'])
                })
    else:
        # Anticipated: Sum of Invoice Items (Unit Price * Quantity)
        items_qs = InvoiceItem.objects.filter(invoice__in=inv_qs)
        total_revenue = items_qs.aggregate(s=Sum(F('unit_price') * F('quantity')))['s'] or 0

        # Trend: Invoice Creation Date
        revenue_trend = items_qs.values('invoice__created_at__date')\
            .annotate(total=Sum(F('unit_price') * F('quantity')))\
            .order_by('invoice__created_at__date')

        for entry in revenue_trend:
            d = entry['invoice__created_at__date']
            if d:
                trend_data.append({
                    'x': d.strftime('%Y-%m-%d'),
                    'y': float(entry['total'])
                })

    invoice_count = inv_qs.count()

    # 3.2 Passenger Metrics
    total_passengers = passenger_qs.count()


    # --- 4. Charts Data Preparation ---

    # 4.2 Client Distribution by Destination (Pie Chart)
    # Changed from Country Code to Product Name (Destination)
    dest_stats = passenger_qs.values(
        'tour_booking__tour_instance__product__name',
        'tour_booking__tour_instance__product__country_code'
    )\
        .annotate(count=Count('id'))\
        .order_by('-count')

    pie_labels = []
    pie_values = []
    for entry in dest_stats:
        name = entry['tour_booking__tour_instance__product__name']
        country = entry['tour_booking__tour_instance__product__country_code']
        label = name or country or "Unknown"
        pie_labels.append(label)
        pie_values.append(entry['count'])

    # 4.3 Passenger Trend (Daily Departures) - Bar Chart
    # Group by Tour Start Date
    passenger_trend = passenger_qs.values('tour_booking__tour_instance__start_date')\
        .annotate(count=Count('id'))\
        .order_by('tour_booking__tour_instance__start_date')

    passenger_trend_data = []
    for entry in passenger_trend:
        d = entry['tour_booking__tour_instance__start_date']
        if d:
            passenger_trend_data.append({
                'x': d.strftime('%Y-%m-%d'),
                'y': entry['count']
            })

    # 4.4 Most Frequent Passengers (Top 10)
    # Group by Client
    top_passengers_qs = passenger_qs.values(
        'client__id',
        'client__first_name',
        'client__last_name',
        'client__gender',
        'client__email',
        'client__phone'
    ).annotate(
        trips=Count('id'),
        total_spend=Sum(F('unit_price') * F('quantity'))
    ).order_by('-trips')[:100]

    # --- 5. Context ---
    context = {
        # Base Filter Context (includes calc_mode)
        **filter_context,

        'active_tab': request.GET.get('tab', 'overview'),

        # Override dashboard titles for component
        'dashboard_title': 'Marketing Command Center',
        'dashboard_subtitle': 'Revenue trends, passenger counts, and market distribution.',

        # Metrics
        'total_revenue': total_revenue,
        'invoice_count': invoice_count,
        'total_passengers': total_passengers,

        # Charts
        'trend_data': trend_data,
        'pie_labels': pie_labels,
        'pie_values': pie_values,
        'passenger_trend_data': passenger_trend_data,

        # Tables
        'top_passengers': top_passengers_qs,
        # 'recent_invoices': inv_qs.select_related('sales_agent').order_by('-created_at')[:20], # Replaced by Top Passengers
    }
    return render(request, 'roles/marketing/dashboard.html', context)

@login_required
@user_passes_test(is_marketing_or_manager)
def marketing_client_history(request, client_id):
    """
    Detailed history for a specific client viewed by Marketing.
    """
    client = get_object_or_404(Client, id=client_id)

    # Get all InvoiceItems linked to this client
    # Sorted by Invoice Date
    # Sort by Invoice Date, Filter only Tour or Flight items
    items = InvoiceItem.objects.filter(client=client).filter(
        Q(tour_booking__isnull=False) | Q(flight_ticket__isnull=False)
    ).select_related('invoice', 'tour_booking__tour_instance__product', 'flight_ticket')\
    .order_by('-invoice__created_at')

    # Calculate Total Spending per Currency
    # Group by Currency Code and Sum Total Price of items linked to this client
    spending_summary = items.values('invoice__currency__code')\
        .annotate(total=Sum('total_price'))\
        .order_by('invoice__currency__code')

    context = {
        'client': client,
        'items': items,
        'spending_summary': spending_summary,
    }
    return render(request, 'roles/marketing/client_history.html', context)
