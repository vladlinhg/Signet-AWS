from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
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
    Dedicated dashboard for Sales Agents.
    Shows: Wallet (My Sales), Recent Invoices, Quick Actions.
    """
    user = request.user
    # 1. Wallet Logic (Manager Only - wait, originally it said Manager Only but code allows User to see OWN wallet?)
    # Original code: show_wallet = user.role == User.Role.MANAGER or user.is_superuser
    # Actually checking original file: users only see wallet if MANAGER? No wait...
    # Re-reading original `views.py` logic:
    # "show_wallet = user.role == User.Role.MANAGER or user.is_superuser"
    # Wait, if Sales Agent can't see wallet, why is it there?
    # Ah, the template had logic.
    # I will preserve original logic.
    
    show_wallet = user.role == User.Role.MANAGER or user.is_superuser
    if show_wallet:
        wallet_data = Invoice.objects.filter(sales_agent=user, status=Invoice.Status.VERIFIED) \
            .values('currency__code', 'currency__symbol') \
            .annotate(total=Sum('total_amount')) \
            .order_by('currency__code')
    else:
        wallet_data = []
    
    # 2. Pending Count
    pending_count = Invoice.objects.filter(sales_agent=user, status__in=[Invoice.Status.DRAFT, Invoice.Status.NEEDS_FIX]).count()
    
    # 3. Recent Invoices
    recent_invoices = Invoice.objects.filter(sales_agent=user).order_by('-created_at')[:10]

    # 4. Contextual "Recent Activity"
    recent_invoice_ids = recent_invoices.values_list('id', flat=True)
    recent_items = InvoiceItem.objects.filter(invoice__in=recent_invoice_ids)
    
    # Extract unique Clients
    seen_clients = set()
    recent_clients = []
    for inv in recent_invoices:
        if inv.client and inv.client.id not in seen_clients:
            recent_clients.append(inv.client)
            seen_clients.add(inv.client.id)
            if len(recent_clients) >= 5: break
            
    # Extract unique Flights
    recent_flights = []
    seen_flights = set()
    flight_items = recent_items.filter(flight_ticket__isnull=False).select_related('flight_ticket')
    for item in flight_items:
        flight = item.flight_ticket.flight
        if flight and flight.id not in seen_flights:
            recent_flights.append(flight)
            seen_flights.add(flight.id)
            if len(recent_flights) >= 5: break
            
    # Extract unique Tours
    recent_tours = []
    seen_tours = set()
    tour_items = recent_items.filter(tour_instance__isnull=False).select_related('tour_instance')
    for item in tour_items:
        tour = item.tour_instance
        if tour and tour.id not in seen_tours:
            recent_tours.append(tour)
            seen_tours.add(tour.id)
            if len(recent_tours) >= 5: break
            
    real_flights = recent_flights
    real_tours = recent_tours

    # 5. Reminders
    today = timezone.now().date()
    my_client_ids = Invoice.objects.filter(sales_agent=user).values_list('client_id', flat=True).distinct()
    
    upcoming_birthdays = Client.objects.filter(
        id__in=my_client_ids, 
        birth_date__month=today.month, 
        birth_date__day__gte=today.day
    ).order_by('birth_date__day')[:5]
    
    passport_expiry = TravelDocument.objects.filter(
        client__id__in=my_client_ids,
        doc_type=TravelDocument.Type.PASSPORT,
        expiry_date__range=[today, today + timezone.timedelta(days=180)]
    ).select_related('client').order_by('expiry_date')[:5]

    context = {
        'wallet_data': wallet_data,
        'show_wallet': show_wallet,
        'pending_count': pending_count,
        'recent_invoices': recent_invoices,
        'recent_clients': recent_clients,
        'recent_flights': real_flights,
        'recent_tours': real_tours,
        'reminders_birthdays': upcoming_birthdays,
        'reminders_passports': passport_expiry,
    }
    return render(request, 'roles/sales/dashboard.html', context)
