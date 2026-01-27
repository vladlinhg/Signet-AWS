from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from apps.invoices.models import Invoice
from django.contrib.auth import get_user_model

User = get_user_model()

def is_accountant(user):
    return user.is_authenticated and (user.role == 'ACCOUNTANT' or user.is_superuser)

@login_required
@user_passes_test(is_accountant)
def accountant_dashboard(request):
    """
    Main dashboard for the Accountant.
    Shows 'Submitted' invoices (Priority) and recent 'Verified' ones.
    """
    # Priority: Submitted invoices needing audit
    audit_queue = Invoice.objects.filter(status=Invoice.Status.SUBMITTED).order_by('created_at')
    
    # Stats
    context = {
        'audit_queue': audit_queue,
        'verified_count': Invoice.objects.filter(status=Invoice.Status.VERIFIED).count(),
        'pending_count': audit_queue.count(),
    }
    return render(request, 'roles/accountant/dashboard.html', context)
