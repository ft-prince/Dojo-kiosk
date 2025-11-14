"""
Process DOJO - App Configuration
"""
from django.apps import AppConfig


class ProcessDojoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'process_dojo'
    verbose_name = 'Process DOJO Training System'
    
    def ready(self):
        """Import signals when app is ready"""
        import process_dojo.signals