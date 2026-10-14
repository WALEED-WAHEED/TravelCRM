"""
Regression test for a real bug found via user report: deleting a Hotel
(or Transport) from the catalog used to CASCADE-delete every BookingHotel
row referencing it — including line items on already-confirmed/completed
bookings, silently rewriting an already-issued voucher's printed history
(voucher_document.html renders BookingHotel.hotel_name/city, a snapshot
taken at booking time, not a live hotel.name lookup).

Fixed via member/models.py (SET_NULL instead of CASCADE, since the
snapshot fields make the FK itself non-essential for display) plus
member/signals.py's pre_delete handler, which additionally drops the
line item outright for still-draft bookings (those aren't historical
yet, so a dangling null-hotel row there would just look broken).
"""
import datetime

import pytest

from utils.tenancy import tenant_context


@pytest.fixture
def draft_and_confirmed_bookings_with_hotel(agency_a, user_a, hotel_a):
    from member.models import Booking, BookingHotel

    with tenant_context(bypass=True):
        draft = Booking.objects.create(
            agency=agency_a, status="draft", total_amount=100, total_price=100,
            agent=user_a, voucher_number="A-VCH-DRAFT",
        )
        confirmed = Booking.objects.create(
            agency=agency_a, status="confirmed", total_amount=200, total_price=200,
            agent=user_a, voucher_number="A-VCH-CONFIRMED",
        )
        check_in = datetime.date.today()
        draft_line = BookingHotel.objects.create(
            booking=draft, hotel=hotel_a, city=hotel_a.city, hotel_name=hotel_a.name,
            check_in=check_in, check_out=check_in + datetime.timedelta(days=3), nights=3,
        )
        confirmed_line = BookingHotel.objects.create(
            booking=confirmed, hotel=hotel_a, city=hotel_a.city, hotel_name=hotel_a.name,
            check_in=check_in, check_out=check_in + datetime.timedelta(days=3), nights=3,
        )
    return draft_line, confirmed_line


@pytest.mark.django_db
def test_deleting_hotel_drops_the_line_item_on_a_draft_booking(hotel_a, draft_and_confirmed_bookings_with_hotel):
    from member.models import BookingHotel

    draft_line, _confirmed_line = draft_and_confirmed_bookings_with_hotel
    with tenant_context(bypass=True):
        hotel_a.delete()
        assert not BookingHotel.objects.filter(pk=draft_line.pk).exists()


@pytest.mark.django_db
def test_deleting_hotel_preserves_the_line_item_and_snapshot_on_a_confirmed_booking(hotel_a, draft_and_confirmed_bookings_with_hotel):
    _draft_line, confirmed_line = draft_and_confirmed_bookings_with_hotel
    hotel_name, city = confirmed_line.hotel_name, confirmed_line.city
    with tenant_context(bypass=True):
        hotel_a.delete()
        confirmed_line.refresh_from_db()
        assert confirmed_line.hotel_id is None
        assert confirmed_line.hotel_name == hotel_name
        assert confirmed_line.city == city


@pytest.mark.django_db
def test_resaving_a_booking_does_not_wipe_an_orphaned_hotel_line_item(hotel_a, draft_and_confirmed_bookings_with_hotel):
    """The deeper gap: _replace_booking_line_items used to wipe *every*
    existing line item on each save and rebuild only from the submitted
    payload — which can never include a row whose hotel was deleted
    (the client only ever submits picks from the live catalog). Editing
    an already-confirmed booking for any unrelated reason (e.g. fixing a
    typo in notes) after the hotel was deleted would silently drop that
    line item on the very next save, even though the SET_NULL fix above
    protects it from the hotel deletion itself."""
    from member.views import _replace_booking_line_items

    _draft_line, confirmed_line = draft_and_confirmed_bookings_with_hotel
    booking = confirmed_line.booking
    agency = booking.agency
    hotel_name = confirmed_line.hotel_name
    with tenant_context(bypass=True):
        hotel_a.delete()
        confirmed_line.refresh_from_db()
        assert confirmed_line.hotel_id is None

        # Simulate resaving the booking worksheet with an empty payload
        # (the orphaned row has no valid hotel_id to resubmit).
        _replace_booking_line_items(agency, booking, [], [], [], [], [])

        confirmed_line.refresh_from_db()
        assert confirmed_line.hotel_name == hotel_name
