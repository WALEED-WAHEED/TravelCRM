"""
Completing a Booking (member workflow) should surface the same way an
agent's approved Voucher submission does — on the Vouchers page, with no
approval gate since a member did this directly. See
_sync_completed_booking_voucher in member/views.py.
"""
from decimal import Decimal

import pytest

from utils.tenancy import tenant_context


@pytest.mark.django_db
def test_completing_a_booking_with_one_traveler_creates_a_matching_voucher(booking_a):
    from member.models import BookingMutamer, Voucher
    from member.views import _sync_completed_booking_voucher

    class _FakeRequest:
        def __init__(self, user):
            self.user = user

    with tenant_context(bypass=True):
        BookingMutamer.objects.create(
            booking=booking_a, name="Amina Yusuf", passport_number="P1",
            nationality="Pakistani", gender="female", email="amina@example.com",
        )
        booking_a.status = "completed"
        booking_a.total_price = Decimal("500")
        booking_a.save()

        _sync_completed_booking_voucher(_FakeRequest(booking_a.agent), booking_a)

        voucher = Voucher.objects.get(booking=booking_a)
        assert voucher.status == "approved"
        assert voucher.mutamer_name == "Amina Yusuf"
        assert voucher.mutamer_passport_number == "P1"
        assert voucher.mutamer_email == "amina@example.com"
        assert voucher.total_amount == Decimal("500")
        assert voucher.agent_id == booking_a.agent_id
        assert voucher.agency_id == booking_a.agency_id
        assert voucher.approved_by_id == booking_a.agent_id
        assert voucher.services.count() == 1


@pytest.mark.django_db
def test_completing_a_booking_with_no_travelers_falls_back_to_client_company(booking_a):
    from member.models import Voucher
    from member.views import _sync_completed_booking_voucher

    class _FakeRequest:
        def __init__(self, user):
            self.user = user

    with tenant_context(bypass=True):
        booking_a.status = "completed"
        booking_a.client_company = "Fallback Travels"
        booking_a.save()

        _sync_completed_booking_voucher(_FakeRequest(booking_a.agent), booking_a)

        voucher = Voucher.objects.get(booking=booking_a)
        assert voucher.mutamer_name == "Fallback Travels"


@pytest.mark.django_db
def test_resaving_a_completed_booking_updates_the_same_voucher_not_a_second_one(booking_a):
    from member.models import Voucher
    from member.views import _sync_completed_booking_voucher

    class _FakeRequest:
        def __init__(self, user):
            self.user = user

    with tenant_context(bypass=True):
        booking_a.status = "completed"
        booking_a.client_company = "First Pass"
        booking_a.save()
        _sync_completed_booking_voucher(_FakeRequest(booking_a.agent), booking_a)
        first_id = Voucher.objects.get(booking=booking_a).id

        booking_a.client_company = "Second Pass"
        booking_a.save()
        _sync_completed_booking_voucher(_FakeRequest(booking_a.agent), booking_a)

        assert Voucher.objects.filter(booking=booking_a).count() == 1
        voucher = Voucher.objects.get(booking=booking_a)
        assert voucher.id == first_id
        assert voucher.mutamer_name == "Second Pass"


@pytest.mark.django_db
def test_reverting_status_away_from_completed_deletes_the_generated_voucher(booking_a):
    from member.models import Voucher
    from member.views import _sync_completed_booking_voucher

    class _FakeRequest:
        def __init__(self, user):
            self.user = user

    with tenant_context(bypass=True):
        booking_a.status = "completed"
        booking_a.save()
        _sync_completed_booking_voucher(_FakeRequest(booking_a.agent), booking_a)
        assert Voucher.objects.filter(booking=booking_a).exists()

        booking_a.status = "confirmed"
        booking_a.save()
        _sync_completed_booking_voucher(_FakeRequest(booking_a.agent), booking_a)

        assert not Voucher.objects.filter(booking=booking_a).exists()


@pytest.mark.django_db
def test_vouchers_page_lists_completed_bookings(client_a, booking_a):
    # The separate Vouchers page is gone; the Bookings page (shown as "Vouchers")
    # now lists every booking, completed ones included, and can filter to them.
    with tenant_context(bypass=True):
        booking_a.status = "completed"
        booking_a.save()

    resp = client_a.get("/member/bookings/")
    assert resp.status_code == 200
    assert booking_a.voucher_number.encode() in resp.content
    only_completed = client_a.get("/member/bookings/", {"status": "completed"})
    assert booking_a.voucher_number.encode() in only_completed.content
    assert client_a.get("/member/vouchers/").status_code == 404
