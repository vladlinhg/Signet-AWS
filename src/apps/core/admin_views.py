from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.management import call_command
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def generate_data_view(request):
    if request.method == "POST":
        count = int(request.POST.get('count', 10))
        try:
            call_command('generate_dummy_sales', count=count)
            messages.success(request, f"Successfully generated {count} dummy invoices.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('admin:index')
    
    context = {
        'title': 'Generate Demo Data',
        'site_header': admin.site.site_header,
        'site_title': admin.site.site_title,
        'has_permission': True,
    }
    return render(request, 'admin/generate_data.html', context)
