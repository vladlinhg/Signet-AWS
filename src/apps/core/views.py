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

            if import_type == 'legacy':
                from apps.core.services.legacy_importer import LegacyImporter
                # For legacy, we might re-process or just save.
                # Actually, the Service handles parsing from file directly in current design.
                # But here we have JSON data from stage 1.
                # Let's adapt: if we already parsed, we can iterate.
                # But LegacyImporter logic is tightly coupled to CSV row processing.
                # We should probably refactor or just call process_row loop.
                importer = LegacyImporter()
                count = 0
                for row in to_save:
                    importer.process_row(row)
                    count += 1
            else:
                service = DataImportService()
                count = service.save_data(to_save, import_type)

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
                    # Pass the file object directly
                    # Note: Django request.FILES are UploadedFile (Bytes)
                    preview_data = [{'data': row} for row in LegacyImporter().parse_csv(csv_file.file)]
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
