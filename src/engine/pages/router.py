from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_router(request):
    """
    Central Router: Dispatches users to their specific dashboard based on Role.
    """
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
        # Fallback for others or if no role set
        return redirect('admin:index')
