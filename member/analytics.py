"""
Shared analytics: one reporting period (with a granularity and a previous
period for comparison) used by the dashboard and every insights page.

Insights answer "what happened over time"; the dashboard answers "what needs
attention today". Everything here is read-only and goes through the default
tenant-scoped managers, so callers pass `agency` only to be explicit.

Money definitions (ledger is the single source of truth for cash):
  cash in   = credit entries of type receipt / booking (auto-posted payments) / income
  cash out  = debit entries of type payment / expense (supplier payments, company expenses)
  sales     = debit service lines (ticket, hotel, visa, transport, package) — charged to parties
  purchases = credit service lines — billed to you by suppliers
"""
import calendar
import datetime
from collections import OrderedDict
from decimal import Decimal

from django.utils import timezone
from django.utils.translation import gettext_lazy as _l

from member.models import Booking, LedgerEntry

ZERO = Decimal("0")

CASH_IN_TYPES = ("receipt", "booking", "income")
CASH_OUT_TYPES = ("payment", "expense")
SERVICE_TYPES = LedgerEntry.SERVICE_TYPES
ACTIVE_BOOKING_STATUSES = ("confirmed", "completed")

# How the charts split the chosen date range into bars (not a second date filter).
GRANULARITIES = OrderedDict([
    ("day", _l("Day")),
    ("week", _l("Week")),
    ("month", _l("Month")),
    ("quarter", _l("Quarter")),
    ("year", _l("Year")),
])
PRESETS = OrderedDict([
    ("today", _l("Today")),
    ("this_week", _l("This week")),
    ("last_7", _l("Last 7 days")),
    ("this_month", _l("This month")),
    ("last_month", _l("Last month")),
    ("last_6_months", _l("Last 6 months")),
    ("this_year", _l("This year")),
    ("last_year", _l("Last year")),
    ("custom", _l("Custom dates")),
])
DEFAULT_PRESET = "this_year"
MAX_BUCKETS = 120  # beyond this a finer granularity is unreadable; we step up automatically


# ---------------------------------------------------------------------------
# Period handling
# ---------------------------------------------------------------------------

def _month_start(d):
    return d.replace(day=1)


def _add_months(d, n):
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))


def _quarter_start(d):
    return d.replace(month=3 * ((d.month - 1) // 3) + 1, day=1)


def preset_range(preset, today):
    if preset == "today":
        return today, today
    if preset == "last_7":
        return today - datetime.timedelta(days=6), today
    if preset == "this_week":
        start = today - datetime.timedelta(days=today.weekday())
        return start, start + datetime.timedelta(days=6)
    if preset == "this_month":
        start = _month_start(today)
        return start, _add_months(start, 1) - datetime.timedelta(days=1)
    if preset == "last_month":
        end = _month_start(today) - datetime.timedelta(days=1)
        return _month_start(end), end
    if preset == "last_6_months":
        return _add_months(_month_start(today), -5), _add_months(_month_start(today), 1) - datetime.timedelta(days=1)
    if preset == "this_year":
        return datetime.date(today.year, 1, 1), datetime.date(today.year, 12, 31)
    if preset == "last_year":
        return datetime.date(today.year - 1, 1, 1), datetime.date(today.year - 1, 12, 31)
    return None, None


def _default_granularity(start, end):
    """Charts group automatically by the range: days for a week or two, weeks for a
    month or quarter, months for anything longer (years only past MAX_BUCKETS months)."""
    days = (end - start).days + 1
    if days <= 14:
        return "day"
    if days <= 92:
        return "week"
    if len(bucket_starts(start, end, "month")) <= MAX_BUCKETS:
        return "month"
    return "year"


def _parse_date(value):
    try:
        return datetime.date.fromisoformat((value or "").strip())
    except ValueError:
        return None


def resolve_period(params, today=None):
    """Read preset / from / to / group from a QueryDict into a full period spec."""
    today = today or timezone.localdate()
    preset = (params.get("preset") or "").strip()
    start, end = _parse_date(params.get("from")), _parse_date(params.get("to"))
    if preset != "custom" or not (start and end):
        if preset not in PRESETS or preset == "custom":
            preset = DEFAULT_PRESET
        start, end = preset_range(preset, today)
    if start > end:
        start, end = end, start

    granularity = _default_granularity(start, end)

    length = (end - start).days + 1
    prev_end = start - datetime.timedelta(days=1)

    prev_start = prev_end - datetime.timedelta(days=length - 1)
    filters = {}  # narrowing filters (staff / package / party) are not offered on the page
    return {
        "preset": preset,
        "start": start,
        "end": end,
        "granularity": granularity,
        "prev_start": prev_start,
        "prev_end": prev_end,
        "days": length,
        "filters": filters,
    }




def bucket_key(d, granularity):
    if granularity == "day":
        return d
    if granularity == "week":
        return d - datetime.timedelta(days=d.weekday())
    if granularity == "month":
        return _month_start(d)
    if granularity == "quarter":
        return _quarter_start(d)
    return datetime.date(d.year, 1, 1)


def _next_bucket(d, granularity):
    if granularity == "day":
        return d + datetime.timedelta(days=1)
    if granularity == "week":
        return d + datetime.timedelta(days=7)
    if granularity == "month":
        return _add_months(d, 1)
    if granularity == "quarter":
        return _add_months(d, 3)
    return datetime.date(d.year + 1, 1, 1)


def bucket_starts(start, end, granularity):
    out = []
    d = bucket_key(start, granularity)
    while d <= end:
        out.append(d)
        d = _next_bucket(d, granularity)
    return out


def bucket_label(d, granularity):
    if granularity == "day":
        return d.strftime("%d %b")
    if granularity == "week":
        return f"W{d.isocalendar()[1]} · {d.strftime('%d %b')}"
    if granularity == "month":
        return d.strftime("%b %Y")
    if granularity == "quarter":
        return f"Q{(d.month - 1) // 3 + 1} {d.year}"
    return str(d.year)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _booking_value(b):
    """Quoted/payable price when set, otherwise the worksheet total."""
    return b["total_price"] if b["total_price"] else b["total_amount"]


def _bookings(agency, start, end, f=None):
    f = f or {}
    qs = Booking.objects.filter(agency=agency, created_at__date__gte=start, created_at__date__lte=end)
    if f.get("staff"):
        qs = qs.filter(agent_id=f["staff"])
    if f.get("package"):
        qs = qs.filter(package_name=f["package"])
    if f.get("party"):
        qs = qs.filter(client_company=f["party"])
    return list(qs.values(
        "id", "created_at", "status", "total_price", "total_amount", "pax_adults", "pax_children",
        "pax_infants", "package_name", "voucher_number", "client_company",
        "agent__first_name", "agent__last_name", "agent__username",
    ))


def _ledger(agency, start, end, f=None):
    f = f or {}
    qs = LedgerEntry.objects.filter(agency=agency, transaction_date__gte=start, transaction_date__lte=end)
    if f.get("party"):
        qs = qs.filter(counterparty_name=f["party"])
    return list(qs.values(
        "transaction_date", "bucket", "direction", "transaction_type", "amount", "payment_method", "category",
        "counterparty_name",
    ))


def _is_cash_in(e):
    return e["direction"] == "credit" and e["transaction_type"] in CASH_IN_TYPES


def _is_cash_out(e):
    return e["direction"] == "debit" and e["transaction_type"] in CASH_OUT_TYPES


def _local_date(dt):
    return timezone.localtime(dt).date() if timezone.is_aware(dt) else dt.date()


def _is_sale(e):
    return e["bucket"] == "lein_dein" and e["transaction_type"] in SERVICE_TYPES and e["direction"] == "debit"


def _is_purchase(e):
    return e["bucket"] == "lein_dein" and e["transaction_type"] in SERVICE_TYPES and e["direction"] == "credit"


def kpis(agency, start, end, f=None):
    bookings = _bookings(agency, start, end, f)
    active = [b for b in bookings if b["status"] in ACTIVE_BOOKING_STATUSES]
    ledger = _ledger(agency, start, end, f)
    cash_in = sum((e["amount"] for e in ledger if _is_cash_in(e)), ZERO)
    cash_out = sum((e["amount"] for e in ledger if _is_cash_out(e)), ZERO)
    value = sum((_booking_value(b) for b in active), ZERO)
    sales = sum((e["amount"] for e in ledger if _is_sale(e)), ZERO)
    purchases = sum((e["amount"] for e in ledger if _is_purchase(e)), ZERO)
    return {
        "bookings": len(active),
        "booking_value": value,
        "avg_value": (value / len(active)).quantize(Decimal(1)) if active else ZERO,
        "sales": sales,
        "purchases": purchases,
        "margin": sales - purchases,
        "margin_pct": ((sales - purchases) * 100 / sales).quantize(Decimal(1)) if sales else ZERO,
        "pax": sum(b["pax_adults"] + b["pax_children"] + b["pax_infants"] for b in active),
        "cancelled": sum(1 for b in bookings if b["status"] == "cancelled"),
        "cash_in": cash_in,
        "cash_out": cash_out,
        "net_cash": cash_in - cash_out,
        "expenses": sum((e["amount"] for e in ledger if e["bucket"] == "company_expense"), ZERO),
    }


def _delta(current, previous):
    """{'pct': abs percent change, 'dir': up|down|flat}, or None when there is no base to compare."""
    if not previous:
        return None
    pct = float((Decimal(current) - Decimal(previous)) / abs(Decimal(previous)) * 100)
    return {"pct": abs(pct), "dir": "up" if pct > 0.5 else "down" if pct < -0.5 else "flat"}


def _money_short(v):
    v = float(v)
    if abs(v) >= 10_000_000:
        return f"Rs. {v / 10_000_000:.1f} crore"
    if abs(v) >= 100_000:
        return f"Rs. {v / 100_000:.1f} lakh"
    return f"Rs. {v:,.0f}"




def _top(items, n=8):
    """Sort (label, value) descending; fold the tail into 'Other' so charts never exceed n rows."""
    items = sorted(((k, v) for k, v in items if v), key=lambda kv: kv[1], reverse=True)
    if len(items) <= n:
        return items
    head, tail = items[: n - 1], items[n - 1:]
    return head + [("Other", sum((v for _k, v in tail), type(tail[0][1])(0)))]














