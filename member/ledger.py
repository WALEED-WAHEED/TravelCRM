"""
Ledger query helpers shared by the ledger page, CSV export and the printable
party statement (member/views.py).

Balance convention matches a travel-trade party statement: balance = debit -
credit. A positive balance means the party owes the agency (receivable, "Dr");
a negative balance means the agency owes the party (payable, "Cr").
"""
import calendar
import datetime
from decimal import Decimal

from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import Coalesce

from .models import Contact, LedgerEntry

ZERO = Decimal("0")

PRESETS = ("this_month", "last_month", "this_year", "all")


def _parse_date(value):
    try:
        return datetime.date.fromisoformat((value or "").strip())
    except ValueError:
        return None


def preset_range(preset, today=None):
    today = today or datetime.date.today()
    if preset == "this_month":
        return today.replace(day=1), today.replace(day=calendar.monthrange(today.year, today.month)[1])
    if preset == "last_month":
        end = today.replace(day=1) - datetime.timedelta(days=1)
        return end.replace(day=1), end
    if preset == "this_year":
        return datetime.date(today.year, 1, 1), datetime.date(today.year, 12, 31)
    return None, None


def read_filters(params):
    """Normalise ledger filters from a GET QueryDict.

    Accepts the legacy `month=YYYY-MM` param so old report links keep working.
    """
    preset = (params.get("preset") or "").strip()
    date_from = _parse_date(params.get("from"))
    date_to = _parse_date(params.get("to"))
    month = (params.get("month") or "").strip()
    if preset in PRESETS and preset != "all":
        date_from, date_to = preset_range(preset)
    elif month and not (date_from or date_to):
        try:
            year, mon = (int(x) for x in month.split("-", 1))
            date_from = datetime.date(year, mon, 1)
            date_to = datetime.date(year, mon, calendar.monthrange(year, mon)[1])
        except ValueError:
            pass
    if date_from and date_to and date_from > date_to:
        date_from, date_to = date_to, date_from
    return {
        "q": (params.get("q") or "").strip(),
        "party": (params.get("party") or "").strip(),
        "type": (params.get("type") or "").strip(),
        "bucket": (params.get("bucket") or "").strip(),
        "preset": preset if preset in PRESETS else "",
        "date_from": date_from,
        "date_to": date_to,
    }


def filtered_entries(agency, f):
    qs = LedgerEntry.objects.filter(agency=agency)
    if f["bucket"]:
        qs = qs.filter(bucket=f["bucket"])
    if f["party"]:
        qs = qs.filter(counterparty_name__iexact=f["party"])
    if f["type"]:
        qs = qs.filter(transaction_type=f["type"])
    if f["date_from"]:
        qs = qs.filter(transaction_date__gte=f["date_from"])
    if f["date_to"]:
        qs = qs.filter(transaction_date__lte=f["date_to"])
    if f["q"]:
        q = f["q"]
        qs = qs.filter(
            Q(description__icontains=q)
            | Q(counterparty_name__icontains=q)
            | Q(trans_no__icontains=q)
            | Q(inv_ref__icontains=q)
            | Q(reference_number__icontains=q)
            | Q(category__icontains=q)
        )
    return qs


def debit_credit_totals(qs):
    t = qs.aggregate(
        debit=Coalesce(Sum("amount", filter=Q(direction="debit")), ZERO),
        credit=Coalesce(Sum("amount", filter=Q(direction="credit")), ZERO),
    )
    return {"debit": t["debit"], "credit": t["credit"], "net": t["debit"] - t["credit"]}


def opening_balance(agency, party, before):
    """Party balance (debit - credit) carried in from before `before`."""
    if not before:
        return ZERO
    qs = LedgerEntry.objects.filter(
        agency=agency, bucket="lein_dein", counterparty_name__iexact=party, transaction_date__lt=before,
    )
    return debit_credit_totals(qs)["net"]


def with_running_balance(entries, opening):
    """Attach `.running` to each entry, oldest first. Returns a list."""
    running = opening
    rows = []
    for e in entries:
        running += e.amount if e.direction == "debit" else -e.amount
        e.running = running
        rows.append(e)
    return rows


def party_balances(agency, date_to=None):
    """One row per party: totals and closing balance (as of `date_to`)."""
    qs = LedgerEntry.objects.filter(agency=agency, bucket="lein_dein").exclude(counterparty_name="")
    if date_to:
        qs = qs.filter(transaction_date__lte=date_to)
    rows = (
        qs.values("counterparty_name")
        .annotate(
            debit=Coalesce(Sum("amount", filter=Q(direction="debit")), ZERO),
            credit=Coalesce(Sum("amount", filter=Q(direction="credit")), ZERO),
            entries=Count("id"),
            last_date=Max("transaction_date"),
        )
        .order_by("counterparty_name")
    )
    out = []
    for r in rows:
        balance = r["debit"] - r["credit"]
        out.append({
            "name": r["counterparty_name"],
            "debit": r["debit"],
            "credit": r["credit"],
            "balance": balance,
            "entries": r["entries"],
            "last_date": r["last_date"],
        })
    out.sort(key=lambda r: abs(r["balance"]), reverse=True)
    return out


def receivable_payable(balances):
    receivable = sum((r["balance"] for r in balances if r["balance"] > 0), ZERO)
    payable = sum((-r["balance"] for r in balances if r["balance"] < 0), ZERO)
    return receivable, payable


def party_names(agency):
    """Existing ledger parties plus active contacts, for the party picker."""
    names = set(
        LedgerEntry.objects.filter(agency=agency).exclude(counterparty_name="")
        .values_list("counterparty_name", flat=True).distinct()
    )
    names.update(Contact.objects.filter(agency=agency, is_active=True).values_list("name", flat=True))
    return sorted(names, key=str.lower)


def pax_totals(entries):
    """{'Hotel': 20, 'Visa / MOFA': 20} — PAX per service type, statement footer."""
    labels = dict(LedgerEntry.TRANSACTION_TYPES)
    totals = {}
    for e in entries:
        if e.pax and e.transaction_type in LedgerEntry.SERVICE_TYPES:
            label = str(labels[e.transaction_type])
            totals[label] = totals.get(label, 0) + e.pax
    return totals


def party_statement(agency, party, date_from, date_to):
    qs = LedgerEntry.objects.filter(agency=agency, bucket="lein_dein", counterparty_name__iexact=party)
    if date_from:
        qs = qs.filter(transaction_date__gte=date_from)
    if date_to:
        qs = qs.filter(transaction_date__lte=date_to)
    entries = list(qs.order_by("transaction_date", "created_at", "id"))
    opening = opening_balance(agency, party, date_from)
    rows = with_running_balance(entries, opening)
    debit = sum((e.debit for e in rows), ZERO)
    credit = sum((e.credit for e in rows), ZERO)
    return {
        "name": rows[0].counterparty_name if rows else party,
        "opening": opening,
        "rows": rows,
        "debit": debit,
        "credit": credit,
        "closing": opening + debit - credit,
        "pax": pax_totals(rows),
    }
