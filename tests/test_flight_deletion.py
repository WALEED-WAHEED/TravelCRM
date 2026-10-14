"""
Same fix, same reasoning as test_hotel_deletion.py — extended to Flight
once BookingFlight got its own airline/flight_number/route/class/PNR
snapshot fields (it had none before, unlike BookingHotel/BookingTransport,
so voucher_document.html used to dereference bf.flight.* live).
"""
import pytest

from utils.tenancy import tenant_context


@pytest.fixture
def draft_and_confirmed_bookings_with_flight(agency_a, user_a, flight_a):
    from member.models import Booking, BookingFlight

    with tenant_context(bypass=True):
        draft = Booking.objects.create(
            agency=agency_a, status="draft", total_amount=100, total_price=100,
            agent=user_a, voucher_number="A-VCH-FLIGHT-DRAFT",
        )
        confirmed = Booking.objects.create(
            agency=agency_a, status="confirmed", total_amount=200, total_price=200,
            agent=user_a, voucher_number="A-VCH-FLIGHT-CONFIRMED",
        )
        common = dict(
            flight=flight_a, flight_type="outbound",
            airline=flight_a.airline, flight_number=flight_a.flight_number,
            departure_city=flight_a.departure_city, arrival_city=flight_a.arrival_city,
            flight_class=flight_a.flight_class, pnr_number="PNR123",
        )
        draft_line = BookingFlight.objects.create(booking=draft, **common)
        confirmed_line = BookingFlight.objects.create(booking=confirmed, **common)
    return draft_line, confirmed_line


@pytest.mark.django_db
def test_deleting_flight_drops_the_line_item_on_a_draft_booking(flight_a, draft_and_confirmed_bookings_with_flight):
    from member.models import BookingFlight

    draft_line, _confirmed_line = draft_and_confirmed_bookings_with_flight
    with tenant_context(bypass=True):
        flight_a.delete()
        assert not BookingFlight.objects.filter(pk=draft_line.pk).exists()


@pytest.mark.django_db
def test_deleting_flight_preserves_the_line_item_and_snapshot_on_a_confirmed_booking(flight_a, draft_and_confirmed_bookings_with_flight):
    _draft_line, confirmed_line = draft_and_confirmed_bookings_with_flight
    airline, flight_number, dep, arr, pnr = (
        confirmed_line.airline, confirmed_line.flight_number,
        confirmed_line.departure_city, confirmed_line.arrival_city, confirmed_line.pnr_number,
    )
    with tenant_context(bypass=True):
        flight_a.delete()
        confirmed_line.refresh_from_db()
        assert confirmed_line.flight_id is None
        assert confirmed_line.airline == airline
        assert confirmed_line.flight_number == flight_number
        assert confirmed_line.departure_city == dep
        assert confirmed_line.arrival_city == arr
        assert confirmed_line.pnr_number == pnr
