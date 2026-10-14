"""
Aggregation functions behind the Reports pages — no new models, this is
read-only analysis of data that already exists (BookingPayment,
LedgerEntry, Booking, Installment, SupplierPayment). Every function takes
an `agency` and queries through the default (tenant-scoped) manager, so
callers never need to filter by agency themselves.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from member.models import Booking, BookingPayment, LedgerEntry
from payments.models import Installment


def _last_n_months_labels(n):
    today = timezone.localdate()
    labels = []
    for i in range(n - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        labels.append((year, month))
    return labels


def revenue_over_time(agency, months=6):
    """Real monthly revenue (paid BookingPayments), replacing the fake
    booking-count proxy that used to live in the member dashboard."""
    since = timezone.now() - timedelta(days=31 * months)
    qs = (
        BookingPayment.objects.filter(booking__agency=agency, status='paid', created_at__gte=since)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('amount'))
    )
    by_month = {(m['month'].year, m['month'].month): m['total'] for m in qs if m['month']}

    labels, values = [], []
    for year, month in _last_n_months_labels(months):
        labels.append(f"{year:04d}-{month:02d}")
        values.append(float(by_month.get((year, month), Decimal('0'))))
    return labels, values


def bookings_by_status(agency):
    qs = Booking.objects.filter(agency=agency).values('status').annotate(count=Count('id')).order_by('status')
    counts = {row['status']: row['count'] for row in qs}
    return [{'status': choice, 'label': label, 'count': counts.get(choice, 0)} for choice, label in Booking.STATUS_CHOICES]


def ledger_summary(agency, months=6):
    """Monthly credit (money in) vs. debit (money out) across the whole
    ledger — party accounts and company expenses combined."""
    since = timezone.now() - timedelta(days=31 * months)
    qs = (
        LedgerEntry.objects.filter(agency=agency, created_at__gte=since)
        .annotate(month=TruncMonth('created_at'))
        .values('month', 'direction')
        .annotate(total=Sum('amount'))
    )
    credit_by_month, debit_by_month = {}, {}
    for row in qs:
        if not row['month']:
            continue
        key = (row['month'].year, row['month'].month)
        if row['direction'] == 'credit':
            credit_by_month[key] = row['total']
        else:
            debit_by_month[key] = row['total']

    labels, credits, debits = [], [], []
    for year, month in _last_n_months_labels(months):
        labels.append(f"{year:04d}-{month:02d}")
        credits.append(float(credit_by_month.get((year, month), Decimal('0'))))
        debits.append(float(debit_by_month.get((year, month), Decimal('0'))))
    return labels, credits, debits


def installments_due(agency, days=30):
    """Pending installments due within the window, plus anything already
    overdue — the same universe send_installment_reminders emails."""
    today = timezone.localdate()
    cutoff = today + timedelta(days=days)
    return (
        Installment.objects.filter(agency=agency, status__in=['pending', 'overdue'], due_date__lte=cutoff)
        .select_related('payment_plan__booking')
        .order_by('due_date')
    )
