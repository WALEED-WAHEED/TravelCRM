"""
Tests for the expanded Super Admin panel: platform staff RBAC (a real
superuser always passes; a non-superuser is_staff account only passes
with the right capability), suspend-with-reason, the audit-trail
expansion to billing/system_config models (and that secrets never leak
into the diff), and tenant broadcast messaging targeting.
"""
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from utils.tenancy import tenant_context


@pytest.fixture
def superuser(db):
    from accounts.models import User
    with tenant_context(bypass=True):
        return User.objects.create_user(
            username="root_admin", password="TestPass123!", is_superuser=True, is_staff=True,
        )


@pytest.fixture
def superuser_client(superuser):
    c = Client()
    c.force_login(superuser)
    return c


@pytest.fixture
def staff_user(db):
    from accounts.models import User
    with tenant_context(bypass=True):
        return User.objects.create_user(username="scoped_staff", password="TestPass123!", is_staff=True)


def _staff_client(staff_user, capabilities):
    from platform_admin.models import StaffAccess
    with tenant_context(bypass=True):
        StaffAccess.objects.create(user=staff_user, capabilities=capabilities)
    c = Client()
    c.force_login(staff_user)
    return c


@pytest.mark.django_db
def test_superuser_bypasses_capability_check_with_no_staffaccess_row(superuser_client):
    resp = superuser_client.get('/platform-admin/plans/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_staff_without_the_right_capability_is_blocked(staff_user):
    client = _staff_client(staff_user, capabilities=['tenants.view'])
    resp = client.get('/platform-admin/plans/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_staff_with_the_right_capability_is_allowed(staff_user):
    client = _staff_client(staff_user, capabilities=['billing.view'])
    resp = client.get('/platform-admin/plans/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_plain_staff_flag_with_no_staffaccess_row_is_blocked(staff_user):
    """is_staff alone (no StaffAccess row at all) must not grant access —
    only is_superuser, or is_staff + an explicit granted capability."""
    client = Client()
    client.force_login(staff_user)
    resp = client.get('/platform-admin/plans/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_only_a_real_superuser_can_reach_staff_management(staff_user):
    """Staff management is root-only (superadmin_required), never
    delegable via a capability — granting staff access is a bootstrap
    action."""
    client = _staff_client(staff_user, capabilities=['tenants.manage', 'billing.manage', 'system_config.manage', 'audit.view', 'analytics.view', 'tenants.view'])
    resp = client.get('/platform-admin/staff/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_suspend_captures_reason_and_actor(superuser_client, superuser, agency_a):
    resp = superuser_client.post(f'/platform-admin/tenants/{agency_a.pk}/suspend/', {'reason': 'non-payment'})
    assert resp.status_code == 302
    agency_a.refresh_from_db()
    assert agency_a.is_active is False
    assert agency_a.suspended_reason == 'non-payment'
    assert agency_a.suspended_by_id == superuser.pk
    assert agency_a.suspended_at is not None


@pytest.mark.django_db
def test_activate_clears_suspension_fields(superuser_client, superuser, agency_a):
    superuser_client.post(f'/platform-admin/tenants/{agency_a.pk}/suspend/', {'reason': 'abuse'})
    resp = superuser_client.post(f'/platform-admin/tenants/{agency_a.pk}/activate/')
    assert resp.status_code == 302
    agency_a.refresh_from_db()
    assert agency_a.is_active is True
    assert agency_a.suspended_reason == ''
    assert agency_a.suspended_by_id is None
    assert agency_a.suspended_at is None


@pytest.mark.django_db
def test_billing_critical_models_now_produce_audit_log_rows():
    """Real gap found in the audit: Plan/Subscription/PaymentRecord and
    the system_config models weren't in register_audited_models()'s list
    — billing-sensitive actions left no trace. Now they should."""
    from billing.models import Plan
    from system_config.models import AuditLog

    with tenant_context(bypass=True):
        plan = Plan.objects.create(name="Regression Test Plan", slug="regression-test-plan", price_amount=10)
        assert AuditLog.all_tenants.filter(model_name="Plan", action="create", object_id=str(plan.pk)).exists()


@pytest.mark.django_db
def test_api_key_secrets_never_land_in_audit_diff():
    """api_key/api_secret must never appear in an AuditLog diff — even
    when changed alongside a non-excluded field that does produce a
    logged "update" (changing *only* an excluded field correctly
    produces no entry at all, since there'd be nothing to show)."""
    from system_config.models import APIKey, AuditLog

    with tenant_context(bypass=True):
        key = APIKey.all_tenants.create(name="Test Key", key_type="other", api_key="super-secret-value", api_secret="also-secret")
        key.name = "Renamed Key"
        key.api_key = "rotated-secret-value"
        key.save()
        entry = AuditLog.all_tenants.filter(model_name="APIKey", action="update", object_id=str(key.pk)).first()
        assert entry is not None
        assert entry.changes.get("name") == {"old": "Test Key", "new": "Renamed Key"}
        assert "api_key" not in entry.changes
        assert "api_secret" not in entry.changes
        assert "super-secret-value" not in str(entry.changes)
        assert "rotated-secret-value" not in str(entry.changes)


@pytest.mark.django_db
def test_announcement_targets_all_tenants_when_blank(agency_a):
    from platform_admin.context_processors import active_announcements
    from platform_admin.models import Announcement

    with tenant_context(bypass=True):
        Announcement.objects.create(title="Maintenance", body="Downtime tonight")

    class FakeUser:
        is_authenticated = True
        agency_id = agency_a.pk

    class FakeRequest:
        user = FakeUser()

    result = active_announcements(FakeRequest())
    assert len(result['active_announcements']) == 1


@pytest.mark.django_db
def test_announcement_scoped_to_other_agency_is_excluded(agency_a, agency_b):
    from platform_admin.context_processors import active_announcements
    from platform_admin.models import Announcement

    with tenant_context(bypass=True):
        ann = Announcement.objects.create(title="Agency B only", body="...")
        ann.target_agencies.set([agency_b])

    class FakeUser:
        is_authenticated = True
        agency_id = agency_a.pk

    class FakeRequest:
        user = FakeUser()

    result = active_announcements(FakeRequest())
    assert len(result['active_announcements']) == 0


@pytest.mark.django_db
def test_expired_announcement_is_excluded(agency_a):
    from platform_admin.context_processors import active_announcements
    from platform_admin.models import Announcement

    with tenant_context(bypass=True):
        Announcement.objects.create(
            title="Old notice", body="...", ends_at=timezone.now() - timedelta(days=1),
        )

    class FakeUser:
        is_authenticated = True
        agency_id = agency_a.pk

    class FakeRequest:
        user = FakeUser()

    result = active_announcements(FakeRequest())
    assert len(result['active_announcements']) == 0
