from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Invoice, InvoiceNote

def is_accountant_or_manager(user):
    return user.is_authenticated and (user.role in ['ACCOUNTANT', 'MANAGER'] or user.is_superuser)

@login_required
@user_passes_test(is_accountant_or_manager)
def accountant_dashboard(request):
    """
    Main dashboard for the Accountant.
    Shows 'Submitted' invoices (Priority) and recent 'Verified' ones.
    """
    # Priority: Submitted invoices needing audit
    audit_queue = Invoice.objects.filter(status=Invoice.Status.SUBMITTED).order_by('created_at')
    
    # Secondary: Needs fix (waiting on sales) or Draft (monitoring)
    # For MVP, mostly focus on Audit Queue
    
    # Stats
    context = {
        'audit_queue': audit_queue,
        'verified_count': Invoice.objects.filter(status=Invoice.Status.VERIFIED).count(),
        'pending_count': audit_queue.count(),
    }
    return render(request, 'sales/dashboard.html', context)

@login_required
@user_passes_test(is_accountant_or_manager)
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
    return render(request, 'sales/audit_detail.html', context)
