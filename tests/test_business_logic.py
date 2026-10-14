"""
Core business logic: payment collection reconciling into the ledger
automatically, and per-tenant (not global) uniqueness on fields that used
to collide the moment a second tenant existed (Phase 01's whole point).
"""
import pytest

from utils.tenancy import tenant_context


@pytest.mark.django_db
def test_recording_a_payment_creates_a_matching_ledger_entry(client_a, booking_a):
    from member.models import BookingPayment, LedgerEntry

    resp = client_a.post(f"/member/bookings/{booking_a.id}/collect-payment/", {
        "amount": "350.00", "payment_method": "cash", "transaction_id": "TXN-1",
    })
    assert resp.status_code == 302

    with tenant_context(agency_id=booking_a.agency_id):
        payment = BookingPayment.objects.get(booking=booking_a, transaction_id="TXN-1")
        assert payment.amount == 350
        assert payment.status == "paid"

        entry = LedgerEntry.objects.get(booking=booking_a)
        assert entry.amount == 350
        assert entry.direction == "credit"
        assert entry.agency_id == booking_a.agency_id


@pytest.mark.django_db
def test_payment_against_an_installment_marks_it_paid(client_a, booking_a, agency_a, user_a):
    from datetime import date

    from payments.models import Installment, PaymentPlan

    with tenant_context(bypass=True):
        plan = PaymentPlan.objects.create(booking=booking_a, agency=agency_a, created_by=user_a)
        installment = Installment.objects.create(
            payment_plan=plan, agency=agency_a, sequence=1,
            label="Deposit", amount=200, due_date=date.today(),
        )

    resp = client_a.post(f"/member/bookings/{booking_a.id}/collect-payment/", {
        "amount": "200.00", "payment_method": "cash",
        "installment_id": str(installment.id),
    })
    assert resp.status_code == 302

    with tenant_context(agency_id=agency_a.id):
        installment.refresh_from_db()
        assert installment.status == "paid"


@pytest.mark.django_db
def test_duplicate_idempotency_key_does_not_double_charge(client_a, booking_a):
    from member.models import BookingPayment

    client_a.post(f"/member/bookings/{booking_a.id}/collect-payment/", {
        "amount": "100.00", "payment_method": "cash", "idempotency_key": "same-key",
    })
    client_a.post(f"/member/bookings/{booking_a.id}/collect-payment/", {
        "amount": "100.00", "payment_method": "cash", "idempotency_key": "same-key",
    })

    with tenant_context(agency_id=booking_a.agency_id):
        assert BookingPayment.objects.filter(idempotency_key="same-key").count() == 1


@pytest.mark.django_db
def test_hotel_code_uniqueness_is_per_tenant_not_global(agency_a, agency_b, user_a, user_b):
    """Phase 01's core deliverable: two agencies can use the identical
    hotel code without colliding — uniqueness is scoped by (agency, code)."""
    from member.models import Hotel

    with tenant_context(bypass=True):
        Hotel.objects.create(
            name="Hotel A", code="SHARED-CODE", address="x", city="Makkah",
            country="Saudi Arabia", sale_price=100, purchase_price=80,
            agency=agency_a, created_by=user_a,
        )
        # Must NOT raise IntegrityError even though the code matches exactly.
        Hotel.objects.create(
            name="Hotel B", code="SHARED-CODE", address="x", city="Madina",
            country="Saudi Arabia", sale_price=100, purchase_price=80,
            agency=agency_b, created_by=user_b,
        )
        assert Hotel.all_tenants.filter(code="SHARED-CODE").count() == 2


@pytest.mark.django_db
def test_hotel_code_still_unique_within_the_same_tenant(agency_a, user_a):
    from django.db import IntegrityError

    from member.models import Hotel

    with tenant_context(bypass=True):
        Hotel.objects.create(
            name="Hotel A1", code="DUPE", address="x", city="Makkah",
            country="Saudi Arabia", sale_price=100, purchase_price=80,
            agency=agency_a, created_by=user_a,
        )
        with pytest.raises(IntegrityError):
            Hotel.objects.create(
                name="Hotel A2", code="DUPE", address="x", city="Makkah",
                country="Saudi Arabia", sale_price=100, purchase_price=80,
                agency=agency_a, created_by=user_a,
            )
