from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponseForbidden
from apps.invoices.models import Invoice, InvoiceNote
from django.contrib.auth import get_user_model

User = get_user_model()

def is_accountant(user):
    return user.is_authenticated and (user.role == 'ACCOUNTANT' or user.is_superuser)

@login_required
def invoice_detail(request, pk):
    """
    Detailed view of an Invoice.
    Permission:
    - Manager/Admin/Accountant: View All
    - Sales: View Own Only
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    user = request.user
    
    # Permission Check
    can_view = False
    if user.role in [User.Role.MANAGER, User.Role.ACCOUNTANT, User.Role.IT_ADMIN] or user.is_superuser:
        can_view = True
    elif user.role == User.Role.SALES and invoice.sales_agent == user:
        can_view = True
    elif user.role == User.Role.MARKETING: 
        can_view = True

    if not can_view:
        return HttpResponseForbidden("You do not have permission to view this invoice.")

    # Edit Permission (Now via Admin)
    # can_edit determines if we show the "Edit in Admin" button
    can_edit = (user.role == User.Role.MANAGER or user.is_superuser) or (user == invoice.sales_agent and invoice.status != Invoice.Status.VERIFIED)
    
    context = {
        'invoice': invoice,
        'can_edit': can_edit,
        'items': invoice.items.all()
    }
    return render(request, 'entities/invoices/detail.html', context)

@login_required
@user_passes_test(is_accountant)
def invoice_audit_detail(request, pk):
    """
    Detailed view to audit an invoice.
    Allows Approve (Verify) or Reject (Needs Fix).
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        note_content = request.POST.get('note')
        
        if action == 'approve':
            invoice.status = Invoice.Status.VERIFIED
            invoice.save()
            messages.success(request, f"Invoice {invoice.invoice_number} Verified.")
            return redirect('accountant_dashboard')
            
        elif action == 'reject':
            if not note_content:
                messages.error(request, "You must provide a note when requesting fixes.")
            else:
                invoice.status = Invoice.Status.NEEDS_FIX
                invoice.save()
                # Create Note
                InvoiceNote.objects.create(
                    invoice=invoice,
                    author=request.user,
                    content=note_content
                )
                messages.warning(request, f"Invoice returned to Sales with note.")
                return redirect('accountant_dashboard')

    context = {
        'invoice': invoice,
    }
    return render(request, 'entities/invoices/audit.html', context)
