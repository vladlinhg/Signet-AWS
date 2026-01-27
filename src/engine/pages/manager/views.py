from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum, Q
from apps.invoices.models import Invoice
from django.contrib.auth import get_user_model

User = get_user_model()

def is_manager(user):
    return user.is_authenticated and (user.role == 'MANAGER' or user.is_superuser)

@login_required
@user_passes_test(is_manager)
def manager_dashboard(request):
    """
    Unified Dashboard for Managers.
    Includes: Sales Performance, Global Wallets, Audit Status.
    """
    # 1. Global Wallet (All Verified Sales)
    wallet_data = Invoice.objects.filter(status=Invoice.Status.VERIFIED) \
        .values('currency__code', 'currency__symbol') \
        .annotate(total=Sum('total_amount')) \
        .order_by('currency__code')

    # 2. Performance Panel (Leaderboard)
    agent_stats = User.objects.filter(role=User.Role.SALES).annotate(
        total_invoices=Count('sales_invoices', filter=Q(sales_invoices__status=Invoice.Status.VERIFIED)),
    ).order_by('-total_invoices')[:5]

    # 3. Dept Status
    audit_backlog = Invoice.objects.filter(status=Invoice.Status.SUBMITTED).count()
    
    # 4. Recent Activity
    recent_invoices = Invoice.objects.all().order_by('-created_at')[:10]

    context = {
        'wallet_data': wallet_data,
        'agent_stats': agent_stats,
        'audit_backlog': audit_backlog,
        'recent_invoices': recent_invoices,
    }
    return render(request, 'roles/manager/dashboard.html', context)
