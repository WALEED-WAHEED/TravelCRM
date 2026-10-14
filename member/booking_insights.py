"""Voucher insights: what an agency can learn from its vouchers (and the Excel export of it).

Everything comes from what a voucher holds — voucher number and date, package (or custom trip),
travellers, hotels, room types and meals, flights, transport, staff and status. No prices.

All numbers are for the vouchers created in the chosen period (totals, trends, mix, packages, hotels, staff).

Period handling (presets, automatic day/week/month grouping, previous period).
"""
from collections import defaultdict

from django.db.models import Max, Min
from django.utils import timezone
from django.utils.translation import gettext as _

from member import analytics

from .models import Booking, BookingFlight, BookingHotel, BookingMutamer, BookingTransport

STATUS_ORDER = ("saved", "draft")


def parse_filters(params=None):
    """The page has no filters any more — only the date range. Kept so callers/tests stay simple."""
    return {"basis": "created", "status": "", "package": "", "city": "", "q": "", "staff": None}


def visible_vouchers(agency):
    """The vouchers the Vouchers page shows: not cancelled, not still in approval (pending / sent back), and not an
    agent's unfinished draft."""
    return (Booking.objects.filter(agency=agency).exclude(status__in=("cancelled", "pending", "rejected"))
            .exclude(status="draft", agent__role="agent"))


def _base(agency):
    return visible_vouchers(agency)


def _range_qs(agency, start, end):
    return (_base(agency).filter(created_at__date__gte=start, created_at__date__lte=end)
            .annotate(starts=Min("hotels__check_in"), ends=Max("hotels__check_out")))


def _pax(b):
    return b.pax_adults + b.pax_children + b.pax_infants


def _name(b):
    return (b.agent.get_full_name() or b.agent.username) if b.agent_id else "—"


def _buckets(values, edges):
    """Count values into [(label, lo, hi)] buckets (hi None = open ended)."""
    out = []
    for _label, lo, hi in edges:
        out.append(sum(1 for v in values if v >= lo and (hi is None or v <= hi)))
    return {"labels": [e[0] for e in edges], "values": out}


def _kpis(bookings, hotel_nights=0):
    total = len(bookings)
    saved = sum(1 for b in bookings if b.status_group == "saved")
    nights = [(b.ends - b.starts).days for b in bookings if b.starts and b.ends]
    lead = [(b.starts - timezone.localtime(b.created_at).date()).days for b in bookings if b.starts]
    pax = sum(_pax(b) for b in bookings)
    return {
        "vouchers": total, "saved": saved, "drafts": total - saved,
        "saved_rate": round(saved * 100 / total, 1) if total else None,
        "pax": pax, "adults": sum(b.pax_adults for b in bookings),
        "children": sum(b.pax_children for b in bookings), "infants": sum(b.pax_infants for b in bookings),
        "avg_group": round(pax / total, 1) if total else None,
        "avg_nights": round(sum(nights) / len(nights), 1) if nights else None,
        "avg_lead": round(sum(lead) / len(lead)) if lead else None,
        "hotel_nights": hotel_nights,
    }


def _ranked(rows, n=10):
    return rows[:n]


def build(agency, period, f=None):
    start, end, g = period["start"], period["end"], period["granularity"]
    bookings = list(_range_qs(agency, start, end).select_related("agent").order_by("-created_at"))
    prev = list(_range_qs(agency, period["prev_start"], period["prev_end"]))
    ids = [b.id for b in bookings]

    hotel_lines = list(BookingHotel.objects.filter(booking_id__in=ids)
                       .values("booking_id", "city", "hotel_name", "nights", "room_type", "meal_plan"))
    k = _kpis(bookings, sum(h["nights"] or 0 for h in hotel_lines))
    pk = _kpis(prev)
    deltas = {key: analytics._delta(k[key] or 0, pk[key] or 0) if k[key] is not None else None
              for key in ("vouchers", "pax", "avg_group")}

    # ---- over time --------------------------------------------------------------------
    starts = analytics.bucket_starts(start, end, g)
    labels = [analytics.bucket_label(d, g) for d in starts]
    index = {d: i for i, d in enumerate(starts)}
    n = len(starts)
    by_status = {s: [0] * n for s in STATUS_ORDER}
    pax_series = [0] * n
    for b in bookings:
        d = timezone.localtime(b.created_at).date()
        i = index.get(analytics.bucket_key(d, g))
        if i is None:
            continue
        by_status.setdefault(b.status_group, [0] * n)[i] += 1
        pax_series[i] += _pax(b)
    status_labels = {"saved": _("Saved"), "draft": _("Drafted")}

    cal = defaultdict(lambda: [0, 0])
    for b in bookings:
        if b.starts:
            key = b.starts.replace(day=1)
            cal[key][0] += 1
            cal[key][1] += _pax(b)
    cal_keys = sorted(cal)

    # ---- group profile --------------------------------------------------------------------
    sizes = _buckets([_pax(b) for b in bookings],
                     [("1–2", 1, 2), ("3–5", 3, 5), ("6–10", 6, 10), ("11–20", 11, 20), ("21+", 21, None)])
    trip_nights = _buckets([(b.ends - b.starts).days for b in bookings if b.starts and b.ends],
                           [("1–7", 1, 7), ("8–10", 8, 10), ("11–15", 11, 15), ("16–21", 16, 21), ("22+", 22, None)])
    lead = _buckets([(b.starts - timezone.localtime(b.created_at).date()).days for b in bookings if b.starts],
                    [(_("Under 1 week"), -9999, 6), (_("1–2 weeks"), 7, 13), (_("2–4 weeks"), 14, 29),
                     (_("1–2 months"), 30, 59), (_("2+ months"), 60, None)])
    gender = defaultdict(int)
    gl = {"male": _("Male"), "female": _("Female")}
    for m in BookingMutamer.objects.filter(booking_id__in=ids).values("gender"):
        gender[gl.get(m["gender"], _("Not set"))] += 1

    # ---- stay ----------------------------------------------------------------------------------
    city_nights, rooms, meals = defaultdict(int), defaultdict(int), defaultdict(int)
    hotels = defaultdict(lambda: {"vouchers": set(), "rooms": 0, "nights": 0, "city": ""})
    for h in hotel_lines:
        city_nights[(h["city"] or _("Other")).strip().title()] += h["nights"] or 0
        if h["room_type"]:
            rooms[h["room_type"].strip().title()] += 1
        if h["meal_plan"]:
            meals[h["meal_plan"].strip().upper()] += 1
        if h["hotel_name"]:
            e = hotels[h["hotel_name"].strip()]
            e["vouchers"].add(h["booking_id"])
            e["rooms"] += 1
            e["nights"] += h["nights"] or 0
            e["city"] = (h["city"] or "").strip().title()
    hotel_rows = sorted(({"hotel": name, "city": e["city"], "vouchers": len(e["vouchers"]), "rooms": e["rooms"],
                          "nights": e["nights"]} for name, e in hotels.items()),
                        key=lambda r: (-r["nights"], r["hotel"].lower()))

    # ---- travel ---------------------------------------------------------------------------------
    routes = defaultdict(int)
    for fl in BookingFlight.objects.filter(booking_id__in=ids).select_related("flight"):
        if fl.sector or fl.airline:
            routes[((fl.sector or "—").strip(), (fl.airline or "—").strip())] += 1
    route_rows = sorted(({"sector": s, "airline": a, "legs": c} for (s, a), c in routes.items()),
                        key=lambda r: (-r["legs"], r["sector"]))
    transports = defaultdict(int)
    for t in BookingTransport.objects.filter(booking_id__in=ids).values("transporter", "vehicle_type"):
        if t["transporter"] or t["vehicle_type"]:
            transports[((t["transporter"] or "—").strip(), (t["vehicle_type"] or "—").strip())] += 1
    transport_rows = sorted(({"transporter": a, "vehicle": v, "bookings": c} for (a, v), c in transports.items()),
                            key=lambda r: (-r["bookings"], r["transporter"]))

    # ---- packages and team ---------------------------------------------------------------------
    pk_rows, staff_rows = {}, {}
    for b in bookings:
        key = b.package_name.strip() if b.package_name else ""
        e = pk_rows.setdefault(key, {"vouchers": 0, "pax": 0, "saved": 0, "nights": []})
        e["vouchers"] += 1
        e["pax"] += _pax(b)
        e["saved"] += b.status_group == "saved"
        if b.starts and b.ends:
            e["nights"].append((b.ends - b.starts).days)
        s = staff_rows.setdefault(_name(b), {"vouchers": 0, "pax": 0, "saved": 0})
        s["vouchers"] += 1
        s["pax"] += _pax(b)
        s["saved"] += b.status_group == "saved"
    package_rows = sorted(({"package": key or _("Custom trip"), "custom": not key, "vouchers": e["vouchers"], "pax": e["pax"],
                            "avg_group": round(e["pax"] / e["vouchers"], 1), "saved": e["saved"], "drafts": e["vouchers"] - e["saved"],
                            "avg_nights": round(sum(e["nights"]) / len(e["nights"]), 1) if e["nights"] else None}
                           for key, e in pk_rows.items()), key=lambda r: (-r["vouchers"], r["package"]))
    team_rows = sorted(({"staff": name, "vouchers": s["vouchers"], "pax": s["pax"], "saved": s["saved"],
                         "drafts": s["vouchers"] - s["saved"], "rate": round(s["saved"] * 100 / s["vouchers"])}
                        for name, s in staff_rows.items()), key=lambda r: (-r["vouchers"], r["staff"]))

    return {
        "kpis": k, "deltas": deltas,
        "tables": {"packages": _ranked(package_rows), "team": _ranked(team_rows), "hotels": _ranked(hotel_rows),
                   "routes": _ranked(route_rows), "transport": _ranked(transport_rows)},
        "full": {"packages": package_rows, "team": team_rows, "hotels": hotel_rows, "routes": route_rows,
                 "transport": transport_rows},
        "charts": {
            "labels": labels,
            "status": {"keys": list(STATUS_ORDER), "labels": [str(status_labels[s]) for s in STATUS_ORDER],
                       "values": [by_status[s] for s in STATUS_ORDER]},
            "pax": pax_series,
            "calendar": {"labels": [d.strftime("%b %Y") for d in cal_keys],
                         "vouchers": [cal[d][0] for d in cal_keys], "pax": [cal[d][1] for d in cal_keys]},
            "pax_mix": {"labels": [_("Adults"), _("Children"), _("Infants")],
                        "values": [k["adults"], k["children"], k["infants"]]},
            "gender": _pairs(gender),
            "sizes": sizes, "trip_nights": trip_nights, "lead": lead,
            "cities": _pairs(city_nights), "rooms": _pairs(rooms), "meals": _pairs(meals),
        },
    }


def _pairs(counter, n=8):
    items = analytics._top(counter.items(), n)
    return {"labels": [str(k) for k, _v in items], "values": [float(v) for _k, v in items]}


def filter_options(agency):
    return {}


def build_xlsx(agency, period, f, data, rtl=False):
    """Excel workbook with exactly what the page shows, one sheet per section:
    Summary, Trends, Travellers, Stay, Travel, Packages, Team."""
    from io import BytesIO

    from openpyxl import Workbook

    from member.xlsx import BOLD, TITLE_FONT, _autosize, _header, _rows, _sheet

    k, c, t = data["kpis"], data["charts"], data["full"]
    wb = Workbook()
    wb.remove(wb.active)
    fmt = "%d %b %Y"

    def block(ws, row, title, headers, rows):
        """A titled mini table; returns the next free row."""
        ws.cell(row=row, column=1, value=title).font = BOLD
        _header(ws, row + 1, headers)
        end = _rows(ws, row + 2, rows) if rows else row + 1
        return max(end, row + 2) + 2

    def pairs(p):
        return list(zip(p["labels"], p["values"], strict=True))

    ws = _sheet(wb, _("Summary"), rtl)
    ws["A1"] = f"{agency.name} — {_('Voucher insights')}"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = f"{_('Period')}: {period['start']:{fmt}} – {period['end']:{fmt}} ({_('voucher date')})"
    ws["A3"] = f"{_('Compared with')}: {period['prev_start']:{fmt}} – {period['prev_end']:{fmt}}"
    _header(ws, 5, [_("Measure"), _("Value")])
    _rows(ws, 6, [
        [_("Vouchers"), k["vouchers"]], [_("Saved"), k["saved"]], [_("Drafted"), k["drafts"]],
        [_("Saved rate (%)"), k["saved_rate"]],
        [_("Travellers (PAX)"), k["pax"]], [_("Adults"), k["adults"]], [_("Children"), k["children"]],
        [_("Infants"), k["infants"]], [_("Average group"), k["avg_group"]],
        [_("Average trip length (nights)"), k["avg_nights"]],
        [_("Average days booked in advance"), k["avg_lead"]],
        [_("Hotel nights"), k["hotel_nights"]],
    ])
    _autosize(ws)
    ws.column_dimensions["A"].width = 34

    ws = _sheet(wb, _("Trends"), rtl)
    st = dict(zip(c["status"]["keys"], c["status"]["values"], strict=True))
    row = block(ws, 1, _("Vouchers by status"), [_("Period")] + c["status"]["labels"] + [_("Travellers (PAX)")],
                [[label] + [st[s][i] for s in c["status"]["keys"]] + [c["pax"][i]] for i, label in enumerate(c["labels"])])
    cal = c["calendar"]
    block(ws, row, _("Departures by month"), ["", _("Vouchers"), _("Travellers (PAX)")],
          [[cal["labels"][i], cal["vouchers"][i], cal["pax"][i]] for i in range(len(cal["labels"]))])
    _autosize(ws)

    ws = _sheet(wb, _("Travellers"), rtl)
    row = block(ws, 1, _("Adults, children and infants"), ["", _("Travellers (PAX)")], pairs(c["pax_mix"]))
    row = block(ws, row, _("Gender"), ["", _("Travellers (PAX)")], pairs(c["gender"]))
    row = block(ws, row, _("Group size"), ["", _("Vouchers")], pairs(c["sizes"]))
    row = block(ws, row, _("Trip length"), ["", _("Vouchers")], pairs(c["trip_nights"]))
    block(ws, row, _("How far ahead groups book"), ["", _("Vouchers")], pairs(c["lead"]))
    _autosize(ws)

    ws = _sheet(wb, _("Stay"), rtl)
    row = block(ws, 1, _("Nights by city"), ["", _("Nights")], pairs(c["cities"]))
    row = block(ws, row, _("Room types"), ["", _("Rooms")], pairs(c["rooms"]))
    row = block(ws, row, _("Meal plans"), ["", _("Rooms")], pairs(c["meals"]))
    block(ws, row, _("Hotels"), [_("Hotel"), _("City"), _("Vouchers"), _("Rooms"), _("Nights")],
          [[r["hotel"], r["city"], r["vouchers"], r["rooms"], r["nights"]] for r in t["hotels"]])
    _autosize(ws)

    ws = _sheet(wb, _("Travel"), rtl)
    row = block(ws, 1, _("Flights"), [_("Sector"), _("Airline"), _("Flights")],
                [[r["sector"], r["airline"], r["legs"]] for r in t["routes"]])
    block(ws, row, _("Transport"), [_("Transporter"), _("Vehicle type"), _("Bookings")],
          [[r["transporter"], r["vehicle"], r["bookings"]] for r in t["transport"]])
    _autosize(ws)

    ws = _sheet(wb, _("Packages"), rtl)
    _header(ws, 1, [_("Package"), _("Vouchers"), _("PAX"), _("Average group"), _("Average nights"), _("Saved"), _("Drafted")])
    _rows(ws, 2, [[r["package"], r["vouchers"], r["pax"], r["avg_group"], r["avg_nights"], r["saved"], r["drafts"]]
                  for r in t["packages"]])
    _autosize(ws)

    ws = _sheet(wb, _("Team"), rtl)
    _header(ws, 1, [_("Staff"), _("Vouchers"), _("PAX"), _("Saved"), _("Drafted"), _("Saved rate (%)")])
    _rows(ws, 2, [[r["staff"], r["vouchers"], r["pax"], r["saved"], r["drafts"], r["rate"]] for r in t["team"]])
    _autosize(ws)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
