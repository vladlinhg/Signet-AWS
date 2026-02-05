from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q
from django.contrib import messages
from apps.invoices.models import Invoice, InvoiceItem
from apps.clients.models import Client, TravelDocument
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def dashboard_router(request):
    user = request.user
    if user.role == 'SALES':
        return redirect('sales_dashboard')
    elif user.role == 'MARKETING':
        return redirect('marketing_dashboard')
    elif user.role == 'MANAGER' or user.is_superuser:
        return redirect('manager_dashboard')
    elif user.role == 'ACCOUNTANT':
        return redirect('accountant_dashboard')
    else:
        return redirect('admin:index')

@login_required
def sales_dashboard(request):
    """
    Refactored Sales Dashboard: "My Work" Console.
    Supports Tabs: Invoices (default), Clients, Flights, Tours.
    Features: Search, Sort, and Scoped Data.
    """
    user = request.user

    # Parameters
    tab = request.GET.get('tab', 'invoices')
    query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '')

    # Defaults
    items = []
    headers = []

    # 1. INVOICES TAB
    if tab == 'invoices':
        # Optimizing query with select_related/prefetch
        if user.is_superuser or user.role == 'IT_ADMIN':
            qs = Invoice.objects.all().select_related('payment_method__travel_group').prefetch_related('items__client')
        else:
            qs = Invoice.objects.filter(sales_agent=user).select_related('payment_method__travel_group').prefetch_related('items__client')

        # Search
        if query:
            qs = qs.filter(
                Q(booking_number__icontains=query) |
                Q(payment_method__travel_group__name__icontains=query) |
                Q(items__client__last_name__icontains=query)
            ).distinct()

        # Sort
        if sort == 'date_asc':
            qs = qs.order_by('created_at')
        elif sort == 'amount_desc':
            qs = qs.order_by('-total_amount')
        elif sort == 'status_asc':
            qs = qs.order_by('status')
        else:
            qs = qs.order_by('-created_at') # Default

        items = qs

    # 2. CLIENTS TAB
    elif tab == 'clients':
        # Client -> InvoiceItem -> Invoice -> SalesAgent
        if user.is_superuser or user.role == 'IT_ADMIN':
            qs = Client.objects.all()
        else:
            qs = Client.objects.filter(invoiceitem__invoice__sales_agent=user).distinct()

        if query:
            qs = qs.filter(
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )

        if sort == 'name_asc':
            qs = qs.order_by('last_name', 'first_name')
        else:
            qs = qs.order_by('-created_at')

        items = qs

    # 3. FLIGHTS TAB
    elif tab == 'flights':
        from apps.flights.models import Flight
        # Flight -> FlightInstance(instances) -> FlightTicket(tickets) -> InvoiceItem -> Invoice -> SalesAgent
        if user.is_superuser or user.role == 'IT_ADMIN':
             qs = Flight.objects.all()
        else:
             qs = Flight.objects.filter(instances__tickets__invoiceitem__invoice__sales_agent=user).distinct()

        if query:
            qs = qs.filter(
                Q(flight_number__icontains=query) |
                Q(departure_airport__code__icontains=query) |
                Q(arrival_airport__code__icontains=query)
            )

        if sort == 'date_asc':
            # Note: sorting by related specific instances is tricky for grouping.
            # Default to airline code or simplistic sort
            qs = qs.order_by('airline__code')
        elif sort == 'airline_asc':
            qs = qs.order_by('airline__code', 'flight_number')
        else:
             qs = qs.order_by('airline__code') # Default

        items = qs

    # 4. TOURS TAB
    elif tab == 'tours':
        from apps.tours.models import TourInstance
        # TourInstance -> TourBooking(bookings) -> InvoiceItem -> Invoice -> SalesAgent
        if user.is_superuser or user.role == 'IT_ADMIN':
            qs = TourInstance.objects.all().select_related('product')
        else:
            qs = TourInstance.objects.filter(bookings__invoiceitem__invoice__sales_agent=user).distinct().select_related('product')

        if query:
            qs = qs.filter(
                Q(product__name__icontains=query) |
                Q(product__country_code__icontains=query)
            )

        if sort == 'date_asc':
            qs = qs.order_by('start_date')
        elif sort == 'country_asc':
            qs = qs.order_by('product__country_code', 'start_date')
        elif sort == 'spots_asc':
            items = sorted(qs, key=lambda t: t.available_spots)
            pass
        elif sort == 'spots_desc':
            items = sorted(qs, key=lambda t: t.available_spots, reverse=True)
            pass
        else:
            qs = qs.order_by('-start_date')

        # If manual sort wasn't applied, use qs
        if not (sort == 'spots_asc' or sort == 'spots_desc'):
            items = qs

    context = {
        'active_tab': tab,
        'items': items,
        'search_query': query,
        'current_sort': sort,
    }
    return render(request, 'roles/sales/dashboard.html', context)
