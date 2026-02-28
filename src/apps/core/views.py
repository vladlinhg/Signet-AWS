from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from .forms import ImportDataForm, WipeDataForm
from .services import DataImportService, DataImporter
from django.core.management import call_command
from apps.tours.models import Product, TourInstance
from apps.flights.models import Flight, FlightTicket
from apps.clients.models import Client
from apps.invoices.models import Invoice
import json

def is_not_accountant(user):
    return user.is_authenticated and user.role != 'ACCOUNTANT'

def is_it_admin(user):
    return user.is_authenticated and user.role == 'IT_ADMIN'

@login_required
@user_passes_test(is_not_accountant, login_url='/sales/dashboard/')
def import_data_view(request):
    # Stage 2: Confirmation
    if request.method == 'POST' and 'confirm_import' in request.POST:
        selected_indices = request.POST.getlist('selected_items')
        raw_json = request.POST.get('preview_data')
        import_type = request.POST.get('import_type')

        if raw_json and selected_indices:
            all_data = json.loads(raw_json)
            # Filter only selected
            to_save = [all_data[int(i)]['data'] for i in selected_indices]

            try:
                if import_type == 'legacy':
                    from apps.core.services.legacy_importer import LegacyImporter
                    importer = LegacyImporter()

                    # Retrieve Action for each item
                    count = 0
                    for i in selected_indices:
                        action_key = f"action_{i}"
                        action = request.POST.get(action_key, 'MERGE')
                        row_data = all_data[int(i)]['data']
                        importer.execute(row_data, action=action)
                        count += 1
                else:
                    service = DataImportService()
                    count = service.save_data(to_save, import_type)
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f"Import Error: {str(e)}")
                return redirect('import_data')

            messages.success(request, f"Successfully imported {count} items.")
            return redirect('import_data')

    # Stage 1: Upload
    if request.method == 'POST':
        form = ImportDataForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            import_type = form.cleaned_data['import_type']

            service = DataImportService()
            try:
                if import_type == 'legacy':
                    from apps.core.services.legacy_importer import LegacyImporter
                    # Pass the file object. Note: Django request.FILES are UploadedFile (Bytes)
                    preview_data = LegacyImporter().preview(csv_file.file)
                else:
                    preview_data = service.parse_csv(csv_file, import_type)

                # Render Preview Page
                return render(request, 'core/import_preview.html', {
                   'preview_data': preview_data,
                   'import_type': import_type,
                   'raw_json': json.dumps(preview_data, default=str)
                })
            except Exception as e:
                messages.error(request, f"Parse Failed: {e}")

    else:
        form = ImportDataForm()

    context = {
        'form': form,
        'title': 'Import Data'
    }
    return render(request, 'core/import_data.html', context)

@login_required
@user_passes_test(is_it_admin, login_url='/admin/')
def wipe_data_confirm(request):
    if request.method == 'POST':
        form = WipeDataForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Delete Data Logic
                Invoice.objects.all().delete()
                FlightTicket.objects.all().delete()
                Flight.objects.all().delete()
                TourInstance.objects.all().delete()
                Product.objects.all().delete()
                Client.objects.all().delete()

            messages.success(request, "All business data has been wiped.")
            return redirect('import_data') # Redirect to Import so they can start fresh
    else:
        form = WipeDataForm()

    return render(request, 'core/wipe_data.html', {'form': form})

@login_required
@user_passes_test(is_it_admin, login_url='/admin/')
def generate_data_view(request):
    if request.method == 'POST':
        try:
            call_command('generate_dummy_sales')
            messages.success(request, "Dummy data generated successfully.")
        except Exception as e:
            messages.error(request, f"Generation Failed: {str(e)}")
        return redirect('import_data')

    return render(request, 'core/generate_data.html')

@login_required
@user_passes_test(is_not_accountant, login_url='/sales/dashboard/')
def pdf_booking_import_view(request):
    from apps.core.services.imports.pdf_parser import PDFParserService
    from apps.core.services.imports.normalize.main import normalize_booking_text
    from apps.core.services.imports.db_sync.main import BookingImportService
    from apps.core.services.imports.db_sync.duplications import check_for_duplicate
    from apps.core.services.imports.db_sync.diff_engine import generate_payload_diff
    import base64
    
    # STAGE 3: Final Commit
    if request.method == 'POST' and 'confirm_import' in request.POST:
        raw_json = request.POST.get('preview_data')
        b64_pdf = request.POST.get('file_bytes')
        filename = request.POST.get('filename')
        
        if raw_json and b64_pdf:
            import json
            data = json.loads(raw_json)
            file_bytes = base64.b64decode(b64_pdf)
            
            try:
                # Disable Dry Run to actually execute insertion
                importer = BookingImportService(data, dry_run=False, file_bytes=file_bytes, filename=filename)
                diff = importer.execute()
                
                # Check User Decision Hooks (Not implemented yet, but keeping structure ready)
                # e.g overrides = request.POST.getlist('override_keys')
                
                messages.success(request, f"Success! Booking Imported.")
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f"Import Error: {str(e)}")
            
            return redirect('import_data')

    # STAGE 1: Upload & Pre-Normalization Check
    if request.method == 'POST' and 'file' in request.FILES:
        pdf_file = request.FILES['file']
        file_bytes = pdf_file.read()
        filename = pdf_file.name
        
        # Parse Raw Text
        try:
            from io import BytesIO
            byte_stream = BytesIO(file_bytes)
            parser = PDFParserService(byte_stream)
            
            # Fast-Exit Check
            booking_no = parser.extract_booking_number_only()
            full_raw_text = parser.text
            
            if check_for_duplicate(booking_no, full_raw_text):
                messages.warning(request, f"Booking {booking_no} was unchanged. Import Skipped.")
                return redirect('import_data')
                
            # Full Parse
            byte_stream.seek(0)
            parsed_data = parser.parse()
            
            # STAGE 2: Normalize & Dry Run
            normalized_payload = normalize_booking_text(booking_no, full_raw_text)
            
            # Dry-Run Execution
            importer = BookingImportService(normalized_payload, dry_run=True, file_bytes=file_bytes, filename=filename)
            diff_tracker = importer.execute()
            
            # Encode Context for Preview Template
            import json
            b64_file = base64.b64encode(file_bytes).decode('utf-8')
            
            # Generate Discrepancy UI Diff Blocks
            diff_blocks = generate_payload_diff(normalized_payload)
            
            context = {
                'preview_data': diff_blocks, # Override default CSV preview matrix
                'diff': diff_tracker,
                'raw_json': json.dumps(normalized_payload, default=str),
                'file_bytes': b64_file,
                'filename': filename,
                'import_type': 'pdf'
            }
            
            return render(request, 'core/import_preview.html', context)
            
        except Exception as e:
            messages.error(request, f"PDF Processing Failed: {e}")
            return redirect('import_data')

    # Fallback/Direct Hit (Should be handled by forms/main view but just in case)
    return redirect('import_data')
