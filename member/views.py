"""Member portal, Auth, and Public views."""
import calendar
import csv
import datetime
import json
import os
import re
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
from xhtml2pdf import pisa

from rbac.engine import has_capability
from system_config.models import AgencyBranding
from travelcrm.languages import ENABLED_LANGUAGES, NATIVE_NAMES
from utils.ratelimit import is_rate_limited

from . import attendance as att_rules
from . import dashboard_charts
from . import ledger as ledger_helpers
from .decorators import agent_required, member_required
from .instruction_views import active_instructions as active_voucher_instructions
from .models import (
    AttendanceLog,
    Booking,
    BookingContactInstruction,
    BookingFlight,
    BookingHotel,
    BookingMutamer,
    BookingNote,
    BookingTransport,
    ContactInstruction,
    Flight,
    Hotel,
    LedgerEntry,
    Package,
    Transport,
    Voucher,
    VoucherInstruction,
    VoucherSequence,
    VoucherService,
)

# ==========================================
# AUTH VIEWS
# ==========================================

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return _role_redirect(request.user)

    error = None
    if request.method == "POST":
        client_ip = request.META.get("REMOTE_ADDR", "unknown")
        if is_rate_limited(f"login:{client_ip}", limit=10, window_seconds=300):
            error = translation.gettext("Too many login attempts. Please wait a few minutes and try again.")
            return render(request, "login.html", {"error": error})

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            next_url = request.GET.get("next", "")
            # Only follow same-site paths — a raw ?next= is an open redirect.
            safe_next = next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
            )
            response = redirect(next_url) if safe_next else _role_redirect(user)
            if user.preferred_language:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user.preferred_language, max_age=settings.LANGUAGE_COOKIE_AGE)
            return response
        else:
            error = translation.gettext("Invalid username or password.")

    return render(request, "login.html", {"error": error})

@login_required(login_url="/login/")
@require_http_methods(["GET", "HEAD", "POST"])
def logout_view(request):
    logout(request)
    return redirect("/login/")

@require_http_methods(["GET", "POST"])
def forgot_password_view(request):
    sent = False
    error = None
    if request.method == "POST":
        client_ip = request.META.get("REMOTE_ADDR", "unknown")
        if is_rate_limited(f"forgot-password:{client_ip}", limit=5, window_seconds=600):
            error = translation.gettext("Too many requests. Please wait a few minutes and try again.")
            return render(request, "forgot_password.html", {"sent": sent, "error": error})

        email = request.POST.get("email", "").strip()
        if email:
            sent = True
        else:
            error = translation.gettext("Please enter a valid email address.")
    return render(request, "forgot_password.html", {"sent": sent, "error": error})

@login_required(login_url="/login/")
def root_redirect(request):
    return _role_redirect(request.user)

def _role_redirect(user):
    # Super Admin lands in the platform control panel, not a tenant dashboard.
    if user.is_superuser:
        return redirect("/platform-admin/")
    if user.is_staff:
        return redirect("/admin/")
    mapping = {
        "member": "/member/dashboard/",
        "agent": "/agent/dashboard/",
    }
    return redirect(mapping.get(user.role, "/member/dashboard/"))

# ==========================================
# MEMBER VIEWS
# ==========================================

@member_required
def dashboard(request):
    """Quick daily overview: this month's numbers, what needs attention today,
    shortcuts, and an AI box that hands off to the full assistant page.
    Money figures come from the shared analytics helpers."""
    from billing.usage import get_subscription
    from member import analytics

    agency = request.user.agency
    today = timezone.localdate()
    ctx = {"page_title": "Member Dashboard", "today": today}

    local_hour = timezone.localtime().hour
    ctx["greeting"] = translation.gettext(
        "Good morning" if local_hour < 12 else "Good afternoon" if local_hour < 18 else "Good evening")

    if not agency:
        return render(request, "member/dashboard.html", ctx)

    # --- Today vs yesterday ------------------------------------------------
    yesterday = today - datetime.timedelta(days=1)
    k = analytics.kpis(agency, today, today)
    kp = analytics.kpis(agency, yesterday, yesterday)
    bookings = Booking.objects.filter(agency=agency)
    todays_bookings = list(bookings.filter(created_at__date=today).order_by("-created_at"))
    k["new_bookings"] = len(todays_bookings)
    kp["new_bookings"] = bookings.filter(created_at__date=yesterday).count()
    k["net"] = k["cash_in"] - k["cash_out"]
    k["net_abs"] = abs(k["net"])
    ctx["k"] = k
    ctx["d"] = {key: analytics._delta(k[key], kp[key]) for key in k if key in kp}

    balances = ledger_helpers.party_balances(agency, date_to=today)
    ctx["receivable_total"] = sum((r["balance"] for r in balances if r["balance"] > 0), Decimal("0"))
    ctx["receivable_count"] = sum(1 for r in balances if r["balance"] > 0)
    # "You owe parties": Cr balances, same figure as the Ledger page.
    ctx["payable_total"] = sum((-r["balance"] for r in balances if r["balance"] < 0), Decimal("0"))
    ctx["payable_count"] = sum(1 for r in balances if r["balance"] < 0)

    att_s = att_rules.get_settings(agency)
    from zoneinfo import ZoneInfo
    try:
        office_zone = ZoneInfo(att_s.time_zone)
    except Exception:
        office_zone = None

    # --- Today's activity: ledger entries and new bookings in one feed --------
    entries = list(LedgerEntry.objects.filter(agency=agency, transaction_date=today).order_by("-created_at")[:25])
    activity = []
    for e in entries:
        row = {"direction": e.direction, "transaction_type": e.transaction_type}
        e.flow = "in" if analytics._is_cash_in(row) else "out" if analytics._is_cash_out(row) else ""
        activity.append({"kind": "entry", "at": e.created_at, "obj": e})
    activity += [{"kind": "booking", "at": b.created_at, "obj": b} for b in todays_bookings[:25]]
    activity.sort(key=lambda a: a["at"], reverse=True)
    for a in activity:
        a["time"] = timezone.localtime(a["at"], office_zone).strftime("%I:%M %p").lstrip("0")
    ctx["activity"] = activity[:25]
    ctx["activity_counts"] = {
        "entries": LedgerEntry.objects.filter(agency=agency, transaction_date=today).count(),
        "bookings": len(todays_bookings),
    }

    # --- Trips: departures / returns over the next 7 days, and who's away now
    from django.db.models import Max, Min
    week_end = today + datetime.timedelta(days=7)
    live = (bookings.filter(status__in=["confirmed", "completed"])
            .annotate(starts=Min("hotels__check_in"), ends=Max("hotels__check_out")))
    trips = []
    for b in live.filter(starts__gte=today, starts__lte=week_end):
        trips.append({"b": b, "date": b.starts, "kind": "out"})
    for b in live.filter(ends__gte=today, ends__lte=week_end):
        trips.append({"b": b, "date": b.ends, "kind": "back"})
    trips.sort(key=lambda t: (t["date"], t["kind"] != "out"))
    for t in trips:
        t["in_days"] = (t["date"] - today).days
        t["pax"] = t["b"].pax_adults + t["b"].pax_children + t["b"].pax_infants
    ctx["trips"] = trips[:25]
    ctx["trips_strip"] = dashboard_charts.trips_strip(trips, today)
    ctx["spark"] = dashboard_charts.kpi_sparks(agency, today)
    ctx["trips_more"] = max(len(trips) - 25, 0)
    away = list(live.filter(starts__lte=today, ends__gte=today))
    ctx["away"] = {"groups": len(away), "pax": sum(b.pax_adults + b.pax_children + b.pax_infants for b in away)}

    # --- Needs attention ---------------------------------------------------
    from payments.models import Installment
    pending_vouchers = Booking.objects.filter(agency=agency, status="pending").count()   # the Approvals queue
    open_inst = Installment.objects.filter(payment_plan__agency=agency, status__in=["pending", "overdue"])
    overdue_inst = open_inst.filter(due_date__lt=today).count()
    due_week = open_inst.filter(due_date__gte=today, due_date__lte=today + datetime.timedelta(days=7)).count()
    corrections = len(list(att_rules.pending_corrections(agency)))
    unconfirmed_soon = (bookings.filter(status="draft")
                        .annotate(starts=Min("hotels__check_in"))
                        .filter(starts__gte=today, starts__lte=week_end).count())
    subscription = get_subscription(agency)
    balances_url = reverse("member-ledger")
    attention = []
    if pending_vouchers:
        attention.append({"tone": "warning", "count": pending_vouchers, "href": reverse("member-approvals"),
                          "label": translation.ngettext("voucher waiting for approval", "vouchers waiting for approval", pending_vouchers)})
    if unconfirmed_soon:
        attention.append({"tone": "danger", "count": unconfirmed_soon, "href": reverse("member-bookings") + "?status=draft",
                          "label": translation.ngettext("draft booking departs within 7 days", "draft bookings depart within 7 days", unconfirmed_soon)})
    if overdue_inst:
        attention.append({"tone": "danger", "count": overdue_inst, "href": balances_url,
                          "label": translation.ngettext("installment overdue", "installments overdue", overdue_inst)})
    if due_week:
        attention.append({"tone": "info", "count": due_week, "href": balances_url,
                          "label": translation.ngettext("installment due this week", "installments due this week", due_week)})
    if corrections:
        attention.append({"tone": "warning", "count": corrections, "href": reverse("member-attendance"),
                          "label": translation.ngettext("attendance correction to review", "attendance corrections to review", corrections)})
    if subscription and subscription.status in ("trialing", "past_due"):
        attention.append({"tone": "danger" if subscription.status == "past_due" else "info", "href": reverse("member-billing"),
                          "count": subscription.days_left_in_trial if subscription.status == "trialing" else "!",
                          "label": translation.gettext("days left in your trial") if subscription.status == "trialing"
                          else translation.gettext("Your payment is overdue")})
    ctx["attention"] = attention
    ctx["pending_vouchers"] = pending_vouchers

    # --- Today's attendance ------------------------------------------------
    rows = att_rules.board(agency, att_s, today)
    counts = {key: sum(1 for r in rows if r["state"] == key) for key in ("present", "late", "absent", "not_in", "leave")}
    # The signed-in person's own check-in, for the greeting card.
    def _t(v):
        return v.strftime("%I:%M %p").lstrip("0") if v else ""
    my_log = att_rules.todays_log(agency, request.user, today)
    ctx["me_att"] = {
        "tracked": any(r["user"].id == request.user.id for r in rows) or bool(my_log),
        "log": my_log,
        "in": _t(my_log.check_in_time) if my_log else "",
        "out": _t(my_log.check_out_time) if my_log else "",
    }
    ctx["office_tz"] = att_s.time_zone
    # Greet by the office's clock (the server runs in UTC).
    office_hour = att_rules.office_now(att_s).hour
    ctx["greeting"] = translation.gettext(
        "Good morning" if office_hour < 12 else "Good afternoon" if office_hour < 18 else "Good evening")
    ctx["att"] = {"total": len(rows), "work_day": today.weekday() in (att_s.work_days or []), **counts, "in": counts["present"] + counts["late"],
                  "late_rows": [r for r in rows if r["state"] in ("late", "absent")]}
    ctx["att_donut"] = dashboard_charts.donut([
        ("present", counts["present"], "#1baf7a"), ("late", counts["late"], "#eda100"),
        ("absent", counts["absent"], "#d93a3a"), ("leave", counts["leave"], "#2a78d6"),
        ("not_in", counts["not_in"], "var(--border)")])

    # --- AI box: a fresh chat; "Continue in AI Assistant" reopens exactly this one
    from assistant.views import fresh_session
    session = fresh_session(agency, request.user)
    ctx["ai_session"] = session
    ctx["voice_provider"] = settings.VOICE_PROVIDER
    return render(request, "member/dashboard.html", ctx)


@member_required
def booking_insights(request):
    """Every booking statistic and chart, with its own filters and Excel / PDF download."""
    from member import analytics

    from . import booking_insights as bi

    agency = request.user.agency
    if not agency:
        return redirect("member-dashboard")
    period = analytics.resolve_period(request.GET)
    f = bi.parse_filters({})   # no filters on this page: only the date range
    data = bi.build(agency, period, f)
    if request.GET.get("export") == "xlsx":
        content = bi.build_xlsx(agency, period, f, data, rtl=translation.get_language_bidi())
        response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = (
            f'attachment; filename="voucher-insights-{period['start']:%Y%m%d}-{period['end']:%Y%m%d}.xlsx"')
        return response
    filters_active = False
    return render(request, "member/booking_insights.html", {
        "page_title": "Voucher insights",
        "period": period,
        "f": f,
        "data": data,
        "options": bi.filter_options(agency),
        "presets": analytics.PRESETS,
        "filters_active": filters_active,
    })


@member_required
def hotels(request):
    agency = request.user.agency
    base_qs = (
        Hotel.objects.filter(agency=agency).order_by("-created_at")
        if agency
        else Hotel.objects.none()
    )
    q = (request.GET.get("q") or "").strip()
    qs = base_qs
    if q:
        qs = base_qs.filter(
            Q(name__icontains=q)
            | Q(code__icontains=q)
            | Q(city__icontains=q)
            | Q(country__icontains=q)
        )

    hotel_stats = {
        "total": base_qs.count(),
        "cities": base_qs.exclude(city="").values("city").distinct().count(),
    }
    ctx = {
        "hotels": qs,
        "page_title": "Hotels",
        "hotel_stats": hotel_stats,
        "search_q": q,
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/hotels_htmx.html", ctx)
    return render(request, "member/hotels.html", ctx)


@member_required
def flights(request):
    agency = request.user.agency
    base_qs = (
        Flight.objects.filter(agency=agency).order_by("-created_at")
        if agency
        else Flight.objects.none()
    )
    q = (request.GET.get("q") or "").strip()
    qs = base_qs
    if q:
        qs = base_qs.filter(
            Q(airline__icontains=q)
            | Q(flight_number__icontains=q)
            | Q(departure_city__icontains=q)
            | Q(arrival_city__icontains=q)
            | Q(pnr_number__icontains=q)
        )
    flight_stats = {
        "total": base_qs.count(),
        "airlines": base_qs.exclude(airline="").values("airline").distinct().count(),
    }
    ctx = {
        "flights": qs,
        "page_title": "Flights",
        "flight_stats": flight_stats,
        "search_q": q,
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/flights_htmx.html", ctx)
    return render(request, "member/flights.html", ctx)


@member_required
def transports(request):
    agency = request.user.agency
    base_qs = (
        Transport.objects.filter(agency=agency).order_by("-created_at")
        if agency
        else Transport.objects.none()
    )
    q = (request.GET.get("q") or "").strip()
    qs = base_qs
    if q:
        qs = base_qs.filter(
            Q(name__icontains=q)
            | Q(transport_type__icontains=q)
            | Q(notes__icontains=q)
        )
    transport_stats = {
        "total": base_qs.count(),
        "active": base_qs.filter(is_active=True).count(),
    }
    ctx = {
        "transports": qs,
        "page_title": "Transports",
        "transport_stats": transport_stats,
        "search_q": q,
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/transports_htmx.html", ctx)
    return render(request, "member/transports.html", ctx)


@member_required
def package_detail(request, package_id):
    """Everything about one package, as the fragment the catalogue's View button opens."""
    package = get_object_or_404(
        Package.objects.select_related("makkah_hotel", "madina_hotel", "flight", "return_flight", "transport"),
        pk=package_id, agency=request.user.agency)
    return render(request, "member/partials/package_detail.html", {"p": package})


@member_required
def packages(request):
    agency = request.user.agency
    base_qs = Package.objects.filter(agency=agency) if agency else Package.objects.none()
    q = (request.GET.get("q") or "").strip()
    type_filter = (request.GET.get("type") or "").strip()
    qs = base_qs.select_related("makkah_hotel", "madina_hotel", "flight", "return_flight", "transport")
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(notes__icontains=q)
            | Q(makkah_hotel__name__icontains=q)
            | Q(madina_hotel__name__icontains=q)
        )
    if type_filter:
        qs = qs.filter(package_type=type_filter)
    package_stats = {
        "total": base_qs.count(),
        "active": base_qs.filter(is_active=True).count(),
    }
    ctx = {
        "packages": qs,
        "page_title": "Packages",
        "package_stats": package_stats,
        "search_q": q,
        "type_filter": type_filter,
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/packages_htmx.html", ctx)
    ctx.update({
        "type_choices": Package.PACKAGE_TYPES,
        "inclusion_choices": Package.INCLUSIONS,
        "hotels": Hotel.objects.filter(agency=agency).order_by("city", "name") if agency else [],
        "flights": Flight.objects.filter(agency=agency).order_by("airline") if agency else [],
        "transports": Transport.objects.filter(agency=agency, is_active=True).order_by("name") if agency else [],
    })
    return render(request, "member/packages.html", ctx)


def decorate_voucher_rows(qs):
    """Rows for a vouchers table: the family head, how many more travellers, the stay dates and nights, the cities."""
    rows = list(qs.prefetch_related("hotels", Prefetch("booking_mutamers", queryset=BookingMutamer.objects.order_by("id"))))
    for b in rows:
        hotels, travellers = list(b.hotels.all()), list(b.booking_mutamers.all())
        b.head = travellers[0] if travellers else None
        b.more_travellers = max(len(travellers) - 1, 0)
        b.stay_from = min((h.check_in for h in hotels), default=None)
        b.stay_to = max((h.check_out for h in hotels), default=None)
        b.stay_nights = sum(h.nights for h in hotels)
        b.cities = list(dict.fromkeys(h.city for h in hotels if h.city))  # e.g. Makkah, Madinah
    return rows


@member_required
def bookings(request):
    agency = request.user.agency
    # The Vouchers page: Draft and Saved vouchers (Saved = confirmed or completed).
    # Older cancelled records are not part of this flow and are left out of the list and the totals.
    base_qs = (
        Booking.objects.filter(agency=agency).exclude(status__in=("cancelled", "pending", "rejected"))
        .exclude(status="draft", agent__role="agent").order_by("-created_at")
        if agency
        else Booking.objects.none()
    )

    q = (request.GET.get("q") or "").strip()
    status_filter = (request.GET.get("status") or "").strip()
    source_filter = request.GET.get("source") if request.GET.get("source") in ("agent", "team") else ""
    qs = base_qs.select_related("agent")
    if source_filter == "agent":
        qs = qs.filter(agent__role="agent")                  # vouchers an agent submitted (and the team approved)
    elif source_filter == "team":
        qs = qs.exclude(agent__role="agent")
    if status_filter == "saved":
        qs = qs.filter(status__in=["confirmed", "completed"])
    elif status_filter in ("draft", "confirmed", "completed"):
        qs = qs.filter(status=status_filter)
    else:
        status_filter = ""
    if q:
        qs = qs.filter(
            Q(voucher_number__icontains=q)
            | Q(package_name__icontains=q)
            | Q(id__in=BookingMutamer.objects.filter(
                Q(name__icontains=q) | Q(passport_number__icontains=q)).values("booking_id"))
            | Q(agent__username__icontains=q) | Q(agent__first_name__icontains=q) | Q(agent__last_name__icontains=q)
        )
    rows = decorate_voucher_rows(qs)

    booking_stats = {
        "total": base_qs.count(),
        "draft": base_qs.filter(status="draft").count(),
        "saved": base_qs.filter(status__in=["confirmed", "completed"]).count(),
    }

    ctx = {
        "bookings": rows,
        "page_title": "Vouchers",
        "booking_stats": booking_stats,
        "search_q": q,
        "status_filter": status_filter,
        "source_filter": source_filter,
        "filters_active": bool(q or status_filter or source_filter),
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/bookings_htmx.html", ctx)
    return render(request, "member/bookings.html", ctx)


def worksheet_new_context(request):
    """Standalone "Create voucher" page — always a blank worksheet. Editing
    an existing booking happens on its own full-page editor
    (booking_detail.html) instead; this page only ever creates."""
    agency = request.user.agency
    branding = None
    if agency:
        branding, _ = AgencyBranding.objects.get_or_create(agency=agency)

    ctx = {
        "page_title": "Create voucher",
        "hotels_list": Hotel.objects.filter(agency=agency).order_by("name") if agency else Hotel.objects.none(),
        "flights_list": Flight.objects.filter(agency=agency).order_by("-created_at") if agency else Flight.objects.none(),
        "transports_list": Transport.objects.filter(agency=agency).order_by("name") if agency else Transport.objects.none(),
        "instructions_list": (
            ContactInstruction.objects.filter(agency=agency).order_by("city", "role")
            if agency
            else ContactInstruction.objects.none()
        ),
        "branding": branding,
        "booking": None,
        "booking_hotels": [],
        "booking_flights": [],
        "booking_transports": [],
        "booking_mutamers": [],
        "booking_instructions": [],
        "selected_instruction_ids": set(),
        "booking_status_choices": Booking.STATUS_CHOICES,
        "voucher_notes": [],
    }
    ctx.update(_voucher_form_extras(agency))
    return ctx


@member_required
def booking_worksheet_new(request):
    return render(request, "member/booking_new.html", worksheet_new_context(request))


ROOM_TYPES = ["Sharing", "Sharing (Gender)", "Single", "Double", "Triple", "Quad", "Quint"]


def _voucher_form_extras(agency):
    """Extra context for the voucher form (create page and full editor)."""
    return {
        "flight_classes": [(value, translation.gettext(label)) for value, label in Flight.FLIGHT_CLASS],
        "flight_legs": [
            ("outbound", translation.gettext("Departure")),
            ("return", translation.gettext("Arrival")),
        ],
        "voucher_instructions": active_voucher_instructions(agency) if agency else [],
        # Package picker: the Packages catalog; picking one pre-fills hotels, flight and transport.
        "packages_catalog": [
            {"name": p.name, "type": p.get_package_type_display(), "nights": p.total_nights,
             "price": str(p.starting_price) if p.starting_price is not None else "",
             "makkah_hotel": p.makkah_hotel_id, "madina_hotel": p.madina_hotel_id,
             "makkah_nights": p.makkah_nights or 0, "madina_nights": p.madina_nights or 0,
             "flight": p.flight_id, "return_flight": p.return_flight_id, "transport": p.transport_id,
             "departure": p.departure_date.isoformat() if p.departure_date else ""}
            for p in Package.objects.filter(agency=agency, is_active=True).order_by("name")
        ] if agency else [],
        # Room types offered on the voucher (value is what gets printed).
        "room_types": [(v, translation.gettext(v)) for v in ROOM_TYPES],
        "room_type_values": ROOM_TYPES,
        "meal_plans": [("RO", translation.gettext("Room only")), ("BB", translation.gettext("Bed & breakfast")),
                       ("HB", translation.gettext("Half board")), ("FB", translation.gettext("Full board"))],
        "meal_values": ["RO", "BB", "HB", "FB"],
        "hotels_url": reverse("member-hotels"),
        "packages_url": reverse("member-packages"),
        "flights_url": reverse("member-flights"),
        "transports_url": reverse("member-transports"),
        "contacts_url": reverse("member-contacts"),
    }


def _parse_booking_int(val, default=0):
    try:
        return max(0, int(val))
    except (TypeError, ValueError):
        return default


def _parse_json_list(raw, max_len=80):
    if not raw or not str(raw).strip():
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return data[:max_len]
    except json.JSONDecodeError:
        return []


def _parse_booking_date(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


APPROVAL_WINDOW_DAYS = 30
_PDF_RTL_FONT = "NotoNaskhArabic"
_PDF_RTL_RE = re.compile("[֐-ࣿיִ-﷿ﹰ-﻿]")


def _register_pdf_rtl_font():
    """The PDF engine only knows Latin fonts: register a bundled Urdu/Arabic one (once)."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from xhtml2pdf import default as pisa_default

    if _PDF_RTL_FONT in pdfmetrics.getRegisteredFontNames():
        pisa_default.DEFAULT_FONT[_PDF_RTL_FONT.lower()] = _PDF_RTL_FONT
        return True
    fonts = os.path.join(settings.BASE_DIR, "static", "fonts")
    try:
        pdfmetrics.registerFont(TTFont(_PDF_RTL_FONT, os.path.join(fonts, "NotoNaskhArabic-Regular.ttf")))
        pisa_default.DEFAULT_FONT[_PDF_RTL_FONT.lower()] = _PDF_RTL_FONT   # let the HTML/CSS use it by name
        return True
    except Exception:
        return False


def _pdf_rtl_lines(text, size=10.4, width=440):
    """Shape + reorder Urdu/Arabic text and wrap it ourselves: the PDF engine can't join letters or run right-to-left."""
    import arabic_reshaper
    from bidi.algorithm import get_display
    from reportlab.pdfbase.pdfmetrics import stringWidth

    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and stringWidth(arabic_reshaper.reshape(trial), _PDF_RTL_FONT, size) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return [get_display(arabic_reshaper.reshape(line)) for line in lines]


def _pdf_instructions(instructions):
    """Instructions ready for the PDF: right-to-left ones become pre-shaped lines."""
    rtl_ok = _register_pdf_rtl_font()
    rows = []
    for n, item in enumerate(instructions, 1):
        text = str(item.text or "").strip()
        if rtl_ok and _PDF_RTL_RE.search(text):
            lines = [ln for para in text.splitlines() if para.strip() for ln in _pdf_rtl_lines(para)]
            rows.append({"n": n, "rtl": True, "lines": lines})
        else:
            rows.append({"n": n, "rtl": False, "text": text})
    return rows


def _voucher_pdf_link_callback(uri, rel):
    from urllib.parse import urlparse

    if uri.startswith(("http://", "https://")) and urlparse(uri).path.startswith(settings.MEDIA_URL):
        uri = urlparse(uri).path
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(
            settings.MEDIA_ROOT,
            uri.replace(settings.MEDIA_URL, "", 1).lstrip("/"),
        )
        path = os.path.normpath(path)
        media_root = os.path.normpath(settings.MEDIA_ROOT)
        if path.startswith(media_root) and os.path.isfile(path):
            return path
    return uri


def _voucher_context(request, booking):
    branding = None
    if booking.agency_id:
        branding, _ = AgencyBranding.objects.get_or_create(agency=booking.agency)
    logo_url = ""
    if branding and branding.logo:
        logo_url = branding.logo.url   # relative: the browser resolves it, the PDF engine maps it to the file
    hotels = list(booking.hotels.select_related("hotel").order_by("check_in"))
    flights = list(booking.flights.select_related("flight").order_by("flight_type", "departure_at", "id"))
    mutamers = list(booking.booking_mutamers.order_by("id"))  # entry order: first row is the family head
    instructions = list(booking.booking_instructions.select_related("instruction").order_by(
        "instruction__city", "instruction__role"))
    teams = {}
    for bi in instructions:
        teams.setdefault(bi.instruction.city or "", []).append(bi.instruction)
    return {
        "booking": booking,
        "branding": branding,
        "logo_url": logo_url,
        "agency": booking.agency,
        "booking_hotels": hotels,
        "booking_flights": flights,
        "outbound_flights": [f for f in flights if f.flight_type == "outbound"],
        "return_flights": [f for f in flights if f.flight_type == "return"],
        "booking_transports": booking.transports.select_related("transport").order_by("travel_date", "id"),
        "booking_mutamers": mutamers,
        "family_head": mutamers[0] if mutamers else None,
        "total_nights": sum(h.nights for h in hotels),
        "pax_total": booking.pax_adults + booking.pax_children + booking.pax_infants,
        "booking_instructions": instructions,
        "teams": sorted(teams.items()),
        "voucher_instructions": active_voucher_instructions(booking.agency),
        "voucher_qr": _voucher_qr(booking, mutamers, hotels),
    }


def _voucher_qr(booking, mutamers, hotels):
    """PNG data-URI QR with the voucher's key facts, for hotel / transport staff to scan."""
    import base64

    import qrcode

    lines = [f"Voucher {booking.voucher_number}"]
    if mutamers:
        lines.append(f"Head {mutamers[0].name} {mutamers[0].passport_number}".strip())
    lines.append(f"PAX {booking.pax_adults + booking.pax_children + booking.pax_infants}")
    for h in hotels:
        lines.append(f"{h.city}: {h.hotel_name} {h.check_in:%d-%m-%y}/{h.check_out:%d-%m-%y}")
    buf = BytesIO()
    qrcode.make(chr(10).join(lines), box_size=4, border=1).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def worksheet_detail_context(request, booking):
    agency = booking.agency
    ctx = _voucher_context(request, booking)
    ctx.update(
        {
            "page_title": f"Voucher · {booking.voucher_number}",
            "hotels_list": Hotel.objects.filter(agency=agency).order_by("name"),
            "flights_list": Flight.objects.filter(agency=agency).order_by("-created_at"),
            "transports_list": Transport.objects.filter(agency=agency).order_by("name"),
            "instructions_list": ContactInstruction.objects.filter(agency=agency).order_by(
                "city", "role"
            ),
            "selected_instruction_ids": set(
                booking.booking_instructions.values_list("instruction_id", flat=True)
            ),
            "booking_status_choices": Booking.STATUS_CHOICES,
        }
    )
    ctx.update(_voucher_form_extras(agency))
    from .note_views import notes_for
    ctx["voucher_notes"] = notes_for(booking, request.user)
    return ctx


@member_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, agency=request.user.agency)
    return render(request, "member/booking_detail.html", worksheet_detail_context(request, booking))


@member_required
@require_POST
def booking_delete(request, booking_id):
    """Delete a voucher (after the confirmation pop-up). Vouchers with money recorded against them are kept."""
    booking = get_object_or_404(Booking, pk=booking_id, agency=request.user.agency)
    number = booking.voucher_number
    if booking.payments.exists() or booking.ledger_entries.exists():
        messages.error(request, translation.gettext(
            "Voucher %(n)s has payments recorded, so it can't be deleted.") % {"n": number})
        return redirect("member-bookings")
    with transaction.atomic():
        generated = getattr(booking, "generated_voucher", None)
        if generated:
            generated.delete()
        booking.delete()
    messages.success(request, translation.gettext("Voucher %(n)s deleted.") % {"n": number})
    return redirect("member-bookings")


def _parse_worksheet_instruction_ids(request):
    instruction_ids = []
    for x in request.POST.getlist("instruction_ids"):
        try:
            instruction_ids.append(int(x))
        except ValueError:
            continue
    return instruction_ids


def _replace_booking_line_items(
    agency,
    booking,
    hotels_payload,
    flights_payload,
    transports_payload,
    mutamers_payload,
    instruction_ids,
):
    # Only wipe-and-recreate rows still tied to a live catalog entry — a
    # row whose hotel/flight/transport was deleted from the catalog
    # (hotel/flight/transport now NULL, see the SET_NULL comments on
    # these FKs above) has no way to be represented in this payload at
    # all (the client only ever submits picks from the live catalog), so
    # leaving it out of the payload must not be read as "the user removed
    # this line item" — it would otherwise be silently dropped on the
    # very next save of an already-confirmed/completed booking.
    booking.hotels.filter(hotel__isnull=False).delete()
    for row in hotels_payload:
        if not isinstance(row, dict):
            continue
        try:
            hid = int(row.get("hotel_id"))
        except (TypeError, ValueError):
            continue
        hotel = Hotel.objects.filter(pk=hid, agency=agency).first()
        if not hotel:
            continue
        ci = _parse_booking_date(row.get("check_in"))
        co = _parse_booking_date(row.get("check_out"))
        if not ci or not co or co < ci:
            continue
        nights = (co - ci).days
        if nights < 1:
            nights = 1
        BookingHotel.objects.create(
            booking=booking,
            hotel=hotel,
            city=hotel.city,
            hotel_name=hotel.name,
            view=str(row.get("view") or "Standard")[:100],
            meal_plan=str(row.get("meal_plan") or "RO")[:10],
            confirmation_number=str(row.get("confirmation_number") or "")[:100],
            room_type=str(row.get("room_type") or "sharing")[:50],
            check_in=ci,
            check_out=co,
            nights=nights,
        )

    booking.flights.filter(flight__isnull=False).delete()
    for row in flights_payload:
        if not isinstance(row, dict):
            continue
        try:
            fid = int(row.get("flight_id"))
        except (TypeError, ValueError):
            continue
        flight = Flight.objects.filter(pk=fid, agency=agency).first()
        if not flight:
            continue
        ft = str(row.get("flight_type") or "outbound").strip()
        if ft not in ("outbound", "return"):
            ft = "outbound"
        fclass = str(row.get("flight_class") or "").strip()
        if fclass not in dict(Flight.FLIGHT_CLASS):
            fclass = "economy"
        BookingFlight.objects.create(
            booking=booking,
            flight=flight,
            flight_type=ft,
            airline=flight.airline,
            flight_number=flight.flight_number or "",
            departure_city=flight.departure_city,
            arrival_city=flight.arrival_city,
            flight_class=fclass,
            pnr_number=flight.pnr_number or "",
            departure_at=_parse_local_datetime(row.get("departure_at")),
            arrival_at=_parse_local_datetime(row.get("arrival_at")),
        )

    booking.transports.filter(transport__isnull=False).delete()
    for row in transports_payload:
        if not isinstance(row, dict):
            continue
        try:
            tid = int(row.get("transport_id"))
        except (TypeError, ValueError):
            continue
        transport = Transport.objects.filter(pk=tid, agency=agency).first()
        if not transport:
            continue
        td = _parse_booking_date(row.get("travel_date"))
        if not td:
            continue
        transporter = str(row.get("transporter") or transport.name or "")[:200]
        vehicle_type = str(row.get("vehicle_type") or transport.get_transport_type_display())[
            :100
        ]
        description = str(row.get("description") or "")[:300]
        BookingTransport.objects.create(
            booking=booking,
            transport=transport,
            travel_date=td,
            transporter=transporter,
            vehicle_type=vehicle_type,
            description=description,
        )

    # Travelers are entered directly on the booking (no catalog to preserve
    # a reference to), so a plain wipe-and-recreate on every save is
    # correct here — unlike hotels/flights/transports above, there's no
    # orphaned-but-still-valid row that this payload could accidentally
    # drop.
    booking.booking_mutamers.all().delete()
    for row in mutamers_payload:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        BookingMutamer.objects.create(
            booking=booking,
            name=name[:200],
            passport_number=str(row.get("passport_number") or "")[:50],
            visa_number=str(row.get("visa_number") or "")[:50],
            nationality=str(row.get("nationality") or "")[:100],
            gender=str(row.get("gender") or "")[:10],
            phone=str(row.get("phone") or "")[:20],
            email=str(row.get("email") or "")[:254],
            family_label=str(row.get("family_label") or "")[:100],
            pax_type=row.get("pax_type") if row.get("pax_type") in ("adult", "child", "infant") else "adult",
            bed=row.get("bed") not in (False, "no", "0", 0),
            mofa_number=str(row.get("mofa_number") or "")[:50],
            group_number=str(row.get("group_number") or "")[:50],
            pnr=str(row.get("pnr") or "")[:50],
        )

    booking.booking_instructions.all().delete()
    for iid in instruction_ids:
        inst = ContactInstruction.objects.filter(pk=iid, agency=agency).first()
        if inst:
            BookingContactInstruction.objects.create(booking=booking, instruction=inst)


def _parse_local_datetime(value):
    """'2026-10-25T16:20' from a datetime-local input -> aware datetime in the current timezone."""
    value = str(value or "").strip()
    if not value:
        return None
    try:
        dt = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def _sync_completed_booking_voucher(request, booking):
    """Keep a Voucher in lockstep with a Booking's completion state.
    Completing a booking (as a member) should surface the same way an
    agent's approved submission does — on the Vouchers page, no approval
    gate needed since a member did this directly. Reverting a booking's
    status away from completed removes its generated voucher again."""
    existing = getattr(booking, "generated_voucher", None)
    if booking.status != "completed":
        if existing:
            existing.delete()
        return

    travelers = list(booking.booking_mutamers.all())
    if len(travelers) == 1:
        t = travelers[0]
        name, passport, visa, nat, gender, phone, email = (
            t.name, t.passport_number, t.visa_number, t.nationality,
            t.gender, t.phone, t.email,
        )
    elif travelers:
        name = f"{travelers[0].name} +{len(travelers) - 1} more"
        passport = visa = nat = gender = phone = email = ""
    else:
        name = booking.client_company or booking.package_name or booking.voucher_number
        passport = visa = nat = gender = phone = email = ""

    paid = sum((p.amount for p in booking.payments.all()), Decimal("0"))
    included = ", ".join(filter(None, [
        ", ".join(h.hotel_name for h in booking.hotels.all()),
        ", ".join(f.airline for f in booking.flights.all()),
        ", ".join(t.transporter for t in booking.transports.all()),
    ])) or booking.package_name or "Package"

    if existing:
        voucher = existing
    else:
        voucher = Voucher(
            booking=booking, agent=booking.agent, agency=booking.agency,
            voucher_number=booking.voucher_number, status="approved",
            approved_by=request.user, approved_at=timezone.now(),
        )
    voucher.mutamer_name = name[:200]
    voucher.mutamer_passport_number = passport[:50]
    voucher.mutamer_visa_number = visa[:50]
    voucher.mutamer_nationality = nat[:100]
    voucher.mutamer_gender = gender[:10]
    voucher.mutamer_phone = phone[:20]
    voucher.mutamer_email = email
    voucher.total_amount = booking.total_price
    voucher.paid_amount = paid
    voucher.notes = booking.notes
    voucher.save()
    voucher.services.all().delete()
    VoucherService.objects.create(
        voucher=voucher, service_type="package",
        service_name=booking.package_name or "Trip package",
        description=included[:500], amount=booking.total_price, quantity=1,
    )


@member_required
@require_POST
def booking_worksheet_save(request):
    return worksheet_save(request, "member")


def _voucher_content(booking):
    """A short readable summary of what a voucher holds, to log what an edit changed."""
    def lst(items):
        return ", ".join(items) or "—"
    return {
        translation.gettext("Travellers"): lst([m.name for m in booking.booking_mutamers.order_by("id")]),
        translation.gettext("Hotels"): lst([f"{h.hotel_name} {h.check_in:%d %b}–{h.check_out:%d %b} ({h.room_type}, {h.meal_plan})" for h in booking.hotels.all()]),
        translation.gettext("Flights"): lst([f"{f.flight_number or f.airline} {f.flight_type} {f.flight_class}" for f in booking.flights.all()]),
        translation.gettext("Transport"): lst([f"{t.transporter} {t.vehicle_type} {t.travel_date:%d %b}" for t in booking.transports.all()]),
        translation.gettext("Team contacts"): str(booking.booking_instructions.count()),
    }


def worksheet_save(request, actor):
    """Create or update a voucher from the on-page worksheet.

    actor "member": the team (Save as draft / Save voucher; on a voucher waiting for approval also Save / Save & approve).
    actor "agent":  an agent (Save as draft / Submit for approval) — they only ever touch their own, unapproved vouchers.
    """
    agency = request.user.agency
    if not agency:
        return HttpResponse("No agency", status=400)

    list_url = "member-bookings" if actor == "member" else "agent-vouchers"
    raw_id = (request.POST.get("worksheet_booking_id") or "").strip()
    booking = None
    if raw_id:
        lookup = {"agency": agency}
        if actor == "agent":
            lookup["agent"] = request.user          # an agent only ever works on their own vouchers
        try:
            booking = Booking.objects.filter(pk=int(raw_id), **lookup).first()
        except ValueError:
            booking = None
        if not booking:
            messages.error(request, translation.gettext("Booking not found."))
            return redirect(list_url)
        if actor == "agent" and booking.status not in ("draft", "pending", "rejected"):
            messages.error(request, translation.gettext("This voucher is already approved, so it can't be changed."))
            return redirect(list_url)
    else:
        from billing.usage import check_booking_limit
        booking_ok, booking_message = check_booking_limit(agency)
        if not booking_ok:
            messages.error(request, booking_message)
            return redirect(list_url)

    package_name = (request.POST.get("package_name") or "").strip()
    client_whatsapp = (request.POST.get("client_whatsapp") or "").strip()
    notes = (request.POST.get("notes") or "").strip()
    if "notes" not in request.POST and booking is not None:
        notes = booking.notes
    save_as = (request.POST.get("save_as") or "").strip()
    current = booking.status if booking is not None else None
    if actor == "agent":
        # Agents can only keep a draft or submit it; the team approves.
        status = "pending" if save_as == "submit" else "draft"
    elif save_as == "draft":
        status = "draft"
    elif save_as == "keep" and current in ("pending", "rejected"):
        status = current                                    # edit a voucher without deciding on it
    elif save_as == "approve" and current == "pending":
        status = "confirmed"
    elif save_as in ("save", "approve", "keep"):
        # A saved voucher is final. Vouchers already completed or cancelled keep that status.
        status = current if current in ("completed", "cancelled") else "confirmed"
    else:
        status = (request.POST.get("status") or "draft").strip()
        if status not in dict(Booking.STATUS_CHOICES):
            status = "draft"
    is_draft = status == "draft"

    default_pax = 1 if booking is None else booking.pax_adults
    pax_adults = _parse_booking_int(request.POST.get("pax_adults"), default_pax)
    pax_children = _parse_booking_int(
        request.POST.get("pax_children"), 0 if booking is None else booking.pax_children
    )
    pax_infants = _parse_booking_int(
        request.POST.get("pax_infants"), 0 if booking is None else booking.pax_infants
    )
    total_beds = _parse_booking_int(
        request.POST.get("total_beds"), 0 if booking is None else (booking.total_beds or 0)
    )

    if not is_draft and pax_adults + pax_children + pax_infants < 1:
        messages.error(request, translation.gettext("At least one passenger is required."))
        return redirect(list_url)

    try:
        total_amount = Decimal(
            str((request.POST.get("total_amount") or "").strip() or "0").replace(",", "")
        )
    except Exception:
        total_amount = Decimal("0") if booking is None else booking.total_amount
    try:
        total_price = Decimal(
            str((request.POST.get("total_price") or "").strip() or "0").replace(",", "")
        )
    except Exception:
        total_price = Decimal("0") if booking is None else booking.total_price

    if "total_amount" not in request.POST:
        total_amount = Decimal("0") if booking is None else booking.total_amount
    if "total_price" not in request.POST:
        total_price = Decimal("0") if booking is None else booking.total_price

    hotels_payload = _parse_json_list(request.POST.get("hotels_json"))
    flights_payload = _parse_json_list(request.POST.get("flights_json"))
    transports_payload = _parse_json_list(request.POST.get("transports_json"))
    mutamers_payload = _parse_json_list(request.POST.get("mutamers_json"))
    instruction_ids = _parse_worksheet_instruction_ids(request)

    with transaction.atomic():
        created_now = booking is None
        if booking is None:
            seq, _ = VoucherSequence.objects.select_for_update().get_or_create(
                agency=agency,
                defaults={"current_sequence": 0},
            )
            voucher_number = seq.increment_and_get_next()
            booking = Booking.objects.create(
                voucher_number=voucher_number,
                package_name=package_name,
                client_whatsapp=client_whatsapp,
                pax_adults=pax_adults,
                pax_children=pax_children,
                pax_infants=pax_infants,
                total_beds=total_beds,
                status=status,
                total_amount=total_amount,
                total_price=total_price,
                notes=notes,
                agent=request.user,
                agency=agency,
            )
        else:
            booking.package_name = package_name
            booking.client_whatsapp = client_whatsapp
            booking.pax_adults = pax_adults
            booking.pax_children = pax_children
            booking.pax_infants = pax_infants
            booking.total_beds = total_beds
            booking.status = status
            booking.total_amount = total_amount
            booking.total_price = total_price
            booking.notes = notes
            booking.save()

        now = timezone.now()
        if status == "pending" and current != "pending":
            booking.submitted_at, booking.rejection_reason = now, ""      # (re)submitted for approval
            booking.decided_by, booking.decided_at = None, None
            booking.save(update_fields=["submitted_at", "rejection_reason", "decided_by", "decided_at", "updated_at"])
        elif save_as == "approve" and current == "pending" and actor == "member":
            booking.rejection_reason = ""
            booking.decided_by, booking.decided_at = request.user, now
            booking.save(update_fields=["rejection_reason", "decided_by", "decided_at", "updated_at"])

        before_content = _voucher_content(booking) if not created_now else None
        _replace_booking_line_items(
            agency,
            booking,
            hotels_payload,
            flights_payload,
            transports_payload,
            mutamers_payload,
            instruction_ids,
        )
        _sync_completed_booking_voucher(request, booking)
        if before_content is not None:
            from utils.audit import log_event
            after_content = _voucher_content(booking)
            log_event(booking, {k: {"old": before_content[k], "new": after_content[k]}
                                for k in after_content if before_content[k] != after_content[k]})
        if actor == "member":                   # internal team notes: agents neither see nor write them
            for text in _parse_json_list(request.POST.get("notes_json")):
                text = str(text or "").strip()
                if text:
                    BookingNote.objects.create(agency=agency, booking=booking, author=request.user, text=text[:2000])

    gt = translation.gettext
    if actor == "agent":
        if status == "pending":
            messages.success(request, gt("Voucher %(n)s submitted for approval.") % {"n": booking.voucher_number})
            return redirect("agent-vouchers")
        messages.success(request, gt("Draft saved — you can finish it any time."))
        return redirect("agent-voucher-edit", booking_id=booking.id)
    if save_as == "approve" and current == "pending":
        messages.success(request, gt("Voucher %(n)s saved and approved.") % {"n": booking.voucher_number})
        return redirect("member-approvals")
    if is_draft:
        messages.success(request, gt("Draft saved — you can finish it any time."))
    elif status in ("pending", "rejected"):
        messages.success(request, gt("Voucher %(n)s saved.") % {"n": booking.voucher_number})
        return redirect("member-approvals")
    else:
        messages.success(request, gt("Voucher saved. You can print or download PDF from the links below."))
    return redirect("member-booking-detail", booking_id=booking.id)


@member_required
@require_POST
def booking_update(request, booking_id):
    agency = request.user.agency
    booking = get_object_or_404(Booking, pk=booking_id, agency=agency)

    package_name = (request.POST.get("package_name") or "").strip()
    client_whatsapp = (request.POST.get("client_whatsapp") or "").strip()
    notes = (request.POST.get("notes") or "").strip()
    status = (request.POST.get("status") or booking.status).strip()
    if status not in dict(Booking.STATUS_CHOICES):
        status = booking.status

    pax_adults = _parse_booking_int(request.POST.get("pax_adults"), booking.pax_adults)
    pax_children = _parse_booking_int(request.POST.get("pax_children"), booking.pax_children)
    pax_infants = _parse_booking_int(request.POST.get("pax_infants"), booking.pax_infants)
    total_beds = _parse_booking_int(request.POST.get("total_beds"), booking.total_beds or 0)

    if pax_adults + pax_children + pax_infants < 1:
        messages.error(request, translation.gettext("At least one passenger is required."))
        return redirect("member-booking-detail", booking_id=booking.id)

    try:
        total_amount = Decimal(
            str((request.POST.get("total_amount") or "").strip() or "0").replace(",", "")
        )
    except Exception:
        total_amount = booking.total_amount
    try:
        total_price = Decimal(
            str((request.POST.get("total_price") or "").strip() or "0").replace(",", "")
        )
    except Exception:
        total_price = booking.total_price

    hotels_payload = _parse_json_list(request.POST.get("hotels_json"))
    flights_payload = _parse_json_list(request.POST.get("flights_json"))
    transports_payload = _parse_json_list(request.POST.get("transports_json"))
    mutamers_payload = _parse_json_list(request.POST.get("mutamers_json"))

    instruction_ids = _parse_worksheet_instruction_ids(request)

    with transaction.atomic():
        booking.package_name = package_name
        booking.client_whatsapp = client_whatsapp
        booking.pax_adults = pax_adults
        booking.pax_children = pax_children
        booking.pax_infants = pax_infants
        booking.total_beds = total_beds
        booking.status = status
        booking.total_amount = total_amount
        booking.total_price = total_price
        booking.notes = notes
        booking.save()

        _replace_booking_line_items(
            agency,
            booking,
            hotels_payload,
            flights_payload,
            transports_payload,
            mutamers_payload,
            instruction_ids,
        )
        _sync_completed_booking_voucher(request, booking)

    messages.success(request, translation.gettext("Voucher and itinerary saved."))
    return redirect("member-booking-detail", booking_id=booking.id)


def render_voucher_print(request, booking):
    ctx = _voucher_context(request, booking)
    ctx["print_mode"] = True
    ctx["for_pdf"] = False
    return render(request, "member/voucher_document.html", ctx)


@member_required
@require_http_methods(["GET", "HEAD"])
def booking_voucher_print(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, agency=request.user.agency)
    return render_voucher_print(request, booking)


@member_required
def booking_voucher_pdf(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, agency=request.user.agency)
    return render_voucher_pdf(request, booking)


def render_voucher_pdf(request, booking):
    ctx = _voucher_context(request, booking)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in booking.voucher_number)[:80]

    # Preferred: print the very same page the View button shows with headless Chrome, so the file is identical to it.
    from . import pdf_chrome

    if pdf_chrome.find_chrome():
        page = dict(ctx, print_mode=True, for_pdf=False, embed_font=pdf_chrome.font_data_uri())
        try:
            page["logo_url"] = pdf_chrome.data_uri(ctx["branding"].logo.path) if ctx.get("branding") and ctx["branding"].logo else ""
        except (OSError, ValueError):
            page["logo_url"] = ""
        data = pdf_chrome.html_to_pdf(render_to_string("member/voucher_document.html", page, request=request))
        if data:
            response = HttpResponse(data, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="voucher_{safe_name}.pdf"'
            return response

    # Fallback (no browser on the server): the table-based layout for xhtml2pdf.
    ctx["print_mode"] = False
    ctx["for_pdf"] = True
    ctx["pdf_instructions"] = _pdf_instructions(ctx.get("voucher_instructions") or [])
    html = render_to_string("member/voucher_document.html", ctx, request=request)
    response = HttpResponse(content_type="application/pdf")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in booking.voucher_number)[
        :80
    ]
    response["Content-Disposition"] = f'attachment; filename="voucher_{safe_name}.pdf"'
    pisa.CreatePDF(
        BytesIO(html.encode("utf-8")),
        dest=response,
        encoding="utf-8",
        link_callback=_voucher_pdf_link_callback,
    )
    return response



@member_required
def approvals(request):
    """Vouchers agents submitted that are waiting for a decision — all of them, whatever their age.

    Approved vouchers move to the Vouchers page, sent-back ones return to their agent; the history is in Approval insights."""
    agency = request.user.agency
    base = Booking.objects.filter(agency=agency).select_related("agent") if agency else Booking.objects.none()
    pending = base.filter(status="pending")
    q = (request.GET.get("q") or "").strip()
    qs = pending
    if q:
        qs = qs.filter(
            Q(voucher_number__icontains=q) | Q(package_name__icontains=q)
            | Q(id__in=BookingMutamer.objects.filter(
                Q(name__icontains=q) | Q(passport_number__icontains=q)).values("booking_id"))
            | Q(agent__username__icontains=q) | Q(agent__first_name__icontains=q) | Q(agent__last_name__icontains=q))
    since = timezone.now() - datetime.timedelta(days=APPROVAL_WINDOW_DAYS)
    ctx = {
        "vouchers": decorate_voucher_rows(qs.order_by("submitted_at", "created_at")),     # oldest waiting first
        "page_title": "Approvals",
        "approval_stats": {
            "pending": pending.count(),
            "approved": base.filter(decided_by__isnull=False, status__in=("confirmed", "completed"),
                                    decided_at__gte=since).count(),
        },
        "search_q": q,
        "filters_active": bool(q),
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/approvals_htmx.html", ctx)
    return render(request, "member/approvals.html", ctx)


INVENTORY_INSIGHTS = {
    "hotels": ("member-hotels", "Hotels"),
    "flights": ("member-flights", "Flights"),
    "transports": ("member-transports", "Transports"),
    "packages": ("member-packages", "Packages"),
    "ledger": ("member-ledger", "Ledger"),
    "attendance": ("member-attendance", "Attendance"),
}


@member_required
def inventory_insights(request, kind):
    """Insights for Hotels, Flights, Transports or Packages — own date range, Excel and PDF download."""
    from member import analytics

    from . import inventory_insights as ii

    if kind not in ii.KINDS:
        raise Http404
    agency = request.user.agency
    if not agency:
        return redirect("member-dashboard")
    period = analytics.resolve_period(request.GET)
    data = ii.build(kind, agency, period)
    if request.GET.get("export") == "xlsx":
        content = ii.build_xlsx(agency, period, data, rtl=translation.get_language_bidi())
        response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = (
            f'attachment; filename="{kind}-insights-{period["start"]:%Y%m%d}-{period["end"]:%Y%m%d}.xlsx"')
        return response
    back_name, back_label = INVENTORY_INSIGHTS[kind]
    return render(request, "member/inventory_insights.html", {
        "page_title": data["title"], "period": period, "data": data, "presets": analytics.PRESETS,
        "charts_json": ii.chart_payload(data), "back_url": reverse(back_name), "back_label": translation.gettext(back_label),
    })


@member_required
def approval_insights(request):
    """How vouchers agents submit move through approval, with its own date range and Excel / PDF download."""
    from member import analytics

    from . import approval_insights as ai

    agency = request.user.agency
    if not agency:
        return redirect("member-dashboard")
    period = analytics.resolve_period(request.GET)
    data = ai.build(agency, period)
    if request.GET.get("export") == "xlsx":
        content = ai.build_xlsx(agency, period, data, rtl=translation.get_language_bidi())
        response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = (
            f'attachment; filename="approval-insights-{period["start"]:%Y%m%d}-{period["end"]:%Y%m%d}.xlsx"')
        return response
    return render(request, "member/approval_insights.html", {
        "page_title": "Approval insights", "period": period, "data": data, "presets": analytics.PRESETS,
    })


@member_required
@require_POST
def approval_approve(request, booking_id):
    """Approve a voucher an agent submitted: it becomes a saved voucher."""
    booking = get_object_or_404(Booking, pk=booking_id, agency=request.user.agency)
    if booking.status != "pending":
        return JsonResponse({"detail": translation.gettext("Only vouchers waiting for approval can be approved.")}, status=400)
    booking.status, booking.rejection_reason = "confirmed", ""
    booking.decided_by, booking.decided_at = request.user, timezone.now()
    booking.save(update_fields=["status", "rejection_reason", "decided_by", "decided_at", "updated_at"])
    return JsonResponse({"detail": "ok"})


@member_required
@require_POST
def approval_reject(request, booking_id):
    """Send a voucher back to its agent. The reason is required: the agent sees it, fixes the voucher and resubmits."""
    booking = get_object_or_404(Booking, pk=booking_id, agency=request.user.agency)
    if booking.status != "pending":
        return JsonResponse({"detail": translation.gettext("Only vouchers waiting for approval can be sent back.")}, status=400)
    try:
        reason = str(json.loads(request.body or b"{}").get("reason") or "").strip()
    except (ValueError, AttributeError):
        reason = ""
    if not reason:
        return JsonResponse({"detail": translation.gettext("Please give a reason so the agent knows what to fix.")}, status=400)
    booking.status, booking.rejection_reason = "rejected", reason[:2000]
    booking.decided_by, booking.decided_at = request.user, timezone.now()
    booking.save(update_fields=["status", "rejection_reason", "decided_by", "decided_at", "updated_at"])
    return JsonResponse({"detail": "ok"})


LEDGER_PAGE_SIZE = 100


def _ledger_dashboard_stats(agency):
    """Headline cards: these ignore the table filters on purpose."""
    balances = ledger_helpers.party_balances(agency)
    receivable, payable = ledger_helpers.receivable_payable(balances)
    month_start, month_end = ledger_helpers.preset_range("this_month")
    month_qs = LedgerEntry.objects.filter(agency=agency, transaction_date__range=(month_start, month_end))
    month = month_qs.aggregate(
        received=Sum("amount", filter=Q(bucket="lein_dein", direction="credit")),
        expenses=Sum("amount", filter=Q(bucket="company_expense")),
    )
    return {
        "receivable": receivable,
        "payable": payable,
        "received_month": month["received"] or 0,
        "expenses_month": month["expenses"] or 0,
        "party_count": len(balances),
        "balances": balances,
    }


def _ledger_results_context(request, agency):
    f = ledger_helpers.read_filters(request.GET)
    ctx = {"f": f}
    qs = ledger_helpers.filtered_entries(agency, f).select_related("created_by", "booking")
    ctx["totals"] = ledger_helpers.debit_credit_totals(qs)
    # A running balance only makes sense for one party's complete statement:
    # narrowing by type or search would make the carried balance wrong.
    show_running = bool(f["party"]) and not f["type"] and not f["q"] and f["bucket"] != "company_expense"
    if show_running:
        opening = ledger_helpers.opening_balance(agency, f["party"], f["date_from"])
        rows = ledger_helpers.with_running_balance(qs.order_by("transaction_date", "created_at", "id"), opening)
        ctx.update({
            "entries": rows,
            "opening": opening,
            "closing": opening + ctx["totals"]["net"],
            "entry_count": len(rows),
        })
    else:
        page = Paginator(qs.order_by("-transaction_date", "-created_at", "-id"), LEDGER_PAGE_SIZE).get_page(
            request.GET.get("page")
        )
        ctx.update({"entries": page.object_list, "page": page, "entry_count": page.paginator.count})
    ctx["show_running"] = show_running
    return ctx


@member_required
def ledger(request):
    agency = request.user.agency
    if not agency:
        return redirect("member-dashboard")
    ctx = _ledger_results_context(request, agency)
    # Filters push the URL, so Back triggers an htmx history restore, which
    # needs the full page rather than the fragment.
    if request.headers.get("HX-Request") and not request.headers.get("HX-History-Restore-Request"):
        return render(request, "member/partials/ledger_htmx.html", ctx)
    stats = _ledger_dashboard_stats(agency)
    balance_by_name = {b["name"]: b["balance"] for b in stats["balances"]}
    ctx.update({
        "page_title": "Ledger",
        "stats": stats,
        # Lets the entry form preview "balance before -> after" as you type.
        "party_balance_map": {name: str(bal) for name, bal in balance_by_name.items()},
        "party_options": [
            {"name": name, "balance": balance_by_name.get(name)}
            for name in ledger_helpers.party_names(agency)
        ],
        "type_choices": LedgerEntry.TRANSACTION_TYPES,
        "fx_choices": LedgerEntry.FX_CURRENCIES,
        "method_choices": LedgerEntry.PAYMENT_METHODS,
    })
    return render(request, "member/ledger.html", ctx)


@member_required
def ledger_export(request):
    """CSV (opens in Excel) of the ledger rows matching the page's filters."""
    agency = request.user.agency
    if not agency:
        return redirect("member-dashboard")
    f = ledger_helpers.read_filters(request.GET)
    qs = ledger_helpers.filtered_entries(agency, f).order_by("transaction_date", "created_at", "id")
    show_running = bool(f["party"]) and not f["type"] and not f["q"] and f["bucket"] != "company_expense"
    rows = qs
    if show_running:
        rows = ledger_helpers.with_running_balance(qs, ledger_helpers.opening_balance(agency, f["party"], f["date_from"]))

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    stamp = timezone.localdate().strftime("%Y%m%d")
    response["Content-Disposition"] = f'attachment; filename="ledger-{stamp}.csv"'
    response.write("﻿")  # BOM so Excel reads Urdu/Arabic names correctly
    writer = csv.writer(response)
    header = ["Date", "Type", "Trans.#", "Party", "Particulars", "PAX", "Inv/Ref", "Foreign amount",
              "Rate", "Debit", "Credit"]
    if show_running:
        header.append("Balance")
    header += ["Method", "Category", "Reference", "Account"]
    writer.writerow(header)
    for e in rows:
        line = [
            e.transaction_date.isoformat(), e.type_code, e.trans_no, e.counterparty_name, e.description,
            e.pax or "", e.inv_ref, f"{e.fx_amount} {e.fx_currency}" if e.fx_amount is not None else "",
            e.rate if e.rate is not None else "", e.debit, e.credit,
        ]
        if show_running:
            line.append(e.running)
        line += [e.get_payment_method_display(), e.category, e.reference_number,
                 "Party" if e.bucket == "lein_dein" else "Company expense"]
        writer.writerow(line)
    return response


@member_required
def ledger_report(request):
    """
    Printable account ledger in the travel-trade statement layout.

    ?party=NAME  -> one party's statement (opening balance, running balance,
                    totals, PAX per service).
    no party     -> every party active in the period, then company expenses.
    Period: ?from=YYYY-MM-DD&to=YYYY-MM-DD, ?preset=..., or legacy ?month=YYYY-MM;
    defaults to the current month.
    """
    agency = request.user.agency
    if not agency:
        return redirect("member-dashboard")
    f = ledger_helpers.read_filters(request.GET)
    if not (f["date_from"] or f["date_to"]) and f["preset"] != "all":
        f["date_from"], f["date_to"] = ledger_helpers.preset_range("this_month")

    if f["party"]:
        statements = [ledger_helpers.party_statement(agency, f["party"], f["date_from"], f["date_to"])]
        expense_entries = []
    else:
        period_qs = ledger_helpers.filtered_entries(agency, {**f, "q": "", "type": "", "bucket": ""})
        names = (
            period_qs.filter(bucket="lein_dein").exclude(counterparty_name="")
            .values_list("counterparty_name", flat=True).distinct().order_by("counterparty_name")
        )
        statements = [
            ledger_helpers.party_statement(agency, name, f["date_from"], f["date_to"]) for name in names
        ]
        expense_entries = list(period_qs.filter(bucket="company_expense").order_by("transaction_date", "created_at"))

    ctx = {
        "page_title": "Ledger report",
        "agency": agency,
        "branding": AgencyBranding.objects.filter(agency=agency).first(),
        "f": f,
        "print_date": timezone.localdate(),
        "statements": statements,
        "single_party": bool(f["party"]),
        "expense_entries": expense_entries,
        "expense_total": sum((e.amount for e in expense_entries), Decimal("0")),
        "currency": agency.default_currency or "PKR",
    }
    return render(request, "member/ledger_report.html", ctx)


@member_required
def attendance(request):
    agency = request.user.agency
    base_qs = (
        AttendanceLog.objects.filter(agency=agency).select_related("user", "user__custom_role").order_by("-date", "-created_at")
        if agency
        else AttendanceLog.objects.none()
    )

    month_filter = (request.GET.get("month") or "").strip()  # YYYY-MM
    if not month_filter:
        today = datetime.date.today()
        month_filter = f"{today.year:04d}-{today.month:02d}"

    year_i, month_i = None, None
    try:
        ys, ms = month_filter.split("-", 1)
        year_i = int(ys)
        month_i = int(ms)
    except Exception:
        today = datetime.date.today()
        year_i = today.year
        month_i = today.month
        month_filter = f"{year_i:04d}-{month_i:02d}"

    start_date = datetime.date(year_i, month_i, 1)
    end_date = datetime.date(year_i, month_i, calendar.monthrange(year_i, month_i)[1])

    qs = base_qs.filter(date__range=(start_date, end_date))

    # Everyone with member login can view their own records.
    # If agency uses shared staff names, also match by full name.
    my_name = (request.user.full_name or "").strip()
    my_logs = qs.filter(Q(user=request.user) | Q(person_name=my_name))

    # Managers (attendance:manage) see everyone's records; others only their own.
    # Records come only from self check-in, automatic absences and approved corrections.
    is_admin_user = bool(agency and has_capability(request.user, 'attendance', 'manage'))
    logs = qs if is_admin_user else my_logs

    # All-records filters (staff / status / verified-by / today only).
    rec_filters = {
        "staff": (request.GET.get("staff") or "").strip(),
        "status": (request.GET.get("status") or "").strip(),
        "source": (request.GET.get("source") or "").strip(),
        "day": (request.GET.get("day") or "").strip(),
    }
    current_month = datetime.date.today().strftime("%Y-%m")
    if agency:
        current_month = att_rules.office_now(att_rules.get_settings(agency)).date().strftime("%Y-%m")
    # Today by default when looking at the current month; other months show every day.
    if rec_filters["day"] not in ("today", "month"):
        rec_filters["day"] = "today" if month_filter == current_month else "month"
    if month_filter != current_month:
        rec_filters["day"] = "month"
    staff_options = sorted(set(logs.values_list("person_name", flat=True)), key=str.lower)
    if rec_filters["staff"]:
        logs = logs.filter(person_name=rec_filters["staff"])
    if rec_filters["status"] in dict(AttendanceLog.STATUS_CHOICES):
        logs = logs.filter(status=rec_filters["status"])
    if rec_filters["source"] in dict(AttendanceLog.SOURCE_CHOICES):
        logs = logs.filter(source=rec_filters["source"])
    if rec_filters["day"] == "today" and agency:
        logs = logs.filter(date=att_rules.office_now(att_rules.get_settings(agency)).date())

    # One aggregate query instead of five counts.
    attendance_stats = my_logs.aggregate(
        present=Count("id", filter=Q(status="present")), absent=Count("id", filter=Q(status="absent")),
        late=Count("id", filter=Q(status="late")), leave=Count("id", filter=Q(status="leave")), total=Count("id"))

    att_settings = att_rules.get_settings(agency) if agency else None
    board_rows, corrections = [], []
    if agency and is_admin_user:
        att_rules.ensure_absences(agency, att_settings, start_date, end_date)
        board_rows = att_rules.board(agency, att_settings, att_rules.office_now(att_settings).date())
        # Each request with the record it would change, so the card can show "now -> requested".
        corrections = [
            {"c": c, "current": att_rules.todays_log(agency, c.user, c.date)}
            for c in att_rules.pending_corrections(agency)
        ]

    return render(
        request,
        "member/attendance.html",
        {
            "page_title": "Attendance",
            "att_settings": att_settings,
            "today_date": att_rules.office_now(att_settings).date() if att_settings else None,
            "board_rows": board_rows,
            "board_counts": {
                k: sum(1 for r in board_rows if r["state"] == k) for k in ("present", "late", "absent", "not_in", "leave")
            },
            "rec_filters": rec_filters,
            "rec_filtered": any(rec_filters[k] for k in ("staff", "status", "source")),
            "is_current_month": month_filter == current_month,
            "staff_options": staff_options,
            "status_choices": AttendanceLog.STATUS_CHOICES,
            # Manual entry was retired; old rows still display their label.
            "source_choices": [c for c in AttendanceLog.SOURCE_CHOICES if c[0] != "manual"],
            "corrections": corrections,
            "checks_enabled": bool(att_settings and (att_settings.require_network or att_settings.require_qr
                                                     or att_settings.require_location)),
            "month_filter": month_filter,
            "period_start": start_date,
            "period_end": end_date,
            "attendance_stats": attendance_stats,
            "logs": logs,
            "my_logs": my_logs,
            "is_admin_user": is_admin_user,
        },
    )


@member_required
def contacts(request):
    """
    Contacts page used for voucher-visible contact instructions:
    City, Role, Contact Name, Phone Number, Notes.
    """
    agency = request.user.agency
    base_qs = (
        ContactInstruction.objects.filter(agency=agency).order_by("-created_at")
        if agency
        else ContactInstruction.objects.none()
    )

    q = (request.GET.get("q") or "").strip()
    city_filter = ""

    qs = base_qs
    if q:
        qs = qs.filter(
            Q(city__icontains=q)
            | Q(role__icontains=q)
            | Q(contact_name__icontains=q)
            | Q(phone_number__icontains=q)
            | Q(notes__icontains=q)
        )

    contact_stats = {
        "total": base_qs.count(),
    }

    cities = (
        list(
            base_qs.values_list("city", flat=True)
            .order_by("city")
            .distinct()
        )
        if agency
        else []
    )

    ctx = {
        "voucher_instructions": (
            VoucherInstruction.objects.filter(agency=agency).order_by("sort_order", "id") if agency
            else VoucherInstruction.objects.none()
        ),
        "contacts": qs,
        "page_title": "Contacts",
        "contact_stats": contact_stats,
        "search_q": q,
        "city_filter": city_filter,
        "cities": cities,
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/contacts_htmx.html", ctx)
    return render(request, "member/contacts.html", ctx)


@member_required
@require_POST
def contact_create(request):
    agency = request.user.agency
    if not agency:
        return HttpResponse(translation.gettext("No agency"), status=400)

    city = (request.POST.get("city") or "").strip()
    role = (request.POST.get("role") or "").strip()
    contact_name = (request.POST.get("contact_name") or "").strip()
    phone_number = (request.POST.get("phone_number") or "").strip()
    notes = (request.POST.get("notes") or "").strip()

    if not city or not role or not contact_name or not phone_number:
        return HttpResponse(translation.gettext("Missing required fields"), status=400)

    ContactInstruction.objects.create(
        agency=agency,
        created_by=request.user,
        city=city,
        role=role,
        contact_name=contact_name,
        phone_number=phone_number,
        notes=notes,
    )
    return HttpResponse("OK", status=200)


@member_required
@require_POST
def contact_update(request, contact_id: int):
    agency = request.user.agency
    if not agency:
        return HttpResponse(translation.gettext("No agency"), status=400)

    c = ContactInstruction.objects.filter(id=contact_id, agency=agency).first()
    if not c:
        return HttpResponse(translation.gettext("Not found"), status=404)

    city = (request.POST.get("city") or "").strip()
    role = (request.POST.get("role") or "").strip()
    contact_name = (request.POST.get("contact_name") or "").strip()
    phone_number = (request.POST.get("phone_number") or "").strip()
    notes = (request.POST.get("notes") or "").strip()

    if not city or not role or not contact_name or not phone_number:
        return HttpResponse(translation.gettext("Missing required fields"), status=400)

    c.city = city
    c.role = role
    c.contact_name = contact_name
    c.phone_number = phone_number
    c.notes = notes
    c.save()
    return HttpResponse("OK", status=200)


@member_required
@require_POST
def contact_delete(request, contact_id: int):
    agency = request.user.agency
    if not agency:
        return HttpResponse(translation.gettext("No agency"), status=400)
    c = ContactInstruction.objects.filter(id=contact_id, agency=agency).first()
    if not c:
        return HttpResponse(translation.gettext("Not found"), status=404)
    c.delete()
    return HttpResponse("OK", status=200)


def profile(request):
    # Member-only: agency settings + branding
    if request.user.role != "member":
        return redirect("/member/dashboard/")

    agency = request.user.agency
    branding = None
    if agency:
        branding, _ = AgencyBranding.objects.get_or_create(agency=agency)

    return render(request, "member/profile.html", {
        "page_title": "Agency settings",
        "agency": agency,
        "branding": branding,
    })


@member_required
@require_POST
def profile_update_branding(request):
    agency = request.user.agency
    if not agency:
        return HttpResponse(translation.gettext("No agency"), status=400)

    branding, _ = AgencyBranding.objects.get_or_create(agency=agency)

    company_name = (request.POST.get("company_name") or "").strip()
    address = (request.POST.get("address") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    email = (request.POST.get("email") or "").strip()
    website = (request.POST.get("website") or "").strip()
    shirka_name = (request.POST.get("shirka_company_name") or "").strip()
    shirka_country = (request.POST.get("shirka_company_country") or "").strip()
    shirka_whatsapp = (request.POST.get("shirka_company_whatsapp") or "").strip()

    if not company_name:
        return HttpResponse(translation.gettext("Company name is required"), status=400)

    logo = request.FILES.get("logo")
    if logo:
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/svg+xml"]
        if getattr(logo, "content_type", "") not in allowed_types:
            return HttpResponse(translation.gettext("Logo must be JPEG, PNG, GIF, or SVG"), status=400)
        if logo.size > 5 * 1024 * 1024:
            return HttpResponse(translation.gettext("Logo file too large (max 5MB)"), status=400)
        branding.logo = logo

    branding.company_name = company_name
    branding.address = address
    branding.phone = phone
    branding.email = email
    branding.website = website
    branding.shirka_company_name = shirka_name
    branding.shirka_company_country = shirka_country
    branding.shirka_company_whatsapp = shirka_whatsapp
    branding.save()

    # Keep core Agency record aligned for legacy lookups
    agency.name = company_name or agency.name
    if phone:
        agency.phone = phone
    if email:
        agency.email = email
    if address:
        agency.address = address
    agency.save(update_fields=["name", "phone", "email", "address", "updated_at"])

    return HttpResponse("OK", status=200)


@agent_required
def settings_home(request):
    """Sidebar → Settings. Lands on the first section this user can manage."""
    if has_capability(request.user, "attendance", "manage"):
        return redirect("attendance-settings")
    if request.user.role == "member":
        return redirect("profile")
    return redirect("language-settings")


@agent_required
def language_settings(request):
    """Personal, account-wide UI language — available to every role
    (agent_required is the level-10 floor, i.e. any logged-in staff
    user), unlike 'profile' which is agency branding/settings for the
    member tier only."""
    if request.method == "POST":
        lang = (request.POST.get("language") or "").strip() or None
        valid_codes = {code for code, _label in ENABLED_LANGUAGES}
        if lang is not None and lang not in valid_codes:
            messages.error(request, translation.gettext("Unknown language."))
            return redirect("language-settings")

        request.user.preferred_language = lang
        request.user.save(update_fields=["preferred_language", "updated_at"])

        messages.success(request, translation.gettext("Language updated."))
        response = redirect("language-settings")
        if lang:
            translation.activate(lang)
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang, max_age=settings.LANGUAGE_COOKIE_AGE)
        else:
            translation.activate(translation.get_language_from_request(request))
            response.delete_cookie(settings.LANGUAGE_COOKIE_NAME)
        return response

    return render(request, "member/language_settings.html", {
        "page_title": "Language",
        "languages": [(c, NATIVE_NAMES.get(c, label), label) for c, label in ENABLED_LANGUAGES],
        "current": request.user.preferred_language,
    })


# ==========================================
# PUBLIC VIEWS
# ==========================================

def public_voucher(request, token):
    # Unauthenticated by design — the unguessable public_token itself is
    # the access control here, not tenant context (there isn't any: this
    # is an anonymous request). Voucher.objects/AgencyBranding.objects
    # would fail-closed to nothing for an anonymous visitor, so this
    # explicitly uses the unscoped manager.
    voucher = get_object_or_404(Voucher.all_tenants.select_related("agent", "agent__agency"), public_token=token)
    preview = voucher.status != "approved"
    if preview:
        # Anonymous visitors only ever see approved vouchers. A signed-in member of the same agency may preview
        # one that is still waiting (or was sent back) — that is what the Approvals page's eye icon opens.
        user = request.user
        if not (user.is_authenticated and (user.is_superuser or user.agency_id == voucher.agency_id)):
            raise Http404
    services = voucher.services.all()
    agency = voucher.agent.agency
    branding = AgencyBranding.all_tenants.filter(agency=agency).first()
    return render(request, "public/voucher.html", {
        "voucher_instructions": active_voucher_instructions(agency, unscoped=True),
        "voucher": voucher,
        "preview": preview,
        "services": services,
        "branding": branding,
        "agency": agency,
    })
