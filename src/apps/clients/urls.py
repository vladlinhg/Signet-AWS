from django.urls import path
from engine.records.clients.views import client_detail

urlpatterns = [
    path('view/<int:pk>/', client_detail, name='client_detail'),
]
