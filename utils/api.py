from .audit import set_current_actor
from .tenancy import apply_db_session_context, resolve_tenant_context, set_current_tenant, set_platform_admin_bypass


class TenantScopedAPIMixin:
    """
    For DRF views whose authentication resolves request.user *after*
    TenantMiddleware already ran — i.e. pure JWT bearer-token calls with
    no session cookie, where DRF's own `initial()` does the
    authentication. Re-applies tenant context once the real user is
    known, so `Model.objects` is correctly scoped inside the view body.

    Views that only ever receive session-cookie requests (the browser
    UI's normal path) are already covered by TenantMiddleware alone,
    since Django's AuthenticationMiddleware resolves request.user before
    DRF ever sees the request — this mixin is what makes JWT-only calls
    to the same endpoints safe too.
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        bypass, tenant_id = resolve_tenant_context(request.user)
        set_platform_admin_bypass(bypass)
        set_current_tenant(tenant_id)
        apply_db_session_context(bypass, tenant_id)
        set_current_actor(request.user, request.META.get('REMOTE_ADDR'), request.META.get('HTTP_USER_AGENT', ''))
