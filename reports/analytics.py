"""
Data behind the Reports page: one reporting period (with a granularity and a
previous period for comparison) applied to every metric on the page.

Reports answer "what happened over time"; the dashboard answers "what needs
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
from collections import OrderedDict, defaultdict
from decimal import Decimal

from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.utils.translation import ngettext

from member.ledger import party_balances
from member.models import AttendanceLog, Booking, LedgerEntry
from payments.models import Installment

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


def granularity_options(start, end):
    """Groupings that make a readable chart for this range: at least 2 bars, at most MAX_BUCKETS.
    Empty for a single day (nothing to split)."""
    return [g for g in GRANULARITIES if 2 <= len(bucket_starts(start, end, g)) <= MAX_BUCKETS]


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


def build_insights(report, labels):
    """Plain-language findings for the 'What stands out' box. Each: (tone, text).
    Only things the cards don't already say; needs-action first, then good news."""
    k, s, b = report["kpis"], report["series"], report["breakdowns"]
    out = []
    total = k["bookings"] + k["cancelled"]
    if total and k["cancelled"]:
        rate = k["cancelled"] * 100 / total
        out.append(("bad" if rate >= 15 else "neutral",
                    _("%(r).0f%% of bookings were cancelled (%(c)d of %(t)d).") % {"r": rate, "c": k["cancelled"], "t": total}))
    if any(s["cash_in"]):
        i = max(range(len(s["cash_in"])), key=lambda j: s["cash_in"][j])
        out.append(("good", _("Best period for money in: %(l)s with %(v)s received.") % {
            "l": labels[i], "v": _money_short(s["cash_in"][i])}))
    sales, purchases = sum(b["services"]["sales"]), sum(b["services"]["purchases"])
    if sales and purchases:
        margin = sales - purchases
        out.append(("good" if margin >= 0 else "bad",
                    _("Gross margin on services: %(m)s (%(p).0f%% of sales), from %(s)s sales and %(c)s supplier bills.") % {
                        "m": _money_short(margin), "p": margin * 100 / sales, "s": _money_short(sales), "c": _money_short(purchases)}))
    if k["net_cash"] < 0:
        out.append(("bad", _("More money went out than came in: net cash flow was %(v)s.") % {"v": _money_short(k["net_cash"])}))
    exp = b["expenses"]
    if exp["values"] and k["expenses"]:
        share = exp["values"][0] * 100 / float(k["expenses"])
        out.append(("neutral", _("Biggest expense: %(c)s, %(p).0f%% of company expenses (%(v)s).") % {
            "c": exp["labels"][0], "p": share, "v": _money_short(exp["values"][0])}))
    rec = b["receivables"]
    if rec["values"]:
        out.append(("bad" if rec["values"][0] >= 500_000 else "neutral",
                    _("%(n)s owes you the most: %(v)s.") % {"n": rec["labels"][0], "v": _money_short(rec["values"][0])}))
    att_k = report.get("attendance", {}).get("kpis", {})
    if att_k.get("rate") is not None and att_k["rate"] < 75:  # only when it needs attention
        out.append(("bad", _("Staff attendance was %(r).0f%% (%(l)d late arrivals, %(a)d absences).") % {
            "r": att_k["rate"], "l": att_k["late"], "a": att_k["absent"]}))
    if report["installments_overdue"]:
        n = report["installments_overdue"]
        out.append(("bad", ngettext("%(n)d installment is overdue — follow up with the client.",
                                    "%(n)d installments are overdue — follow up with these clients.", n) % {"n": n}))
    order = {"bad": 0, "good": 1, "neutral": 2}
    return sorted(out, key=lambda item: order.get(item[0], 3))


def _top(items, n=8):
    """Sort (label, value) descending; fold the tail into 'Other' so charts never exceed n rows."""
    items = sorted(((k, v) for k, v in items if v), key=lambda kv: kv[1], reverse=True)
    if len(items) <= n:
        return items
    head, tail = items[: n - 1], items[n - 1:]
    return head + [("Other", sum((v for _k, v in tail), type(tail[0][1])(0)))]


ATTENDANCE_STATUSES = ("present", "late", "absent", "leave")


def _attendance(agency, start, end, f=None):
    qs = AttendanceLog.objects.filter(agency=agency, date__gte=start, date__lte=end)
    if (f or {}).get("staff"):
        qs = qs.filter(user_id=f["staff"])
    return list(qs.values("date", "status", "person_name", "work_hours"))


def attendance_kpis(agency, start, end, f=None):
    logs = _attendance(agency, start, end, f)
    counts = {k: sum(1 for lg in logs if lg["status"] == k) for k in ATTENDANCE_STATUSES}
    expected = counts["present"] + counts["late"] + counts["absent"]  # leave days aren't expected days
    hours = [lg["work_hours"] for lg in logs if lg["work_hours"]]
    return {
        "rate": round((counts["present"] + counts["late"]) * 100 / expected, 1) if expected else None,
        "late": counts["late"],
        "absent": counts["absent"],
        "leave": counts["leave"],
        "avg_hours": round(float(sum(hours)) / len(hours), 1) if hours else None,
        "records": len(logs),
    }


def attendance_section(agency, period, starts, index):
    start, end, g = period["start"], period["end"], period["granularity"]
    n = len(starts)
    series = {k: [0] * n for k in ATTENDANCE_STATUSES}
    people = {}
    f = period.get("filters")
    for lg in _attendance(agency, start, end, f):
        i = index.get(bucket_key(lg["date"], g))
        if i is not None and lg["status"] in series:
            series[lg["status"]][i] += 1
        row = people.setdefault(lg["person_name"], {"name": lg["person_name"], "hours": 0.0,
                                                    **{k: 0 for k in ATTENDANCE_STATUSES}})
        if lg["status"] in ATTENDANCE_STATUSES:
            row[lg["status"]] += 1
        row["hours"] += float(lg["work_hours"] or 0)
    for row in people.values():
        expected = row["present"] + row["late"] + row["absent"]
        row["rate"] = round((row["present"] + row["late"]) * 100 / expected) if expected else None
        row["hours"] = round(row["hours"], 1)
    current = attendance_kpis(agency, start, end, f)
    previous = attendance_kpis(agency, period["prev_start"], period["prev_end"], f)
    return {
        "kpis": current,
        "deltas": {k: _delta(current[k] or 0, previous[k] or 0) if current[k] is not None else None
                   for k in ("rate", "late", "absent", "avg_hours")},
        "people": sorted(people.values(), key=lambda r: (r["rate"] is None, -(r["rate"] or 0), r["name"].lower())),
        "series": {"keys": list(ATTENDANCE_STATUSES), "values": [series[k] for k in ATTENDANCE_STATUSES]},
    }


def build_report(agency, period):
    start, end, g = period["start"], period["end"], period["granularity"]
    starts = bucket_starts(start, end, g)
    labels = [bucket_label(d, g) for d in starts]
    index = {d: i for i, d in enumerate(starts)}
    n = len(starts)

    f = period.get("filters") or {}
    bookings = _bookings(agency, start, end, f)
    ledger = _ledger(agency, start, end, f)

    # --- time series ---------------------------------------------------------
    statuses = [s for s, _label in Booking.STATUS_CHOICES]
    by_status = {s: [0] * n for s in statuses}
    value = [ZERO] * n
    pax = [0] * n
    for b in bookings:
        i = index.get(bucket_key(_local_date(b["created_at"]), g))
        if i is None:
            continue
        by_status.setdefault(b["status"], [0] * n)[i] += 1
        if b["status"] in ACTIVE_BOOKING_STATUSES:
            value[i] += _booking_value(b)
            pax[i] += b["pax_adults"] + b["pax_children"] + b["pax_infants"]

    cash_in, cash_out, expenses = [ZERO] * n, [ZERO] * n, [ZERO] * n
    for e in ledger:
        i = index.get(bucket_key(e["transaction_date"], g))
        if i is None:
            continue
        if _is_cash_in(e):
            cash_in[i] += e["amount"]
        if _is_cash_out(e):
            cash_out[i] += e["amount"]
        if e["bucket"] == "company_expense":
            expenses[i] += e["amount"]

    # --- breakdowns ----------------------------------------------------------
    service_labels = dict(LedgerEntry.TRANSACTION_TYPES)
    sales, purchases = defaultdict(lambda: ZERO), defaultdict(lambda: ZERO)
    by_category, by_method, by_payer = defaultdict(lambda: ZERO), defaultdict(lambda: ZERO), defaultdict(lambda: ZERO)
    method_labels = dict(LedgerEntry.PAYMENT_METHODS)
    for e in ledger:
        if e["bucket"] == "lein_dein" and e["transaction_type"] in SERVICE_TYPES:
            (sales if e["direction"] == "debit" else purchases)[e["transaction_type"]] += e["amount"]
        if e["bucket"] == "company_expense":
            by_category[(e["category"] or "Uncategorised").strip()] += e["amount"]
        if _is_cash_in(e):
            by_method[str(method_labels.get(e["payment_method"], "Not specified"))] += e["amount"]
            if e["counterparty_name"]:
                by_payer[e["counterparty_name"]] += e["amount"]

    services = [s for s in SERVICE_TYPES if sales[s] or purchases[s]]

    staff_value, staff_count, packages = defaultdict(lambda: ZERO), defaultdict(int), defaultdict(int)
    clients = defaultdict(lambda: ZERO)
    for b in bookings:
        if b["status"] not in ACTIVE_BOOKING_STATUSES:
            continue
        name = f"{b['agent__first_name']} {b['agent__last_name']}".strip() or b["agent__username"] or "—"
        staff_value[name] += _booking_value(b)
        staff_count[name] += 1
        if b["package_name"]:
            packages[b["package_name"].strip()] += 1
        if b["client_company"]:
            clients[b["client_company"].strip()] += _booking_value(b)

    balances = party_balances(agency, date_to=end)
    if f.get("party"):
        balances = [r for r in balances if r["name"] == f["party"]]
    receivables = _top([(r["name"], r["balance"]) for r in balances if r["balance"] > 0])
    payables = _top([(r["name"], -r["balance"]) for r in balances if r["balance"] < 0])
    staff = _top(staff_value.items())

    # --- KPIs with previous-period comparison --------------------------------
    current = kpis(agency, start, end, f)
    previous = kpis(agency, period["prev_start"], period["prev_end"], f)
    deltas = {k: _delta(current[k], previous[k]) for k in current}

    today = timezone.localdate()
    inst_qs = Installment.objects.filter(
        agency=agency, status__in=["pending", "overdue"], due_date__lte=today + datetime.timedelta(days=30),
    ).select_related("payment_plan__booking")
    if f.get("staff"):
        inst_qs = inst_qs.filter(payment_plan__booking__agent_id=f["staff"])
    if f.get("package"):
        inst_qs = inst_qs.filter(payment_plan__booking__package_name=f["package"])
    if f.get("party"):
        inst_qs = inst_qs.filter(payment_plan__booking__client_company=f["party"])
    installments = list(inst_qs.order_by("due_date")[:60])

    status_labels = dict(Booking.STATUS_CHOICES)
    booking_rows = [{
        "id": b["id"], "date": _local_date(b["created_at"]), "voucher": b["voucher_number"],
        "client": b["client_company"], "package": b["package_name"],
        "staff": f"{b['agent__first_name']} {b['agent__last_name']}".strip() or b["agent__username"],
        "pax": b["pax_adults"] + b["pax_children"] + b["pax_infants"], "status": b["status"],
        "status_label": str(status_labels.get(b["status"], b["status"])), "value": _booking_value(b),
    } for b in sorted(bookings, key=lambda b: b["created_at"], reverse=True)]

    f = float
    report = {
        "kpis": current,
        "previous": previous,
        "deltas": deltas,
        "receivable_total": sum((v for _k, v in receivables), ZERO),
        "payable_total": sum((v for _k, v in payables), ZERO),
        "installments": installments,
        "booking_rows": booking_rows,
        "party_rows": [dict(r, abs=abs(r["balance"])) for r in balances if r["balance"]],
        "installments_overdue": sum(1 for i in installments if i.due_date < today),
        "series": {
            "labels": labels,
            "cash_in": [f(v) for v in cash_in],
            "cash_out": [f(v) for v in cash_out],
            "net": [f(a - b) for a, b in zip(cash_in, cash_out, strict=True)],
            "expenses": [f(v) for v in expenses],
            "booking_value": [f(v) for v in value],
            "active_count": [sum(by_status.get(st, [0] * n)[i] for st in ACTIVE_BOOKING_STATUSES) for i in range(n)],
            "cancelled": by_status.get("cancelled", [0] * n),
            "pax": pax,
            "status": {
                "keys": statuses,
                "labels": [str(label) for _s, label in Booking.STATUS_CHOICES],
                "values": [by_status[s] for s in statuses],
            },
        },
        "breakdowns": {
            "services": {
                "labels": [str(service_labels[s]) for s in services],
                "sales": [f(sales[s]) for s in services],
                "purchases": [f(purchases[s]) for s in services],
            },
            "expenses": _pairs(_top(by_category.items())),
            "methods": _pairs(_top(by_method.items())),
            "receivables": _pairs(receivables),
            "payables": _pairs(payables),
            "staff": {
                "labels": [k for k, _v in staff],
                "values": [f(v) for _k, v in staff],
                "counts": [staff_count.get(k, 0) for k, _v in staff],
            },
            "packages": _pairs(_top(packages.items())),
            "clients": _pairs(_top(clients.items())),
            "payers": _pairs(_top(by_payer.items())),
        },
    }
    report["attendance"] = attendance_section(agency, period, starts, index)
    report["series"]["attendance"] = report["attendance"]["series"]
    report["insights"] = build_insights(report, labels)
    return report


def _pairs(items):
    return {"labels": [str(k) for k, _v in items], "values": [float(v) for _k, v in items]}


def timeseries_rows(report):
    """Rows for the CSV export: one per period bucket."""
    s = report["series"]
    status = dict(zip(s["status"]["keys"], s["status"]["values"], strict=True))
    for i, label in enumerate(s["labels"]):
        yield [
            label,
            status.get("confirmed", [0] * len(s["labels"]))[i] + status.get("completed", [0] * len(s["labels"]))[i],
            status.get("cancelled", [0] * len(s["labels"]))[i],
            s["booking_value"][i], s["pax"][i], s["cash_in"][i], s["cash_out"][i], s["net"][i], s["expenses"][i],
        ]
