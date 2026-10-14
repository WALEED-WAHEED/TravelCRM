from django.apps import AppConfig


class SystemConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'system_config'

    def ready(self):
        from utils.audit import register_audited_models
        register_audited_models()
