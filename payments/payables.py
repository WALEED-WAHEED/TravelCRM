"""
Supplier payables are computed live from confirmed/completed bookings'
line items rather than maintained as a running balance — same reasoning
as billing/usage.py: a computed total can't drift out of sync with the
bookings it's based on.

Assumption, stated plainly since it's not obvious from the schema: each
Hotel/Flight/Transport's `purchase_price` is treated as the full cost of
that booked line item as entered (not multiplied by nights/segments) —
this mirrors how Booking.total_amount itself is a single agent-entered
figure elsewhere in the app, not a computed sum. If your pricing model
is actually per-night/per-seat, purchase_price should be entered as the
already-multiplied total for the stay/segment booked.
"""
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from member.models import BookingFlight, BookingHotel, BookingTransport, Contact, LedgerEntry

from .models import SupplierPayment

RELEVANT_BOOKING_STATUSES = ['confirmed', 'completed']


def _supplier_line_items(agency, supplier):
    hotel_lines = BookingHotel.objects.filter(
        booking__agency=agency, booking__status__in=RELEVANT_BOOKING_STATUSES, hotel__supplier=supplier,
    ).select_related('hotel', 'booking')
    flight_lines = BookingFlight.objects.filter(
        booking__agency=agency, booking__status__in=RELEVANT_BOOKING_STATUSES, flight__supplier=supplier,
    ).select_related('flight', 'booking')
    transport_lines = BookingTransport.objects.filter(
        booking__agency=agency, booking__status__in=RELEVANT_BOOKING_STATUSES, transport__supplier=supplier,
    ).select_related('transport', 'booking')
    return hotel_lines, flight_lines, transport_lines


def get_amount_owed(agency, supplier):
    hotel_lines, flight_lines, transport_lines = _supplier_line_items(agency, supplier)
    total = Decimal('0')
    total += sum((line.hotel.purchase_price for line in hotel_lines), start=Decimal('0'))
    total += sum((line.flight.purchase_price for line in flight_lines), start=Decimal('0'))
    total += sum((line.transport.purchase_price or Decimal('0') for line in transport_lines), start=Decimal('0'))
    return total


def get_amount_paid(agency, supplier):
    """Payments recorded either way count: SupplierPayment rows (which also
    auto-post a ledger 'expense' line, so those are not counted twice) plus
    'Made payment' entries entered directly in the ledger against this
    supplier's name."""
    total = SupplierPayment.objects.filter(agency=agency, supplier=supplier).aggregate(total=Sum('amount'))['total']
    ledger = LedgerEntry.objects.filter(
        agency=agency, bucket='lein_dein', direction='debit', transaction_type='payment',
        counterparty_name__iexact=supplier.name,
    ).aggregate(total=Sum('amount'))['total']
    return (total or Decimal('0')) + (ledger or Decimal('0'))


def is_overdue(agency, supplier):
    """Approximated from hotel checkout / transport travel date having
    passed on an unpaid balance — flights are excluded from the date
    check (no single reliable date at the BookingFlight level) but still
    count toward the owed/paid totals above."""
    owed = get_amount_owed(agency, supplier)
    paid = get_amount_paid(agency, supplier)
    if owed - paid <= 0:
        return False
    today = timezone.localdate()
    hotel_lines, _flight_lines, transport_lines = _supplier_line_items(agency, supplier)
    if hotel_lines.filter(check_out__lt=today).exists():
        return True
    if transport_lines.filter(travel_date__lt=today).exists():
        return True
    return False


def get_supplier_payables(agency):
    """One row per supplier Contact this agency has ever bought from,
    with owed/paid/balance/overdue — the payables dashboard's data."""
    supplier_ids = set()
    for model, field in [(BookingHotel, 'hotel__supplier'), (BookingFlight, 'flight__supplier'), (BookingTransport, 'transport__supplier')]:
        supplier_ids.update(
            model.objects.filter(booking__agency=agency, booking__status__in=RELEVANT_BOOKING_STATUSES)
            .exclude(**{f"{field}__isnull": True})
            .values_list(field, flat=True)
            .distinct()
        )

    rows = []
    for supplier in Contact.objects.filter(id__in=supplier_ids):
        owed = get_amount_owed(agency, supplier)
        paid = get_amount_paid(agency, supplier)
        rows.append({
            'supplier': supplier,
            'owed': owed,
            'paid': paid,
            'balance': owed - paid,
            'overdue': is_overdue(agency, supplier),
        })
    rows.sort(key=lambda r: r['balance'], reverse=True)
    return rows
