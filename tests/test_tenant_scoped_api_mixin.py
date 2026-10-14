"""
Regression test for a real bug found during Phase 11's Docker smoke test:
9 of 13 DRF ViewSets never inherited TenantScopedAPIMixin. Every native
test in this project (and every manual verification across the whole
build) ran the app connected as a Postgres superuser, which bypasses Row-
Level Security entirely — so the bug was invisible until the app was
finally run as the actual scoped, non-superuser role docker-compose.yml's
own comments have documented as correct since Phase 01.

The concrete failure: TenantMiddleware sets the RLS session GUCs from
request.user *before* DRF's own JWTAuthentication resolves who that user
is (JWT auth happens later, inside DRF's dispatch cycle) — so a JWT-only
request reaches a tenant-scoped ViewSet with the RLS context still at
its anonymous default. Every INSERT then violates the RLS policy
(`new row violates row-level security policy for table "..."`), and
every SELECT silently returns nothing, for *any* tenant-owned model's
ViewSet that doesn't re-apply tenant context after authentication
resolves via TenantScopedAPIMixin.get_queryset()/initial().

This test can't exercise RLS itself (the reasons above apply here too —
the test suite's own `default` connection is a superuser, by necessity,
so it could create the test database). Instead it directly encodes the
invariant that actually matters: every DRF ViewSet operating on a
tenant-owned (agency-scoped) model must inherit the mixin. A new
tenant-scoped ViewSet added later that forgets it will fail this test
immediately, in CI, rather than silently only under a real deployment's
RLS-enforcing connection.
"""
from rest_framework import viewsets

from utils.api import TenantScopedAPIMixin

# ViewSets that operate on a tenant-owned (agency-scoped) model and are
# reachable by more than just a superuser — these MUST inherit the mixin.
TENANT_SCOPED_VIEWSETS = [
    ("accounts.views", "UserViewSet"),
    ("agencies.views", "AgencyViewSet"),
    ("member.api_views", "HotelViewSet"),
    ("member.api_views", "FlightViewSet"),
    ("member.api_views", "TransportViewSet"),
    ("member.api_views", "PackageViewSet"),
    ("member.ledger_api_views", "LedgerEntryViewSet"),
    ("member.voucher_api_views", "VoucherViewSet"),
    ("system_config.views", "AgencyBrandingViewSet"),
    ("system_config.views", "EmailTemplateViewSet"),
    ("system_config.views", "NotificationSettingsViewSet"),
]

# Genuinely platform-global (no agency column at all) or Super-Admin-only
# views where getting this wrong fails closed (empty results) rather than
# leaking data — still worth the mixin for correctness, tracked
# separately since a missing entry here isn't a tenant-isolation bug.
PLATFORM_LEVEL_VIEWSETS_WITH_MIXIN_ANYWAY = [
    ("system_config.views", "APIKeyViewSet"),
    ("system_config.views", "AuditLogViewSet"),
    ("system_config.views", "SystemConfigDashboardViewSet"),
]


def _import_viewset(module_path, class_name):
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def test_every_tenant_scoped_viewset_applies_tenant_context_for_jwt_requests():
    missing = []
    for module_path, class_name in TENANT_SCOPED_VIEWSETS:
        cls = _import_viewset(module_path, class_name)
        assert issubclass(cls, viewsets.ViewSetMixin), f"{class_name} is not a DRF ViewSet — update this test's list"
        if not issubclass(cls, TenantScopedAPIMixin):
            missing.append(f"{module_path}.{class_name}")
    assert not missing, (
        "These tenant-scoped ViewSets don't inherit TenantScopedAPIMixin — "
        "JWT-authenticated requests to them will fail (writes) or silently "
        f"return nothing (reads) under RLS enforcement: {missing}"
    )


def test_platform_level_viewsets_also_apply_tenant_context():
    """Not a tenant-isolation bug if missing (Super-Admin-only, fails
    closed), but still wrong: a superuser's own JWT request would see
    empty results without this, since RLS's is_platform_admin GUC is set
    by the same mixin, not by Django's is_superuser flag."""
    missing = []
    for module_path, class_name in PLATFORM_LEVEL_VIEWSETS_WITH_MIXIN_ANYWAY:
        cls = _import_viewset(module_path, class_name)
        if not issubclass(cls, TenantScopedAPIMixin):
            missing.append(f"{module_path}.{class_name}")
    assert not missing, f"Missing TenantScopedAPIMixin: {missing}"
