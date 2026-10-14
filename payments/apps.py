from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
    verbose_name = 'Payments & Suppliers'

    def ready(self):
        from . import signals  # noqa: F401 — registers signal handlers
