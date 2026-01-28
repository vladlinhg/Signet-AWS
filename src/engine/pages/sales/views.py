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
        qs = Invoice.objects.filter(sales_agent=user).select_related('payment_method__family').prefetch_related('items__client')

        # Search
        if query:
            qs = qs.filter(
                Q(invoice_number__icontains=query) |
                Q(payment_method__family__name__icontains=query) |
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
        qs = Client.objects.filter(invoice_items__invoice__sales_agent=user).distinct()

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
        # Flight -> Tickets -> InvoiceItems -> Invoice -> SalesAgent
        qs = Flight.objects.filter(tickets__invoice_items__invoice__sales_agent=user).distinct()

        if query:
            qs = qs.filter(
                Q(flight_number__icontains=query) |
                Q(origin__icontains=query) | # Flight model uses origin/destination but display uses arrival/dep airport? Check model.
                Q(destination__icontains=query)
            )

        if sort == 'date_asc':
            qs = qs.order_by('departure_date', 'departure_time')
        elif sort == 'airline_asc':
            qs = qs.order_by('airline_code', 'flight_number')
        elif sort == 'departure_asc':
            qs = qs.order_by('departure_airport', 'departure_date')
        elif sort == 'arrival_asc':
            qs = qs.order_by('arrival_airport', 'departure_date')
        else:
            qs = qs.order_by('-departure_date', '-departure_time')

        items = qs

    # 4. TOURS TAB
    elif tab == 'tours':
        from apps.tours.models import TourInstance
        # TourInstance -> TourBooking -> InvoiceItem -> Invoice -> SalesAgent
        qs = TourInstance.objects.filter(bookings__invoice_items__invoice__sales_agent=user).distinct().select_related('product')

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
