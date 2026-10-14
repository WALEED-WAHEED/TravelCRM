"""Insights for the four inventory pages — Hotels, Flights, Transports and Packages.

Every page answers the same two questions: what was used / sold in the chosen period (from the vouchers made in it),
and what in the catalogue is not being used. A page is described declaratively — key numbers, then sections of chart
and table cards — so one template and one Excel export serve all four.

Period handling (presets, automatic grouping, previous-period comparison) is shared with Reports.
"""
import datetime
from collections import defaultdict

from django.utils import timezone
from django.utils.translation import gettext as _

from reports import analytics

from .booking_insights import visible_vouchers
from .models import BookingFlight, BookingHotel, BookingTransport, Flight, Hotel, Package, Transport

KINDS = ("hotels", "flights", "transports", "packages", "ledger", "attendance")
LIMIT = 10


# ---------------------------------------------------------------------------------------------------------------- helpers
def _num(n):
    return f"{int(round(n)):,}"


def _pct(part, whole):
    return round(part * 100 / whole) if whole else 0


def _ranked(counter, n=8):
    items = analytics._top(counter.items(), n)
    return [str(k) for k, _v in items], [float(v) for _k, v in items]


def kpi(label, value, sub="", cur=None, prev=None):
    """A key number; with `cur`/`prev` it also carries the change against the previous period."""
    d = analytics._delta(cur, prev) if cur is not None and prev is not None else None
    return {"label": str(label), "value": value, "sub": str(sub), "delta": d, "nodelta": cur is None}


def chart(cid, title, hint, kind, labels, series, wide=False, money=False):
    """kind: bar | hbar | donut | stacked.  series: [{label, values, slot}]"""
    return {"type": "chart", "id": cid, "title": str(title), "hint": str(hint), "kind": kind, "wide": wide, "money": money, "is_donut": kind == "donut",
            "labels": [str(x) for x in labels], "series": series}


def table(title, hint, headers, rows, num=(), wide=True, empty=""):
    """rows: lists of cells; a cell is a value, or {"t": text, "href": url, "bar": percent}."""
    out = []
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            d = c if isinstance(c, dict) else {"t": c}
            d = {"t": "—" if d.get("t") in (None, "") else d["t"], "href": d.get("href", ""), "bar": d.get("bar"), "num": i in num}
            cells.append(d)
        out.append(cells)
    return {"type": "table", "title": str(title), "hint": str(hint), "headers": [str(h) for h in headers], "rows": out,
            "num": list(num), "wide": wide, "empty": str(empty or _("Nothing to show for this period."))}


class Frame:
    """The vouchers of the period and the previous one, plus the period's buckets."""

    def __init__(self, agency, period):
        self.agency, self.period = agency, period
        start, end, g = period["start"], period["end"], period["granularity"]
        self.g = g
        base = visible_vouchers(agency)
        self.rows = list(base.filter(created_at__date__gte=start, created_at__date__lte=end).select_related("agent"))
        self.prev = list(base.filter(created_at__date__gte=period["prev_start"], created_at__date__lte=period["prev_end"]))
        self.ids = [b.id for b in self.rows]
        self.pax = {b.id: b.pax_adults + b.pax_children + b.pax_infants for b in self.rows}
        self.pax.update({b.id: b.pax_adults + b.pax_children + b.pax_infants for b in self.prev})
        self.starts = analytics.bucket_starts(start, end, g)
        self.labels = [analytics.bucket_label(d, g) for d in self.starts]
        self.index = {d: i for i, d in enumerate(self.starts)}
        self.when = {b.id: timezone.localtime(b.created_at).date() for b in self.rows}

    def slot(self, booking_id):
        return self.index.get(analytics.bucket_key(self.when[booking_id], self.g))

    def per_period(self, pairs):
        """[(booking_id, amount)] -> a value per bucket."""
        out = [0] * len(self.starts)
        for bid, amount in pairs:
            i = self.slot(bid)
            if i is not None:
                out[i] += amount
        return out


def _month_series(dates):
    counter = defaultdict(int)
    for d in dates:
        if d:
            counter[d.replace(day=1)] += 1
    keys = sorted(counter)
    return [k.strftime("%b %Y") for k in keys], [counter[k] for k in keys]


def _pair_chart(cid, title, hint, kind, counter, label, n=8, slot=1, wide=False, money=False):
    labels, values = _ranked(counter, n)
    return chart(cid, title, hint, kind, labels, [{"label": str(label), "values": values, "slot": slot}], wide, money)


# ------------------------------------------------------------------------------------------------------------------ hotels
def build_hotels(agency, period):
    f = Frame(agency, period)
    lines = list(BookingHotel.objects.filter(booking_id__in=f.ids).values(
        "booking_id", "hotel_id", "hotel_name", "city", "nights", "room_type", "meal_plan", "check_in"))
    prev_lines = list(BookingHotel.objects.filter(booking_id__in=[b.id for b in f.prev]).values("booking_id", "nights"))
    catalogue = list(Hotel.objects.filter(agency=agency))
    nights = sum(x["nights"] for x in lines)
    prev_nights = sum(x["nights"] for x in prev_lines)
    guest = sum(x["nights"] * f.pax.get(x["booking_id"], 0) for x in lines)
    used_names = {x["hotel_name"].strip().lower() for x in lines if x["hotel_name"]}
    listed = {h.name.strip().lower() for h in catalogue}
    cities = {h.city.strip().title() for h in catalogue if h.city}

    kpis = [
        kpi(_("Hotels"), len(catalogue), _("%(n)s cities") % {"n": len(cities)}),
        kpi(_("Stays booked"), len(lines), _("hotel stays on vouchers"), len(lines), len(prev_lines)),
        kpi(_("Nights booked"), nights, _("across all stays"), nights, prev_nights),
        kpi(_("Guest nights"), guest, _("nights × travellers")),
        kpi(_("Hotels used"), len(used_names & listed), _("of %(n)s in your list") % {"n": len(catalogue)}),
        kpi(_("Average stay"), _("%(n)s nights") % {"n": round(nights / len(lines), 1)} if lines else "—", _("per stay")),
    ]

    city_nights, rooms, meals = defaultdict(int), defaultdict(int), defaultdict(int)
    hotel_rows = {}
    for x in lines:
        city_nights[(x["city"] or _("Other")).strip().title()] += x["nights"]
        if x["room_type"]:
            rooms[x["room_type"].strip().title()] += 1
        if x["meal_plan"]:
            meals[x["meal_plan"].strip().upper()] += 1
        name = (x["hotel_name"] or "").strip()
        if name:
            e = hotel_rows.setdefault(name.lower(), {"name": name, "city": (x["city"] or "").strip().title(), "stays": 0, "nights": 0, "guest": 0})
            e["stays"] += 1
            e["nights"] += x["nights"]
            e["guest"] += x["nights"] * f.pax.get(x["booking_id"], 0)
    top = sorted(hotel_rows.values(), key=lambda e: (-e["nights"], e["name"].lower()))
    unused = sorted((h for h in catalogue if h.name.strip().lower() not in used_names), key=lambda h: h.name.lower())
    by_city = defaultdict(int)
    for h in catalogue:
        by_city[(h.city or _("Other")).strip().title()] += 1
    stars = defaultdict(int)
    for h in catalogue:
        stars[_("%(n)s ★") % {"n": h.rating} if h.rating else _("Not rated")] += 1

    sections = [
        {"title": _("Trends"), "cards": [
            chart("nights", _("Nights booked"), _("Hotel nights on the vouchers made each period."), "bar", f.labels,
                  [{"label": _("Nights"), "values": f.per_period((x["booking_id"], x["nights"]) for x in lines), "slot": 1}], wide=True),
            chart("checkins", _("Check-ins by month"), _("When these stays start."), "bar", *_month_series(x["check_in"] for x in lines)[:1],
                  [{"label": _("Stays"), "values": _month_series(x["check_in"] for x in lines)[1], "slot": 3}]),
        ]},
        {"title": _("Where guests stay"), "cards": [
            _pair_chart("city", _("Nights by city"), _("Makkah, Madinah and other stays."), "hbar", city_nights, _("Nights")),
            _pair_chart("rooms", _("Room types"), _("Stays by room type."), "hbar", rooms, _("Stays")),
            _pair_chart("meals", _("Meal plans"), _("RO, BB, HB and FB."), "hbar", meals, _("Stays")),
        ]},
        {"title": _("Hotels"), "cards": [
            table(_("Most booked hotels"), _("Nights and guest nights per hotel."),
                  [_("Hotel"), _("City"), _("Stays"), _("Nights"), _("Guest nights"), _("Share of nights")],
                  [[e["name"], e["city"], e["stays"], e["nights"], e["guest"], {"t": f"{_pct(e['nights'], nights)}%", "bar": _pct(e["nights"], nights)}]
                   for e in top[:LIMIT]], num=(2, 3, 4)),
            table(_("Not booked this period"), _("Hotels in your list that no voucher used."),
                  [_("Hotel"), _("City"), _("Stars"), _("Sale price / night")],
                  [[h.name, h.city, h.rating or "—", _num(h.sale_price)] for h in unused[:LIMIT]], num=(3,), wide=False,
                  empty=_("Every hotel was used.")),
            chart("cat_city", _("Hotels by city"), _("Your hotel list."), "donut", *_ranked(by_city)[:1],
                  [{"label": _("Hotels"), "values": _ranked(by_city)[1], "slot": 1}]),
        ]},
    ]
    return {"title": _("Hotel insights"), "kpis": kpis, "sections": sections, "full": {"hotels": top, "unused": unused}, "star_counts": dict(stars)}


# ----------------------------------------------------------------------------------------------------------------- flights
def build_flights(agency, period):
    f = Frame(agency, period)
    legs = list(BookingFlight.objects.filter(booking_id__in=f.ids).select_related("flight"))
    prev_legs = list(BookingFlight.objects.filter(booking_id__in=[b.id for b in f.prev]))
    catalogue = list(Flight.objects.filter(agency=agency))
    seats = sum(f.pax.get(x.booking_id, 0) for x in legs)
    prev_seats = sum(f.pax.get(x.booking_id, 0) for x in prev_legs)
    routes, airlines, classes = defaultdict(int), defaultdict(int), defaultdict(int)
    used = {}
    class_names = dict(Flight.FLIGHT_CLASS)
    for x in legs:
        sector = (x.sector or "—").strip()
        routes[sector] += 1
        if x.airline:
            airlines[x.airline.strip()] += 1
        classes[str(class_names.get(x.flight_class, x.flight_class))] += 1
        key = (x.airline.strip(), (x.flight_number or "").strip(), sector)
        e = used.setdefault(key, {"legs": 0, "seats": 0, "classes": defaultdict(int), "flight_id": x.flight_id})
        e["legs"] += 1
        e["seats"] += f.pax.get(x.booking_id, 0)
        e["classes"][str(class_names.get(x.flight_class, x.flight_class))] += 1
    used_ids = {e["flight_id"] for e in used.values() if e["flight_id"]}
    busiest = max(routes.items(), key=lambda kv: kv[1])[0] if routes else "—"

    kpis = [
        kpi(_("Flights"), len(catalogue), _("in your list")),
        kpi(_("Flight legs booked"), len(legs), _("departure and return"), len(legs), len(prev_legs)),
        kpi(_("Seats booked"), seats, _("travellers on every leg"), seats, prev_seats),
        kpi(_("Vouchers with flights"), len({x.booking_id for x in legs}), _("in this period")),
        kpi(_("Airlines"), len(airlines), _("used")),
        kpi(_("Busiest route"), busiest, _("most booked sector")),
    ]
    out_legs = f.per_period((x.booking_id, 1) for x in legs if x.flight_type == "outbound")
    back_legs = f.per_period((x.booking_id, 1) for x in legs if x.flight_type == "return")
    month_labels, month_values = _month_series(timezone.localtime(x.departure_at).date() if x.departure_at else None for x in legs)
    flight_rows = sorted(used.items(), key=lambda kv: (-kv[1]["legs"], kv[0]))
    unused = sorted((fl for fl in catalogue if fl.id not in used_ids), key=lambda fl: (fl.airline.lower(), fl.flight_number or ""))

    sections = [
        {"title": _("Trends"), "cards": [
            chart("legs", _("Flight legs"), _("Departure and return legs on the vouchers made each period."), "stacked", f.labels,
                  [{"label": _("Departure"), "values": out_legs, "slot": 1}, {"label": _("Arrival"), "values": back_legs, "slot": 3}], wide=True),
            chart("months", _("Flights by month"), _("When the booked flights depart."), "bar", month_labels,
                  [{"label": _("Flights"), "values": month_values, "slot": 3}]),
        ]},
        {"title": _("Mix"), "cards": [
            _pair_chart("routes", _("Routes"), _("Legs per sector."), "hbar", routes, _("Flights")),
            _pair_chart("airlines", _("Airlines"), _("Legs per airline."), "hbar", airlines, _("Flights")),
            chart("classes", _("Class"), _("Economy, business or first."), "donut", *_ranked(classes)[:1],
                  [{"label": _("Flights"), "values": _ranked(classes)[1], "slot": 1}]),
        ]},
        {"title": _("Flights"), "cards": [
            table(_("Flights used"), _("How often each flight was booked."),
                  [_("Flight"), _("Sector"), _("Flights"), _("Seats"), _("Class")],
                  [[f"{k[0]} {k[1]}".strip(), k[2], e["legs"], e["seats"], " · ".join(f"{c} {n}" for c, n in e["classes"].items())]
                   for k, e in flight_rows[:LIMIT]], num=(2, 3)),
            table(_("Not booked this period"), _("Flights in your list that no voucher used."),
                  [_("Flight"), _("Sector")],
                  [[f"{fl.airline} {fl.flight_number or ''}".strip(), fl.sector] for fl in unused[:LIMIT]], wide=False,
                  empty=_("Every flight was used.")),
        ]},
    ]
    return {"title": _("Flight insights"), "kpis": kpis, "sections": sections, "full": {"flights": flight_rows, "unused": unused}}


# -------------------------------------------------------------------------------------------------------------- transports
def build_transports(agency, period):
    f = Frame(agency, period)
    lines = list(BookingTransport.objects.filter(booking_id__in=f.ids).select_related("transport"))
    prev_lines = list(BookingTransport.objects.filter(booking_id__in=[b.id for b in f.prev]))
    catalogue = list(Transport.objects.filter(agency=agency))
    carried = sum(f.pax.get(x.booking_id, 0) for x in lines)
    prev_carried = sum(f.pax.get(x.booking_id, 0) for x in prev_lines)
    with_cap = [(f.pax.get(x.booking_id, 0), x.transport.capacity) for x in lines if x.transport_id and x.transport.capacity]
    load = _pct(sum(p for p, _c in with_cap), sum(c for _p, c in with_cap)) if with_cap else None
    types, companies, routes = defaultdict(int), defaultdict(int), defaultdict(int)
    used = {}
    for x in lines:
        if x.vehicle_type:
            types[x.vehicle_type.strip()] += 1
        if x.transporter:
            companies[x.transporter.strip()] += 1
        if x.description:
            routes[x.description.strip()] += 1
        key = ((x.transporter or "").strip(), (x.vehicle_type or "").strip())
        e = used.setdefault(key, {"n": 0, "pax": 0, "cap": 0, "carried": 0})
        e["n"] += 1
        e["pax"] += f.pax.get(x.booking_id, 0)
        if x.transport_id and x.transport.capacity:
            e["cap"] += x.transport.capacity
            e["carried"] += f.pax.get(x.booking_id, 0)
    used_ids = {x.transport_id for x in lines if x.transport_id}
    unused = sorted((t for t in catalogue if t.id not in used_ids and t.is_active), key=lambda t: t.name.lower())
    active = sum(1 for t in catalogue if t.is_active)
    cat_types = defaultdict(int)
    for t in catalogue:
        cat_types[t.get_transport_type_display()] += 1
    month_labels, month_values = _month_series(x.travel_date for x in lines)

    kpis = [
        kpi(_("Vehicles"), len(catalogue), _("%(n)s active") % {"n": active}),
        kpi(_("Transport bookings"), len(lines), _("legs on vouchers"), len(lines), len(prev_lines)),
        kpi(_("Travellers carried"), carried, _("across all bookings"), carried, prev_carried),
        kpi(_("Average load"), f"{load}%" if load is not None else "—", _("travellers vs vehicle capacity")),
        kpi(_("Vouchers with transport"), len({x.booking_id for x in lines}), _("in this period")),
        kpi(_("Companies"), len(companies), _("used")),
    ]
    rows = sorted(used.items(), key=lambda kv: (-kv[1]["n"], kv[0]))
    sections = [
        {"title": _("Trends"), "cards": [
            chart("bookings", _("Transport bookings"), _("Legs on the vouchers made each period."), "bar", f.labels,
                  [{"label": _("Bookings"), "values": f.per_period((x.booking_id, 1) for x in lines), "slot": 1}], wide=True),
            chart("months", _("Travel dates by month"), _("When the transport runs."), "bar", month_labels,
                  [{"label": _("Bookings"), "values": month_values, "slot": 3}]),
        ]},
        {"title": _("Mix"), "cards": [
            _pair_chart("types", _("Vehicle types"), _("Bookings per vehicle type."), "hbar", types, _("Bookings")),
            _pair_chart("companies", _("Transporters"), _("Bookings per company."), "hbar", companies, _("Bookings")),
            _pair_chart("routes", _("Routes"), _("The most booked journeys."), "hbar", routes, _("Bookings")),
        ]},
        {"title": _("Vehicles"), "cards": [
            table(_("Transport used"), _("Bookings, travellers and how full the vehicles were."),
                  [_("Transporter"), _("Vehicle type"), _("Bookings"), _("Travellers"), _("Average load")],
                  [[k[0], k[1], e["n"], e["pax"], {"t": f"{_pct(e['carried'], e['cap'])}%", "bar": min(_pct(e["carried"], e["cap"]), 100)} if e["cap"] else "—"]
                   for k, e in rows[:LIMIT]], num=(2, 3)),
            table(_("Not booked this period"), _("Active vehicles that no voucher used."),
                  [_("Vehicle"), _("Type"), _("Capacity")],
                  [[t.name, t.get_transport_type_display(), t.capacity] for t in unused[:LIMIT]], num=(2,), wide=False,
                  empty=_("Every vehicle was used.")),
            chart("cat_types", _("Vehicles by type"), _("Your vehicle list."), "donut", *_ranked(cat_types)[:1],
                  [{"label": _("Vehicles"), "values": _ranked(cat_types)[1], "slot": 1}]),
        ]},
    ]
    return {"title": _("Transport insights"), "kpis": kpis, "sections": sections, "full": {"used": rows, "unused": unused}}


# ------------------------------------------------------------------------------------------------------------------ packages
def build_packages(agency, period):
    f = Frame(agency, period)
    packages = list(Package.objects.filter(agency=agency))
    by_name = {p.name.strip().lower(): p for p in packages}

    def is_package(b):
        return bool(b.package_name) and b.package_name.strip().lower() in by_name

    mine = [b for b in f.rows if is_package(b)]
    prev_mine = [b for b in f.prev if is_package(b)]
    custom = len(f.rows) - len(mine)
    sold_pax = sum(f.pax[b.id] for b in mine)
    prev_sold = sum(f.pax[b.id] for b in prev_mine)
    today = timezone.localdate()
    upcoming = [p for p in packages if p.is_active and p.departure_date and today <= p.departure_date <= today + datetime.timedelta(days=60)]
    margins = [(p.starting_price - p.cost_price) * 100 / p.starting_price for p in packages if p.cost_price and p.starting_price]
    agent_n = sum(1 for b in mine if b.agent.role == "agent") if mine else 0

    # seat fill uses every voucher ever made for the package (seats belong to a departure, not to a period)
    all_sold = defaultdict(int)
    for b in visible_vouchers(agency).exclude(package_name=""):
        p = by_name.get(b.package_name.strip().lower())
        if p:
            all_sold[p.id] += b.pax_adults + b.pax_children + b.pax_infants

    perf = {}
    for b in mine:
        p = by_name[b.package_name.strip().lower()]
        e = perf.setdefault(p.id, {"p": p, "vouchers": 0, "pax": 0})
        e["vouchers"] += 1
        e["pax"] += f.pax[b.id]
    perf_rows = sorted(perf.values(), key=lambda e: (-e["vouchers"], e["p"].name.lower()))
    unsold = sorted((p for p in packages if p.is_active and p.id not in perf), key=lambda p: p.name.lower())
    seat_rows = sorted((p for p in packages if p.total_seats), key=lambda p: (p.departure_date is None, p.departure_date or today, p.name.lower()))
    types = defaultdict(int)
    for p in packages:
        types[p.get_package_type_display()] += 1
    spread = defaultdict(int)
    for p in packages:
        sp = p.starting_price
        if sp is None:
            continue
        spread[_("Under 200k") if sp < 200_000 else _("200k – 300k") if sp < 300_000 else _("300k – 400k") if sp < 400_000 else _("400k and above")] += 1
    order = [_("Under 200k"), _("200k – 300k"), _("300k – 400k"), _("400k and above")]
    pkg_per_period = f.per_period((b.id, 1) for b in mine)
    custom_per_period = f.per_period((b.id, 1) for b in f.rows if not is_package(b))

    kpis = [
        kpi(_("Packages"), len(packages), _("%(n)s active") % {"n": sum(1 for p in packages if p.is_active)}),
        kpi(_("Vouchers from packages"), len(mine), _("in this period"), len(mine), len(prev_mine)),
        kpi(_("Travellers sold"), sold_pax, _("on those vouchers"), sold_pax, prev_sold),
        kpi(_("Custom trips"), f"{_pct(custom, len(f.rows))}%" if f.rows else "—", _("%(n)s vouchers without a package") % {"n": custom}),
        kpi(_("Departing soon"), len(upcoming), _("packages leaving in 60 days")),
        kpi(_("Average margin"), f"{round(sum(margins) / len(margins))}%" if margins else "—", _("price vs your cost")),
    ]
    sections = [
        {"title": _("Sales"), "cards": [
            chart("sales", _("Packages and custom trips"), _("Vouchers made each period."), "stacked", f.labels,
                  [{"label": _("From a package"), "values": pkg_per_period, "slot": 1}, {"label": _("Custom trip"), "values": custom_per_period, "slot": 4}], wide=True),
            chart("channel", _("Sold by"), _("Package vouchers made by the team and by agents."), "donut",
                  [_("Team"), _("Agents")], [{"label": _("Vouchers"), "values": [len(mine) - agent_n, agent_n], "slot": 1}]),
            table(_("Package performance"), _("What sold in this period."),
                  [_("Package"), _("Code"), _("Type"), _("Vouchers"), _("Travellers"), _("Share")],
                  [[e["p"].name, e["p"].code, e["p"].get_package_type_display(), e["vouchers"], e["pax"],
                    {"t": f"{_pct(e['vouchers'], len(mine))}%", "bar": _pct(e["vouchers"], len(mine))}] for e in perf_rows[:LIMIT]], num=(3, 4)),
        ]},
        {"title": _("Seats and departures"), "cards": [
            table(_("Seat fill"), _("Seats sold so far against seats on offer (all vouchers, not only this period)."),
                  [_("Package"), _("Departure"), _("Days to go"), _("Seats"), _("Sold"), _("Left"), _("Filled")],
                  [[p.name, p.departure_date.strftime("%d %b %Y") if p.departure_date else "—",
                    (p.departure_date - today).days if p.departure_date and p.departure_date >= today else "—", p.total_seats,
                    all_sold.get(p.id, 0), max(p.total_seats - all_sold.get(p.id, 0), 0),
                    {"t": f"{min(_pct(all_sold.get(p.id, 0), p.total_seats), 100)}%", "bar": min(_pct(all_sold.get(p.id, 0), p.total_seats), 100)}]
                   for p in seat_rows[:LIMIT]], num=(2, 3, 4, 5), empty=_("No package has a seat count yet.")),
            table(_("Not sold this period"), _("Active packages with no voucher in this period."),
                  [_("Package"), _("Code"), _("Type"), _("From")],
                  [[p.name, p.code, p.get_package_type_display(), _num(p.starting_price) if p.starting_price is not None else "—"] for p in unsold[:LIMIT]],
                  num=(3,), wide=False, empty=_("Every package sold.")),
        ]},
        {"title": _("Your catalogue"), "cards": [
            chart("types", _("Packages by type"), _("Umrah, Hajj, Ziyarat and more."), "donut", *_ranked(types)[:1],
                  [{"label": _("Packages"), "values": _ranked(types)[1], "slot": 1}]),
            chart("price", _("Starting price"), _("How the package prices spread."), "bar", order,
                  [{"label": _("Packages"), "values": [spread.get(k, 0) for k in order], "slot": 3}]),
        ]},
    ]
    return {"title": _("Package insights"), "kpis": kpis, "sections": sections, "full": {"perf": perf_rows, "unsold": unsold, "seats": seat_rows}}


def build_ledger(agency, period):
    """Money in and out for the period, who owes whom today, and where the money goes."""
    from decimal import Decimal

    from .ledger import party_balances
    from .models import LedgerEntry

    start, end, g = period["start"], period["end"], period["granularity"]
    zero = Decimal("0")
    entries = list(LedgerEntry.objects.filter(agency=agency, transaction_date__gte=start, transaction_date__lte=end))
    prev = list(LedgerEntry.objects.filter(agency=agency, transaction_date__gte=period["prev_start"], transaction_date__lte=period["prev_end"]))
    starts = analytics.bucket_starts(start, end, g)
    labels = [analytics.bucket_label(d, g) for d in starts]
    index = {d: i for i, d in enumerate(starts)}

    def money_in(e):
        return e.direction == "credit" and e.transaction_type in analytics.CASH_IN_TYPES

    def money_out(e):
        return e.direction == "debit" and e.transaction_type in analytics.CASH_OUT_TYPES

    def total(rows, test):
        return sum((e.amount for e in rows if test(e)), zero)

    got, paid = total(entries, money_in), total(entries, money_out)
    prev_got, prev_paid = total(prev, money_in), total(prev, money_out)
    expenses = total(entries, lambda e: e.bucket == "company_expense" and e.direction == "debit")
    balances = party_balances(agency)
    owed_to_us = sum((b["balance"] for b in balances if b["balance"] > 0), zero)
    we_owe = sum((-b["balance"] for b in balances if b["balance"] < 0), zero)

    def fmt(v):
        return analytics._money_short(v)

    in_series, out_series = [0.0] * len(starts), [0.0] * len(starts)
    for e in entries:
        i = index.get(analytics.bucket_key(e.transaction_date, g))
        if i is None:
            continue
        if money_in(e):
            in_series[i] += float(e.amount)
        elif money_out(e):
            out_series[i] += float(e.amount)
    kinds, methods, categories = defaultdict(float), defaultdict(float), defaultdict(float)
    type_names = dict(LedgerEntry.TRANSACTION_TYPES)
    method_names = dict(LedgerEntry.PAYMENT_METHODS)
    for e in entries:
        kinds[str(type_names.get(e.transaction_type, e.transaction_type))] += float(e.amount)
        if money_in(e):
            methods[str(method_names.get(e.payment_method, _("Not recorded")))] += float(e.amount)
        if e.bucket == "company_expense" and e.direction == "debit":
            categories[(e.category or e.description or _("Other")).strip()[:40]] += float(e.amount)
    receivers = sorted((b for b in balances if b["balance"] > 0), key=lambda b: -b["balance"])
    payers = sorted((b for b in balances if b["balance"] < 0), key=lambda b: b["balance"])
    in_by_party = defaultdict(float)
    for e in entries:
        if money_in(e) and e.counterparty_name:
            in_by_party[e.counterparty_name] += float(e.amount)
    oldest = []
    for b in receivers:
        days = (timezone.localdate() - b["last_date"]).days if b["last_date"] else None
        oldest.append((b, days))

    kpis = [
        kpi(_("Received"), fmt(got), _("money in"), float(got), float(prev_got)),
        kpi(_("Paid out"), fmt(paid), _("money out"), float(paid), float(prev_paid)),
        kpi(_("Net cash"), fmt(got - paid), _("received minus paid")),
        kpi(_("Expenses"), fmt(expenses), _("company expenses")),
        kpi(_("Parties owe you"), fmt(owed_to_us), _("%(n)s parties") % {"n": len(receivers)}),
        kpi(_("You owe parties"), fmt(we_owe), _("%(n)s parties") % {"n": len(payers)}),
    ]
    sections = [
        {"title": _("Cash flow"), "cards": [
            chart("flow", _("Money in and out"), _("Received and paid each period."), "stacked", labels,
                  [{"label": _("Received"), "values": in_series, "slot": 3}, {"label": _("Paid out"), "values": out_series, "slot": 2}], wide=True, money=True),
            _pair_chart("kinds", _("By entry type"), _("Where the entries of this period are."), "hbar", kinds, _("Rs."), money=True),
            _pair_chart("methods", _("How money came in"), _("Received by payment method."), "donut", methods, _("Rs."), money=True),
        ]},
        {"title": _("Balances today"), "cards": [
            table(_("Parties who owe you"), _("Biggest balances first."),
                  [_("Party"), _("Balance"), _("Entries"), _("Last entry"), _("Days since")],
                  [[b["name"], _num(b["balance"]), b["entries"], b["last_date"].strftime("%d %b %Y") if b["last_date"] else "—", d if d is not None else "—"]
                   for b, d in oldest[:LIMIT]], num=(1, 2, 4), empty=_("Nobody owes you anything.")),
            table(_("Parties you owe"), _("Biggest balances first."),
                  [_("Party"), _("Balance"), _("Entries"), _("Last entry")],
                  [[b["name"], _num(-b["balance"]), b["entries"], b["last_date"].strftime("%d %b %Y") if b["last_date"] else "—"] for b in payers[:LIMIT]],
                  num=(1, 2), empty=_("You owe nobody anything.")),
        ]},
        {"title": _("Where the money goes"), "cards": [
            _pair_chart("expenses", _("Expenses"), _("Company expenses by category."), "hbar", categories, _("Rs."), money=True),
            _pair_chart("payers", _("Top payers"), _("Parties who paid you most in this period."), "hbar", in_by_party, _("Rs."), money=True),
        ]},
    ]
    return {"title": _("Ledger insights"), "kpis": kpis, "sections": sections, "full": {"receivers": receivers, "payers": payers}}


def build_attendance(agency, period):
    """Who comes in, how punctual they are, hours worked, and the correction requests."""
    from .models import AttendanceCorrection, AttendanceLog

    start, end, g = period["start"], period["end"], period["granularity"]
    logs = list(AttendanceLog.objects.filter(agency=agency, date__gte=start, date__lte=end).select_related("user"))
    prev = list(AttendanceLog.objects.filter(agency=agency, date__gte=period["prev_start"], date__lte=period["prev_end"]))
    corrections = list(AttendanceCorrection.objects.filter(agency=agency, created_at__date__gte=start, created_at__date__lte=end))
    starts = analytics.bucket_starts(start, end, g)
    labels = [analytics.bucket_label(d, g) for d in starts]
    index = {d: i for i, d in enumerate(starts)}
    states = ("present", "late", "absent", "leave")
    names = {"present": _("Present"), "late": _("Late"), "absent": _("Absent"), "leave": _("Leave")}

    def rate(rows):
        expected = sum(1 for x in rows if x.status in ("present", "late", "absent"))
        came = sum(1 for x in rows if x.status in ("present", "late"))
        return round(came * 100 / expected, 1) if expected else None

    def on_time(rows):
        came = sum(1 for x in rows if x.status in ("present", "late"))
        return round(sum(1 for x in rows if x.status == "present") * 100 / came, 1) if came else None

    hours = [float(x.work_hours) for x in logs if x.work_hours]
    series = {k: [0] * len(starts) for k in states}
    per = {}
    weekday = [[0, 0] for _d in range(7)]            # [came, expected]
    late_in = defaultdict(int)
    for x in logs:
        i = index.get(analytics.bucket_key(x.date, g))
        if i is not None and x.status in series:
            series[x.status][i] += 1
        p = per.setdefault(x.person_name, {"present": 0, "late": 0, "absent": 0, "leave": 0, "hours": 0.0})
        if x.status in p:
            p[x.status] += 1
        p["hours"] += float(x.work_hours or 0)
        if x.status in ("present", "late", "absent"):
            weekday[x.date.weekday()][1] += 1
            if x.status in ("present", "late"):
                weekday[x.date.weekday()][0] += 1
        if x.status == "late":
            late_in[x.person_name] += 1
    day_names = [_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun")]
    people = []
    for name, p in per.items():
        exp = p["present"] + p["late"] + p["absent"]
        people.append({"name": name, **p, "rate": round((p["present"] + p["late"]) * 100 / exp) if exp else None})
    people.sort(key=lambda r: (-(r["rate"] if r["rate"] is not None else -1), -(r["present"] + r["late"] + r["absent"] + r["leave"]), r["name"].lower()))
    source = defaultdict(int)
    source_names = dict(AttendanceLog.SOURCE_CHOICES)
    for x in logs:
        source[str(source_names.get(x.source, x.source))] += 1
    pend = sum(1 for c in corrections if c.status == "pending")
    ok = sum(1 for c in corrections if c.status == "approved")
    cur, old = rate(logs), rate(prev)

    kpis = [
        kpi(_("Attendance rate"), f"{cur}%" if cur is not None else "—", _("came in on expected days"), cur, old),
        kpi(_("On time"), f"{on_time(logs)}%" if on_time(logs) is not None else "—", _("of those who came")),
        kpi(_("Late arrivals"), sum(1 for x in logs if x.status == "late"), _("in this period"),
            sum(1 for x in logs if x.status == "late"), sum(1 for x in prev if x.status == "late")),
        kpi(_("Absences"), sum(1 for x in logs if x.status == "absent"), _("in this period"),
            sum(1 for x in logs if x.status == "absent"), sum(1 for x in prev if x.status == "absent")),
        kpi(_("Average hours"), f"{round(sum(hours) / len(hours), 1)} h" if hours else "—", _("worked per day")),
        kpi(_("Correction requests"), len(corrections), _("%(a)s approved · %(p)s pending") % {"a": ok, "p": pend}),
    ]
    sections = [
        {"title": _("Trends"), "cards": [
            chart("states", _("Attendance by day"), _("Present, late, absent and on leave each period."), "stacked", labels,
                  [{"label": str(names[k]), "values": series[k], "slot": slot} for k, slot in zip(states, (3, 4, 2, 1), strict=True)], wide=True),
            chart("weekday", _("Attendance by weekday"), _("Share of expected staff who came in."), "bar", day_names,
                  [{"label": _("Came in (%)"), "values": [round(c * 100 / e) if e else 0 for c, e in weekday], "slot": 1}]),
            _pair_chart("late", _("Most late arrivals"), _("Staff who were late most often."), "hbar", late_in, _("Late")),
        ]},
        {"title": _("People"), "cards": [
            table(_("Staff"), _("How each person did in this period."),
                  [_("Staff"), _("Present"), _("Late"), _("Absent"), _("Leave"), _("Hours"), _("Attendance")],
                  [[r["name"], r["present"], r["late"], r["absent"], r["leave"], round(r["hours"], 1),
                    {"t": f"{r['rate']}%", "bar": r["rate"]} if r["rate"] is not None else "—"] for r in people[:LIMIT]], num=(1, 2, 3, 4, 5)),
            chart("how", _("How check-ins were made"), _("Self check-in, manual entry, automatic and corrected."), "donut", *_ranked(source)[:1],
                  [{"label": _("Records"), "values": _ranked(source)[1], "slot": 1}]),
        ]},
    ]
    return {"title": _("Attendance insights"), "kpis": kpis, "sections": sections, "full": {"people": people}}


BUILDERS = {"hotels": build_hotels, "flights": build_flights, "transports": build_transports, "packages": build_packages,
            "ledger": build_ledger, "attendance": build_attendance}


def build(kind, agency, period):
    return BUILDERS[kind](agency, period)


def chart_payload(data):
    """Just the chart specs, keyed by id, for the page script."""
    return {c["id"]: c for s in data["sections"] for c in s["cards"] if c["type"] == "chart"}


def build_xlsx(agency, period, data, rtl=False):
    """One Summary sheet with the key numbers, then a sheet per section holding every table and chart the page shows."""
    from io import BytesIO

    from openpyxl import Workbook

    from reports.export import BOLD, TITLE_FONT, _autosize, _header, _rows, _sheet

    wb = Workbook()
    wb.remove(wb.active)
    fmt = "%d %b %Y"
    ws = _sheet(wb, _("Summary"), rtl)
    ws["A1"] = f"{agency.name} — {data['title']}"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = f"{_('Period')}: {period['start']:{fmt}} – {period['end']:{fmt}} ({_('voucher date')})"
    ws["A3"] = f"{_('Compared with')}: {period['prev_start']:{fmt}} – {period['prev_end']:{fmt}}"
    _header(ws, 5, [_("Measure"), _("Value"), _("Note")])
    _rows(ws, 6, [[k["label"], k["value"], k["sub"]] for k in data["kpis"]])
    _autosize(ws)
    ws.column_dimensions["A"].width = 30

    used = {"Summary"}
    for section in data["sections"]:
        name = "".join(ch for ch in section["title"] if ch not in "[]:*?/\\")[:31] or "Sheet"
        while name in used:
            name = name[:28] + "…"
        used.add(name)
        ws = _sheet(wb, name, rtl)
        row = 1
        for card in section["cards"]:
            ws.cell(row=row, column=1, value=card["title"]).font = BOLD
            if card["type"] == "table":
                headers = card["headers"]
                rows = [[c["t"] for c in r] for r in card["rows"]]
            else:
                headers = [""] + [s["label"] for s in card["series"]]
                rows = [[lab] + [s["values"][i] for s in card["series"]] for i, lab in enumerate(card["labels"])]
            _header(ws, row + 1, headers)
            end = _rows(ws, row + 2, rows) if rows else row + 1
            row = max(end, row + 2) + 2
        _autosize(ws)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
