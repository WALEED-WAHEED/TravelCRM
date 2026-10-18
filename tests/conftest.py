"""
Shared fixtures for the Phase 11 test suite.

Two fully separate tenants (agency_a/agency_b, each with their own owner
user) are the backbone of almost every test here — tenant isolation can
only be proven by having two tenants and showing one can never see the
other's rows, through any path.
"""
import pytest
from django.test import Client

from utils.tenancy import tenant_context


@pytest.fixture(autouse=True)
def _celery_runs_inline(settings):
    """
    Run Celery tasks in-process during tests. Without this, a reachable Redis
    (e.g. the compose `redis` container) would swallow the notification tasks
    into the real queue — the tests would see no emails, and a running worker
    would try to process test bookings against the real database.
    """
    from travelcrm.celery import app

    settings.CELERY_TASK_ALWAYS_EAGER = True
    app.conf.task_always_eager = True
    yield
    app.conf.task_always_eager = False


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    The test database is created fresh (CREATE DATABASE test_..., not a
    clone of the real one), so it doesn't inherit the GRANTs the real
    database has for the scoped `travelcrm_app` role — every RLS test
    would otherwise fail with "permission denied", which looks like a
    tenant-isolation bug but is actually just a missing grant. Re-grant
    on the test database itself, once per test session.
    """
    with django_db_blocker.unblock():
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO travelcrm_app;")
            cursor.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO travelcrm_app;")
    yield


@pytest.fixture(autouse=True)
def _ensure_rbac_templates(db):
    """
    The four global role templates (Owner/Manager/Agent/Read-only) are
    seeded once by a data migration
    (rbac/migrations/0002_seed_catalog.py), not created per-test. But
    tests marked `transaction=True` (the RLS tests) get their tables
    flushed by Django after each one runs — and Django's flush doesn't
    distinguish "migration-seeded data" from "data this test created",
    so it wipes the template rows too. Every view gated by
    member_required/agent_required depends on a template existing, so a
    test run order where a transactional test happens to run first would
    otherwise make every later permission check silently fail. Re-seed
    idempotently before every test rather than depend on flush/rollback
    ordering to preserve migration data correctly.
    """
    from rbac import engine as rbac_engine
    from rbac.catalog import CAPABILITIES, TEMPLATE_LEVELS, TEMPLATES
    from rbac.models import Permission, Role

    with tenant_context(bypass=True):
        if Role.all_tenants.filter(is_template=True).count() == len(TEMPLATES):
            return
        # _template_role() is process-cached; a cached instance from before
        # a flush would still report the right .level but an empty M2M
        # (permissions table got flushed too), so drop the cache whenever
        # we actually have to reseed.
        rbac_engine._template_role.cache_clear()
        perm_by_key = {}
        for capability, _label in CAPABILITIES:
            for action in ("view", "manage"):
                perm, _ = Permission.objects.get_or_create(capability=capability, action=action)
                perm_by_key[(capability, action)] = perm
        for name, grants in TEMPLATES.items():
            role, _ = Role.all_tenants.get_or_create(
                agency=None, name=name,
                defaults={"is_template": True, "level": TEMPLATE_LEVELS[name]},
            )
            role.is_template = True
            role.level = TEMPLATE_LEVELS[name]
            role.save()
            perm_ids = [
                perm_by_key[(capability, action)].id
                for capability, actions in grants.items()
                for action in actions
            ]
            role.permissions.set(perm_ids)


@pytest.fixture
def agency_a(db):
    from agencies.models import Agency
    with tenant_context(bypass=True):
        return Agency.objects.create(
            name="Agency A", code="AGENCY-A", email="a@example.com",
            phone="0300", address="Addr A", city="Lahore", state="Punjab",
            country="Pakistan", postal_code="54000",
        )


@pytest.fixture
def agency_b(db):
    from agencies.models import Agency
    with tenant_context(bypass=True):
        return Agency.objects.create(
            name="Agency B", code="AGENCY-B", email="b@example.com",
            phone="0300", address="Addr B", city="Karachi", state="Sindh",
            country="Pakistan", postal_code="75000",
        )


def _make_owner(agency, username):
    from accounts.models import User
    with tenant_context(bypass=True):
        user = User.objects.create_user(
            username=username, password="TestPass123!",
            role="member", agency=agency,
        )
    return user


@pytest.fixture
def user_a(agency_a):
    return _make_owner(agency_a, "owner_a")


@pytest.fixture
def user_b(agency_b):
    return _make_owner(agency_b, "owner_b")


@pytest.fixture
def client_a(user_a):
    c = Client()
    c.force_login(user_a)
    return c


@pytest.fixture
def client_b(user_b):
    c = Client()
    c.force_login(user_b)
    return c


@pytest.fixture
def hotel_a(agency_a, user_a):
    from member.models import Hotel
    with tenant_context(bypass=True):
        return Hotel.objects.create(
            name="Hotel A", address="Addr", city="Makkah", country="Saudi Arabia",
            sale_price=100, purchase_price=80, agency=agency_a, created_by=user_a,
        )


@pytest.fixture
def hotel_b(agency_b, user_b):
    from member.models import Hotel
    with tenant_context(bypass=True):
        return Hotel.objects.create(
            name="Hotel B", address="Addr", city="Madina", country="Saudi Arabia",
            sale_price=100, purchase_price=80, agency=agency_b, created_by=user_b,
        )


@pytest.fixture
def flight_a(agency_a, user_a):
    from member.models import Flight
    with tenant_context(bypass=True):
        return Flight.objects.create(
            airline="Test Air", flight_number="TA-100",
            departure_city="Lahore", arrival_city="Jeddah",
            sale_price=500, purchase_price=400, agency=agency_a, created_by=user_a,
        )


@pytest.fixture
def booking_a(agency_a, user_a):
    from member.models import Booking
    with tenant_context(bypass=True):
        return Booking.objects.create(
            agency=agency_a, status="confirmed", total_amount=1000,
            agent=user_a, voucher_number="A-VCH-001",
        )


@pytest.fixture
def booking_b(agency_b, user_b):
    from member.models import Booking
    with tenant_context(bypass=True):
        return Booking.objects.create(
            agency=agency_b, status="confirmed", total_amount=2000,
            agent=user_b, voucher_number="B-VCH-001",
        )
