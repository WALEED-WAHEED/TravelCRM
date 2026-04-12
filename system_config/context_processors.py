from .models import SAASProductConfig

def saas_config(request):
    """
    Context processor to make SAASProductConfig available globally in all templates
    as {{ saas_config }}.
    """
    try:
        config = SAASProductConfig.load()
        return {'saas_config': config}
    except Exception:
        return {'saas_config': None}
