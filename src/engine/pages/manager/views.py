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
        .prefetch_related(
            'items',
            'items__client',
            'payments',
            'items__tour_booking__tour_instance__product',
            'items__flight_ticket__flight',
            'items__addon_service',
            'items__coupon'
        )\
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
            client_name = client.formal_name
            client_phone = client.phone
            client_email = client.email

        # Prepare Item Badges (Max 3)
        items_display = []
        for item in inv.items.all()[:3]:
            label = item.description or "Item"
            badge_class = "bg-gray-100 text-gray-800"

            if item.tour_booking:
                tour = item.tour_booking.tour_instance
                # Product Name or Country Name or Country Code or "Tour"
                p_name = tour.product.name if tour.product and tour.product.name else (tour.product.country_code if tour.product else "Tour")
                label = f"Tour: {p_name} ({tour.tour_code})"
                badge_class = "bg-indigo-100 text-indigo-800"
            elif item.flight_ticket:
                flight = item.flight_ticket.flight
                label = f"Flight: {flight.flight_code}"
                badge_class = "bg-green-100 text-green-800"
            elif item.addon_service:
                label = f"Addon: {item.addon_service.title}"
                badge_class = "bg-yellow-100 text-yellow-800"
            elif item.coupon:
                label = f"Coupon: {item.coupon.code}"
                badge_class = "bg-pink-100 text-pink-800"

            items_display.append({'label': label, 'class': badge_class})

        # Calculate Row Value based on Mode
        if calc_mode == 'actual':
            # Sum of payments
            row_value = sum(p.amount for p in inv.payments.all())
        else:
            # Anticipated: Sum of items
            row_value = sum(item.unit_price * item.quantity for item in inv.items.all())

        activity_data.append({
            'id': inv.id,
            'booking_number': inv.booking_number,
            'client_id': client.id if client else None,
            'client_name': client_name,
            'phone': client_phone,
            'email': client_email,
            'items_display': items_display,
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

def is_manager_or_sales(user):
    return user.is_authenticated and (user.role in ['MANAGER', 'SALES'] or user.is_superuser)

@login_required
@user_passes_test(is_manager_or_sales)
def import_booking_pdf(request):
    from django.contrib import messages
    from django.shortcuts import redirect

    # Check if this is a "Restart" request (clear session)
    if request.GET.get('reset'):
        if 'import_preview_data' in request.session:
            del request.session['import_preview_data']

    if request.method == "POST":
        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            messages.error(request, "Please upload a file.")
            return redirect('import_booking_pdf')

        try:
            # 1. Parse PDF
            from apps.core.services.pdf_parser import PDFParserService

            # Save temp file for PyMuPDF (it needs a path or bytes)
            # We'll pass the stream content directly if possible, or save temp
            # PyMuPDF fits.open(stream=bytes, filetype="pdf") works perfectly

            file_bytes = pdf_file.read()
            print(f"DEBUG: Uploaded file size: {len(file_bytes)} bytes") # Log file size

            parser = PDFParserService(file_stream=file_bytes)
            parsed_data = parser.parse()

            # Debug Logs
            text_len = len(parsed_data.get('raw_text_preview', ''))
            print(f"DEBUG: Extracted Text Length: {text_len}")
            print(f"DEBUG: Header Extracted: {parsed_data.get('header')}")
            if text_len > 0:
                print(f"DEBUG: Text Preview (Start): {parsed_data['raw_text_preview'][:100]}")
            else:
                print("DEBUG: Raw text is EMPTY")

            # 2. Store in Session for Review
            # We need to serialize this data (it's mostly dicts/lists/strings, so it's JSON safe)
            # Just ensure no non-serializable objects (like datetime objects) are in there yet
            # The parser returns strings currently, so we should be good.
            request.session['import_preview_data'] = parsed_data

            messages.success(request, "PDF analyzed successfully. Please review the details below.")
            return render(request, 'roles/manager/import_preview.html', {'preview_data': parsed_data})

        except Exception as e:
            messages.error(request, f"Import Error: {str(e)}")
            return redirect('import_booking_pdf')

    # GET Request: Show Upload Form (or Preview if session exists?)
    # Usually better to stay on upload form unless explicitly in preview flow.
    # If we have data in session, let's clear it unless we just posted?
    # Actually, let's keep it simple: GET always shows upload form.
    return render(request, 'roles/manager/import_booking.html')

@login_required
@user_passes_test(is_manager_or_sales)
def confirm_booking_import(request):
    from django.contrib import messages
    from django.shortcuts import redirect
    from apps.core.services.booking_importer import BookingImporterService

    if request.method != "POST":
         return redirect('import_booking_pdf')

    parsed_data = request.session.get('import_preview_data')
    if not parsed_data:
        messages.error(request, "Session expired or no data found. Please upload again.")
        return redirect('import_booking_pdf')

    try:
        # Execute Import
        importer = BookingImporterService(parsed_data, user=request.user)
        invoice = importer.import_booking()

        # Success
        messages.success(request, f"Booking {invoice.booking_number} imported successfully!")

        # Clear session
        del request.session['import_preview_data']

        # Redirect to Invoice
        # Assuming 'sales:invoice_detail' or similar exists, or manager view
        # Let's try to find a generic invoice detail view, or fallback to dashboard
        return redirect(f'/invoices/view/{invoice.id}/') # Adjust URL name as needed

    except Exception as e:
        messages.error(request, f"Database Import Failed: {str(e)}")
        # Keep session data so they can try again if it's transient,
        # or stick on preview page?
        return redirect('import_booking_pdf')
