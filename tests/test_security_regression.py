"""
Security regression tests: IDOR (can tenant A reach tenant B's objects by
guessing/incrementing an ID in a URL?) and permission-boundary checks (does
the RBAC layer actually deny what it claims to deny?).

These exist so a future change can't silently reopen either hole without
CI catching it — this is exactly the class of bug Phase 01/02 closed.
"""
import pytest

# ---------------------------------------------------------------------------
# IDOR: object-level access control via get_object_or_404(..., agency=agency)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_cannot_view_another_tenants_booking_by_id(client_a, booking_b):
    resp = client_a.get(f"/member/bookings/{booking_b.id}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_cannot_collect_payment_on_another_tenants_booking(client_a, booking_b):
    resp = client_a.post(f"/member/bookings/{booking_b.id}/collect-payment/", {
        "amount": "500", "payment_method": "cash",
    })
    assert resp.status_code == 404


@pytest.mark.django_db
def test_cannot_view_another_tenants_payment_plan(client_a, booking_b):
    resp = client_a.get(f"/member/bookings/{booking_b.id}/payment-plan/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_own_tenants_booking_is_reachable(client_a, booking_a):
    """Sanity check on the IDOR tests above — proves 404 means "blocked",
    not "URL/fixture is broken and everything 404s."""
    resp = client_a.get(f"/member/bookings/{booking_a.id}/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_cannot_delete_another_tenants_contact_instruction(client_a, agency_b, user_b):
    from member.models import ContactInstruction
    from utils.tenancy import tenant_context
    with tenant_context(bypass=True):
        contact_b = ContactInstruction.objects.create(
            agency=agency_b, created_by=user_b, city="Makkah",
            role="Helpline", contact_name="B's contact", phone_number="0300",
        )
    resp = client_a.post(f"/member/contacts/{contact_b.id}/delete/")
    assert resp.status_code == 404
    from utils.tenancy import tenant_context as tc
    with tc(bypass=True):
        assert ContactInstruction.objects.filter(id=contact_b.id).exists()


@pytest.mark.django_db
def test_public_voucher_requires_the_real_token(client_a, agency_b, user_b, booking_b):
    """The public voucher view is intentionally unauthenticated — its
    access control *is* the token. A wrong/guessed token must 404, not
    fall back to "no token filter" and leak the first voucher in the table."""
    from member.models import Voucher
    from utils.tenancy import tenant_context
    with tenant_context(bypass=True):
        Voucher.objects.create(
            agency=agency_b, agent=user_b, status="approved",
            total_amount=100, public_token="the-real-token",
            mutamer_name="Traveler", mutamer_passport_number="P1",
            mutamer_nationality="Pakistani", mutamer_gender="male",
        )
    resp = client_a.get("/public/voucher/not-the-real-token/")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Permission boundaries (RBAC)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_agent_role_cannot_reach_member_tier_views(agency_a):
    """/member/team/ requires the 'team:view' capability, which the
    'Agent' template (level 25) doesn't grant — must be a hard 403, not
    the page or its data."""
    from django.test import Client

    from accounts.models import User
    from utils.tenancy import tenant_context
    with tenant_context(bypass=True):
        agent_user = User.objects.create_user(
            username="agent_low_tier", password="TestPass123!",
            role="agent", agency=agency_a,
        )
    c = Client()
    c.force_login(agent_user)
    resp = c.get("/member/team/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unauthenticated_request_is_redirected_to_login(booking_a):
    from django.test import Client
    c = Client()
    resp = c.get(f"/member/bookings/{booking_a.id}/")
    assert resp.status_code == 302
    assert "/login/" in resp.url


@pytest.mark.django_db
def test_member_cannot_reach_platform_admin(client_a):
    """Platform Super Admin is a wholly separate control plane — a regular
    tenant user, however senior within their own agency, must never reach it."""
    resp = client_a.get("/platform-admin/")
    assert resp.status_code in (302, 403, 404)
    if resp.status_code == 302:
        assert "/platform-admin/" not in (resp.url or "")
