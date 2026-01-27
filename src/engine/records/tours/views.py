from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from apps.tours.models import TourInstance
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def tour_detail(request, pk):
    """
    Detailed view of a Tour Instance.
    """
    tour = get_object_or_404(TourInstance, pk=pk)
    user = request.user
    
    # Permission Check
    if not user.role in [User.Role.MANAGER, User.Role.SALES, User.Role.IT_ADMIN, User.Role.MARKETING] and not user.is_superuser:
        return HttpResponseForbidden("You do not have permission to view tours.")

    # Edit Permission
    can_edit = (user.role in [User.Role.MANAGER, User.Role.IT_ADMIN] or user.is_superuser)
    
    context = {
        'tour': tour,
        'can_edit': can_edit,
    }
    return render(request, 'entities/tours/detail.html', context)
