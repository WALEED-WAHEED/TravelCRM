from .audit import clear_current_actor, set_current_actor
from .tenancy import (
    apply_db_session_context,
    clear_current_tenant,
    resolve_tenant_context,
    set_current_tenant,
    set_platform_admin_bypass,
)


class TenantMiddleware:
    """
    Establishes tenant context for the duration of a request, from
    whichever user Django's AuthenticationMiddleware resolved (session
    cookie). Must sit *after* AuthenticationMiddleware in MIDDLEWARE.

    Requests authenticated some other way *after* this middleware runs
    (pure JWT bearer tokens, where request.user is only resolved inside
    DRF's own dispatch) are covered separately by TenantScopedAPIMixin.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        bypass, tenant_id = resolve_tenant_context(request.user)
        set_platform_admin_bypass(bypass)
        set_current_tenant(tenant_id)
        apply_db_session_context(bypass, tenant_id)
        set_current_actor(request.user, request.META.get('REMOTE_ADDR'), request.META.get('HTTP_USER_AGENT', ''))
        try:
            response = self.get_response(request)
        finally:
            clear_current_tenant()
            set_platform_admin_bypass(False)
            clear_current_actor()
        return response
