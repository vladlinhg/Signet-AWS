from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from apps.core.admin_views import generate_data_view
from apps.core.views import import_data_view, wipe_data_confirm

urlpatterns = [
    path('import/', import_data_view, name='import_data'),
    path('admin/wipe-data/', wipe_data_confirm, name='wipe_data'),
    path('admin/generate-data/', generate_data_view, name='generate_data'),
    path('admin/', admin.site.urls),
    path('sales/', include('apps.sales.urls')),
    path('', RedirectView.as_view(url='sales/dashboard/', permanent=False)),
]
