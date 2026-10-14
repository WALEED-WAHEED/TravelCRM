"""Small inline-SVG chart data for the member dashboard.

Everything here returns plain dicts of pre-computed geometry so the template only
draws shapes — no chart library, no client-side maths.
"""
import datetime
from collections import defaultdict
from decimal import Decimal

from django.utils import formats, timezone

from reports import analytics

from .models import Booking, LedgerEntry

DAYS = 14
W, H = 140, 30  # SVG viewBox for the KPI sparklines


def _days(today):
    return [today - datetime.timedelta(days=i) for i in range(DAYS - 1, -1, -1)]


def _label(d):
    return formats.date_format(d, "D j M")


def _bars(values, days, height=H, gap=0.3):
    """Upward bars on a 0 baseline, one per day."""
    top = max([abs(v) for v in values] + [1])
    slot = W / len(values)
    bw = slot * (1 - gap)
    out = []
    for i, (v, d) in enumerate(zip(values, days, strict=True)):
        h = max(float(abs(v)) / float(top) * (height - 2), 1.2 if v else 0.6)
        out.append({"x": round(i * slot + (slot - bw) / 2, 2), "y": round(height - h, 2), "w": round(bw, 2),
                    "h": round(h, 2), "v": v, "day": _label(d), "today": i == len(values) - 1})
    return out


def _line(values, days):
    lo, hi = min(values), max(values)
    span = (hi - lo) or Decimal(1)
    step = W / (len(values) - 1)
    pts = [(round(i * step, 2), round(H - 3 - float((v - lo) / span) * (H - 6), 2)) for i, v in enumerate(values)]
    line = " ".join(f"{x},{y}" for x, y in pts)
    return {
        "line": line,
        "area": f"0,{H} {line} {W},{H}",
        "points": [{"hx": round(max(x - step / 2, 0), 2), "hw": round(step, 2), "v": v, "day": _label(d)}
                   for (x, _y), v, d in zip(pts, values, days, strict=True)],
        "slot": round(step, 2),
    }


def kpi_sparks(agency, today):
    days = _days(today)
    start = days[0]

    # Cash in (up) / out (down) per day
    cash_in, cash_out = defaultdict(Decimal), defaultdict(Decimal)
    for e in LedgerEntry.objects.filter(agency=agency, transaction_date__gte=start, transaction_date__lte=today).values(
            "transaction_date", "direction", "transaction_type", "amount"):
        if analytics._is_cash_in(e):
            cash_in[e["transaction_date"]] += e["amount"]
        elif analytics._is_cash_out(e):
            cash_out[e["transaction_date"]] += e["amount"]
    ins = [cash_in[d] for d in days]
    outs = [cash_out[d] for d in days]
    half = H / 2
    up = _bars(ins, days, height=half - 1)
    peak = max([float(v) for v in ins + outs] + [1])
    cash = []
    for i, d in enumerate(days):
        hi = float(ins[i]) / peak * (half - 2) if ins[i] else 0
        ho = float(outs[i]) / peak * (half - 2) if outs[i] else 0
        cash.append({"x": up[i]["x"], "w": up[i]["w"], "in_y": round(half - 1 - hi, 2), "in_h": round(hi, 2),
                     "out_h": round(ho, 2), "out_y": round(half + 1, 2), "in": ins[i], "out": outs[i],
                     "day": _label(d), "today": i == DAYS - 1})

    # New bookings per day (office-local creation date)
    per_day = defaultdict(int)
    since = timezone.make_aware(datetime.datetime.combine(start, datetime.time.min)) - datetime.timedelta(days=1)
    for dt in Booking.objects.filter(agency=agency, created_at__gte=since).values_list("created_at", flat=True):
        per_day[timezone.localtime(dt).date()] += 1
    bookings = _bars([per_day[d] for d in days], days)

    # Receivable / payable totals at the end of each day
    entries = (LedgerEntry.objects.filter(agency=agency, bucket="lein_dein", transaction_date__lte=today)
               .exclude(counterparty_name="").order_by("transaction_date")
               .values_list("transaction_date", "counterparty_name", "direction", "amount"))
    bal = defaultdict(Decimal)
    recv, pay = [], []
    it = iter(entries)
    pending = next(it, None)
    for d in days:
        while pending and pending[0] <= d:
            _date, party, direction, amount = pending
            bal[party] += amount if direction == "debit" else -amount
            pending = next(it, None)
        recv.append(sum((b for b in bal.values() if b > 0), Decimal(0)))
        pay.append(sum((-b for b in bal.values() if b < 0), Decimal(0)))

    return {"w": W, "h": H, "half": H / 2, "cash": cash, "bookings": bookings,
            "recv": _line(recv, days), "pay": _line(pay, days)}


def trips_strip(trips, today, days=8):
    """Travellers departing / returning per day for the next week."""
    cols = []
    for i in range(days):
        d = today + datetime.timedelta(days=i)
        out = sum(t["pax"] for t in trips if t["date"] == d and t["kind"] == "out")
        back = sum(t["pax"] for t in trips if t["date"] == d and t["kind"] == "back")
        cols.append({"date": d, "out": out, "back": back, "today": i == 0})
    peak = max([c["out"] + c["back"] for c in cols] + [1])
    for c in cols:
        c["out_pct"] = round(c["out"] / peak * 100, 1)
        c["back_pct"] = round(c["back"] / peak * 100, 1)
    return cols


def donut(segments):
    """segments: [(key, value, colour)] -> stroke-dasharray arcs on a 100-unit circle."""
    total = sum(v for _k, v, _c in segments) or 1
    arcs, offset = [], 25  # start at 12 o'clock
    for key, value, colour in segments:
        if not value:
            continue
        pct = value / total * 100
        arcs.append({"key": key, "dash": f"{max(pct - 1.2, 0.6):.2f} {100 - max(pct - 1.2, 0.6):.2f}",
                     "offset": f"{offset:.2f}", "colour": colour, "value": value})
        offset -= pct
    return arcs
