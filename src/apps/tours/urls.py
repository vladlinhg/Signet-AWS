from django.urls import path
from engine.records.tours.views import tour_detail

urlpatterns = [
    path('view/<int:pk>/', tour_detail, name='tour_detail'),
]
