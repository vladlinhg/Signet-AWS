from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from apps.clients.models import Client
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def client_detail(request, pk):
    """
    Detailed view of a Client.
    """
    client = get_object_or_404(Client, pk=pk)
    user = request.user
    
    # Permission Check (Open to most roles)
    if not user.role in [User.Role.MANAGER, User.Role.SALES, User.Role.ACCOUNTANT, User.Role.IT_ADMIN, User.Role.MARKETING] and not user.is_superuser:
        return HttpResponseForbidden("You do not have permission to view clients.")

    # Edit Permission
    can_edit = (user.role in [User.Role.MANAGER, User.Role.SALES] or user.is_superuser)
    
    context = {
        'client': client,
        'can_edit': can_edit,
        'documents': client.documents.all()
    }
    return render(request, 'entities/clients/detail.html', context)
