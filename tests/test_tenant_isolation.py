"""
Tenant isolation — the single most important property this platform has
to hold. Two layers are tested independently:

1. ORM layer (utils.tenancy.TenantManager) — Python-side, contextvar-driven.
2. RLS layer (Postgres Row-Level Security) — database-side, enforced even
   if the ORM layer were bypassed entirely (raw SQL, a future management
   command, a bug in the middleware).

RLS is inert for a table owner or superuser, so the RLS tests connect
through the 'scoped' database alias (the real `travelcrm_app` role) rather
than the 'default' connection — see travelcrm/settings.py DATABASES and
tests/conftest.py. Getting this wrong (testing RLS through a superuser
connection) would make these tests pass even if RLS were completely
broken, which is worse than not having them.
"""
import pytest
from django.db import connections

from utils.tenancy import clear_current_tenant, set_current_tenant, set_platform_admin_bypass, tenant_context

# ---------------------------------------------------------------------------
# Layer 1: ORM (TenantManager)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_orm_hides_other_tenant_hotels(agency_a, agency_b, hotel_a, hotel_b):
    from member.models import Hotel
    set_current_tenant(agency_a.id)
    set_platform_admin_bypass(False)
    try:
        visible = list(Hotel.objects.all())
    finally:
        clear_current_tenant()
    assert hotel_a in visible
    assert hotel_b not in visible


@pytest.mark.django_db
def test_orm_hides_other_tenant_bookings(agency_a, agency_b, booking_a, booking_b):
    from member.models import Booking
    set_current_tenant(agency_b.id)
    set_platform_admin_bypass(False)
    try:
        visible = list(Booking.objects.all())
    finally:
        clear_current_tenant()
    assert booking_b in visible
    assert booking_a not in visible


@pytest.mark.django_db
def test_orm_explicit_cross_tenant_filter_still_returns_nothing(agency_a, hotel_b):
    """Even asking for the other tenant's row by its own ID must come back
    empty — the manager filters *before* any .filter()/.get() the caller adds."""
    from member.models import Hotel
    set_current_tenant(agency_a.id)
    set_platform_admin_bypass(False)
    try:
        assert not Hotel.objects.filter(id=hotel_b.id).exists()
        with pytest.raises(Hotel.DoesNotExist):
            Hotel.objects.get(id=hotel_b.id)
    finally:
        clear_current_tenant()


@pytest.mark.django_db
def test_orm_no_tenant_context_is_fail_closed(hotel_a, hotel_b):
    """No tenant context set at all (e.g. a code path that forgot to call
    the middleware/context manager) must see nothing, not everything."""
    from member.models import Hotel
    clear_current_tenant()
    set_platform_admin_bypass(False)
    assert list(Hotel.objects.all()) == []


@pytest.mark.django_db
def test_orm_bypass_sees_every_tenant(agency_a, agency_b, hotel_a, hotel_b):
    from member.models import Hotel
    set_platform_admin_bypass(True)
    try:
        visible = set(Hotel.objects.all())
    finally:
        set_platform_admin_bypass(False)
    assert {hotel_a, hotel_b} <= visible


@pytest.mark.django_db
def test_tenant_context_manager_restores_previous_state(agency_a, agency_b, hotel_a, hotel_b):
    from member.models import Hotel
    set_current_tenant(agency_a.id)
    set_platform_admin_bypass(False)
    try:
        with tenant_context(agency_id=agency_b.id):
            assert list(Hotel.objects.all()) == [hotel_b]
        # back to agency_a after the `with` block exits
        assert list(Hotel.objects.all()) == [hotel_a]
    finally:
        clear_current_tenant()


# ---------------------------------------------------------------------------
# Layer 2: Postgres Row-Level Security, via the scoped `travelcrm_app` role
# ---------------------------------------------------------------------------

RLS_TABLES = [
    "member_hotel", "member_flight", "member_transport", "member_package", "member_attendancelog",
    "member_contact", "member_contactinstruction", "member_voucherinstruction",
    "member_booking", "member_voucher", "member_ledgerentry", "member_vouchersequence",
    "notifications_notificationdeliverylog",
]


def _set_rls_context(cursor, tenant_id, bypass=False):
    cursor.execute("SELECT set_config('app.is_platform_admin', %s, false)", ["true" if bypass else "false"])
    cursor.execute(
        "SELECT set_config('app.current_tenant_id', %s, false)",
        [str(tenant_id) if tenant_id is not None else ""],
    )


@pytest.mark.django_db(databases=["default", "scoped"], transaction=True, serialized_rollback=True)
def test_rls_enabled_on_every_tenant_table():
    """Meta-test: guards against a future migration accidentally dropping
    RLS on one of these tables without anyone noticing."""
    cur = connections["scoped"].cursor()
    cur.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "AND rowsecurity = true AND tablename = ANY(%s)",
        [RLS_TABLES],
    )
    enabled = {row[0] for row in cur.fetchall()}
    missing = set(RLS_TABLES) - enabled
    assert not missing, f"RLS disabled on: {missing}"


@pytest.mark.django_db(databases=["default", "scoped"], transaction=True, serialized_rollback=True)
def test_rls_blocks_cross_tenant_select_with_explicit_filter(agency_a, agency_b, hotel_a, hotel_b):
    cur = connections["scoped"].cursor()
    _set_rls_context(cur, agency_a.id)
    cur.execute("SELECT id FROM member_hotel WHERE agency_id = %s", [agency_b.id])
    assert cur.fetchall() == []


@pytest.mark.django_db(databases=["default", "scoped"], transaction=True, serialized_rollback=True)
def test_rls_blocks_cross_tenant_select_with_no_filter_at_all(agency_a, agency_b, hotel_a, hotel_b):
    """The dangerous case: a query with *no* WHERE clause at all — exactly
    what a forgotten `.filter(agency=...)` in application code would run."""
    cur = connections["scoped"].cursor()
    _set_rls_context(cur, agency_a.id)
    cur.execute("SELECT id, agency_id FROM member_hotel")
    rows = cur.fetchall()
    assert all(row[1] == agency_a.id for row in rows)
    assert (hotel_b.id, agency_b.id) not in rows


@pytest.mark.django_db(databases=["default", "scoped"], transaction=True, serialized_rollback=True)
def test_rls_allows_own_tenant_rows(agency_a, hotel_a):
    cur = connections["scoped"].cursor()
    _set_rls_context(cur, agency_a.id)
    cur.execute("SELECT id FROM member_hotel WHERE id = %s", [hotel_a.id])
    assert cur.fetchall() == [(hotel_a.id,)]


@pytest.mark.django_db(databases=["default", "scoped"], transaction=True, serialized_rollback=True)
def test_rls_no_tenant_set_sees_nothing(agency_a, hotel_a):
    """No `app.current_tenant_id` GUC set at all (fresh connection, never
    initialized) must also fail closed at the database layer."""
    cur = connections["scoped"].cursor()
    cur.execute("SELECT set_config('app.is_platform_admin', 'false', false)")
    cur.execute("SELECT set_config('app.current_tenant_id', '', false)")
    cur.execute("SELECT id FROM member_hotel")
    assert cur.fetchall() == []


@pytest.mark.django_db(databases=["default", "scoped"], transaction=True, serialized_rollback=True)
def test_rls_platform_admin_bypass_sees_everything(agency_a, agency_b, hotel_a, hotel_b):
    cur = connections["scoped"].cursor()
    _set_rls_context(cur, None, bypass=True)
    cur.execute("SELECT id FROM member_hotel WHERE id IN (%s, %s)", [hotel_a.id, hotel_b.id])
    ids = {row[0] for row in cur.fetchall()}
    assert ids == {hotel_a.id, hotel_b.id}


@pytest.mark.django_db(databases=["default", "scoped"], transaction=True, serialized_rollback=True)
def test_rls_blocks_cross_tenant_ledger_entries(agency_a, agency_b, booking_a, booking_b):
    """Financial data (the ledger) gets its own explicit check — the
    highest-consequence table if isolation ever failed."""
    from datetime import date

    from member.models import LedgerEntry
    with tenant_context(bypass=True):
        LedgerEntry.objects.create(
            agency=agency_a, booking=booking_a, transaction_type="booking",
            transaction_date=date.today(), payment_method="cash",
            amount=500, description="A payment",
        )
        LedgerEntry.objects.create(
            agency=agency_b, booking=booking_b, transaction_type="booking",
            transaction_date=date.today(), payment_method="cash",
            amount=999, description="B payment",
        )

    cur = connections["scoped"].cursor()
    _set_rls_context(cur, agency_a.id)
    cur.execute("SELECT amount FROM member_ledgerentry")
    amounts = [row[0] for row in cur.fetchall()]
    assert amounts == [500]


# ---------------------------------------------------------------------------
# tenant_context mirrors onto the DB session (needed when the app runs as the
# scoped role, where RLS - not just the ORM - decides which rows are visible)
# ---------------------------------------------------------------------------


def _guc():
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT current_setting('app.current_tenant_id', true), current_setting('app.is_platform_admin', true)")
        return cur.fetchone()


def test_tenant_context_sets_and_restores_db_session(agency_a, agency_b):
    from utils.tenancy import tenant_context

    before = _guc()
    with tenant_context(agency_id=agency_a.id):
        assert _guc() == (str(agency_a.id), "false")
        with tenant_context(agency_id=agency_b.id):
            assert _guc() == (str(agency_b.id), "false")
        assert _guc() == (str(agency_a.id), "false")
        with tenant_context(bypass=True):
            assert _guc() == ("", "true")
        assert _guc() == (str(agency_a.id), "false")
    after = _guc()
    assert after[1] == "false"
    assert after[0] in ("", None, before[0])


@pytest.mark.django_db(databases=["default", "scoped"], transaction=True, serialized_rollback=True)
def test_rls_blocks_cross_tenant_notification_delivery_log(agency_a, agency_b):
    from notifications.models import NotificationDeliveryLog

    with tenant_context(bypass=True):
        NotificationDeliveryLog.all_tenants.create(agency=agency_a, event_type="voucher_generated", channel="email", status="sent", recipient="a@example.com")
        NotificationDeliveryLog.all_tenants.create(agency=agency_b, event_type="voucher_generated", channel="email", status="sent", recipient="b@example.com")
    cur = connections["scoped"].cursor()
    _set_rls_context(cur, agency_a.id)
    cur.execute("SELECT recipient FROM notifications_notificationdeliverylog")
    assert [r[0] for r in cur.fetchall()] == ["a@example.com"]
