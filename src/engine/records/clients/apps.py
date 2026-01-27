from django.apps import AppConfig

class ClientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'engine.records.client'
    label = 'records_client'
