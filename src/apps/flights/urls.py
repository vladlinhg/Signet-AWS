from django.urls import path
from engine.records.flights.views import flight_detail

urlpatterns = [
    path('view/<int:pk>/', flight_detail, name='flight_detail'),
]
