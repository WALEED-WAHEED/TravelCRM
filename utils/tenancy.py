"""
Tenant-scoping infrastructure.

Every agency-owned model gets its default `objects` manager auto-filtered
to "whichever tenant this request belongs to" via a context-var set by
TenantMiddleware (session requests) / TenantScopedAPIMixin (DRF requests
authenticated after middleware runs, e.g. pure JWT). This means a view or
viewset that forgets to filter by agency no longer leaks another tenant's
rows — it gets an empty queryset instead, because nothing else is
"current tenant" by default.

This is layer one of two. Postgres Row-Level Security (see
platform_admin/migrations for the RLS policies) is layer two, enforced by
the database itself even if a raw query or a future management command
bypasses the ORM entirely.
"""
import contextvars

from django.db import models

_current_tenant_id = contextvars.ContextVar("current_tenant_id", default=None)
_platform_admin_bypass = contextvars.ContextVar("platform_admin_bypass", default=False)


def set_current_tenant(agency_id):
    _current_tenant_id.set(agency_id)


def get_current_tenant_id():
    return _current_tenant_id.get()


def clear_current_tenant():
    _current_tenant_id.set(None)


def set_platform_admin_bypass(value):
    _platform_admin_bypass.set(bool(value))


def is_platform_admin_bypass():
    return _platform_admin_bypass.get()


class tenant_context:
    """
    Context manager for code paths that run outside a request (management
    commands, shell sessions, scripts) and need explicit tenant scoping.

        with tenant_context(agency_id=5):
            Hotel.objects.all()  # scoped to agency 5

        with tenant_context(bypass=True):
            Hotel.objects.all()  # every tenant — trusted admin code only
    """

    def __init__(self, agency_id=None, bypass=False):
        self.agency_id = agency_id
        self.bypass = bypass
        self._tenant_token = None
        self._bypass_token = None

    def __enter__(self):
        self._tenant_token = _current_tenant_id.set(self.agency_id)
        self._bypass_token = _platform_admin_bypass.set(self.bypass)
        return self

    def __exit__(self, *exc_info):
        _current_tenant_id.reset(self._tenant_token)
        _platform_admin_bypass.reset(self._bypass_token)


class TenantManager(models.Manager):
    """
    Default manager for tenant-owned models (anything with an `agency`
    FK). Scopes to the current request's tenant automatically; returns
    nothing if no tenant context has been established, rather than
    everything — a missing context is treated as "no access", not "full
    access".
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if is_platform_admin_bypass():
            return qs
        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            return qs.none()
        return qs.filter(agency_id=tenant_id)


class TenantOrGlobalManager(TenantManager):
    """
    Same as TenantManager, but also includes rows with agency=NULL
    ("global" / platform-wide rows) — used by the handful of models
    (EmailTemplate, APIKey) that intentionally support both agency-owned
    and platform-wide records.
    """

    def get_queryset(self):
        qs = models.Manager.get_queryset(self)
        if is_platform_admin_bypass():
            return qs
        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            return qs.filter(agency__isnull=True)
        return qs.filter(models.Q(agency_id=tenant_id) | models.Q(agency__isnull=True))


class UnscopedManager(models.Manager):
    """
    Every row, every tenant, no filtering — only for trusted platform-admin
    code paths (the Super Admin app, data migrations, management commands
    run via `tenant_context(bypass=True)`). Never expose this manager's
    results to a tenant-facing view or API response.
    """

    pass


def apply_db_session_context(bypass, tenant_id):
    """
    Mirrors the Python-side tenant context onto Postgres session GUCs so
    Row-Level Security policies (enforced by the database itself, not the
    ORM) see the same tenant. A no-op on backends without SET support
    (e.g. sqlite in tests) and safe to call every request — Django gives
    each request a fresh connection by default (CONN_MAX_AGE=0), so there
    is no risk of one request's tenant leaking into the next via a reused
    connection.
    """
    from django.db import connection

    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.is_platform_admin', %s, false)", ["true" if bypass else "false"])
        cursor.execute(
            "SELECT set_config('app.current_tenant_id', %s, false)",
            [str(tenant_id) if tenant_id is not None else ""],
        )


def resolve_tenant_context(user):
    """
    Given an authenticated (or anonymous) user, decide the (bypass,
    tenant_id) pair that should apply for the rest of the request.
    Shared by TenantMiddleware and TenantScopedAPIMixin so both paths
    make the exact same decision.
    """
    if not getattr(user, "is_authenticated", False):
        return False, None
    if getattr(user, "is_superuser", False):
        return True, None
    return False, getattr(user, "agency_id", None)
