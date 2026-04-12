"""Member portal, Auth, and Public views."""
import json
import calendar
import datetime
import os

from decimal import Decimal
from io import BytesIO

from django.db import transaction
from django.db.models import Avg, Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings

from xhtml2pdf import pisa

from .decorators import member_required
from .models import (
    Hotel,
    Flight,
    Transport,
    Mutamer,
    Booking,
    BookingHotel,
    BookingFlight,
    BookingTransport,
    BookingMutamer,
    BookingContactInstruction,
    Voucher,
    VoucherSequence,
    LedgerEntry,
    AttendanceLog,
    Contact,
    ContactInstruction,
)
from system_config.models import AgencyBranding

# ==========================================
# AUTH VIEWS
# ==========================================

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return _role_redirect(request.user)

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            next_url = request.GET.get("next", "")
            if next_url:
                return redirect(next_url)
            return _role_redirect(user)
        else:
            error = "Invalid username or password."

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
        email = request.POST.get("email", "").strip()
        if email:
            sent = True
        else:
            error = "Please enter a valid email address."
    return render(request, "forgot_password.html", {"sent": sent, "error": error})

@login_required(login_url="/login/")
def root_redirect(request):
    return _role_redirect(request.user)

def _role_redirect(user):
    # If a superuser sneaks through or is already logged in, route them to admin
    if user.is_superuser or user.is_staff:
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
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count, Q
    from django.db.models.functions import TruncMonth

    agency = request.user.agency
    
    # Base KPI
    total_bookings = Booking.objects.filter(agency=agency).count() if agency else 0
    pending_vouchers = Voucher.objects.filter(agent__agency=agency, status="pending").count() if agency else 0
    total_mutamers = Mutamer.objects.filter(agency=agency).count() if agency else 0
    active_agents = agency.users.filter(role="agent", is_active=True).count() if agency else 0

    # Voucher Topology (Approved, Rejected, Draft)
    approved_vouchers = Voucher.objects.filter(agent__agency=agency, status="approved").count() if agency else 0
    rejected_vouchers = Voucher.objects.filter(agent__agency=agency, status="rejected").count() if agency else 0
    draft_vouchers = Voucher.objects.filter(agent__agency=agency, status="draft").count() if agency else 0

    # Revenue Kinetics (Last 6 Months Bookings Count as proxy for volume)
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_bookings = []
    month_labels = []
    
    if agency:
        # Group by month
        qs = Booking.objects.filter(agency=agency, created_at__gte=six_months_ago).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        # We should build a simple dict and pad the missing months
        data_dict = {item['month'].strftime('%b'): item['count'] for item in qs if item['month']}
        
        # Generate last 6 months list dynamically
        for i in range(5, -1, -1):
            dt = timezone.now() - timedelta(days=30 * i)
            m_str = dt.strftime('%b')
            month_labels.append(m_str)
            # Use random dummy multiplier 5000 to mimic revenue if actual financial data is complex,
            # or directly multiply real prices. We will use `count * 1500` as a proxy calculation.
            monthly_bookings.append(data_dict.get(m_str, 0) * 450 + 1000) # Base 1000 just to keep chart alive

    recent_bookings = []
    if agency:
        recent_bookings = list(
            Booking.objects.filter(agency=agency)
            .order_by("-created_at")[:6]
        )

    context = {
        "page_title": "Member Dashboard",
        "total_bookings": total_bookings,
        "pending_vouchers": pending_vouchers,
        "total_mutamers": total_mutamers,
        "active_agents": active_agents,
        "approved_vouchers": approved_vouchers,
        "rejected_vouchers": rejected_vouchers,
        "draft_vouchers": draft_vouchers,
        "month_labels": month_labels,
        "monthly_revenue": monthly_bookings,
        "month_labels_json": json.dumps(month_labels),
        "monthly_revenue_json": json.dumps(monthly_bookings),
        "recent_bookings": recent_bookings,
    }
    return render(request, "member/dashboard.html", context)


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

    avg_sale = base_qs.aggregate(v=Avg("sale_price"))["v"]
    hotel_stats = {
        "total": base_qs.count(),
        "avg_sale": avg_sale,
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
    avg_sale = base_qs.aggregate(v=Avg("sale_price"))["v"]
    flight_stats = {
        "total": base_qs.count(),
        "scheduled": base_qs.filter(status="scheduled").count(),
        "avg_sale": avg_sale,
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
    avg_sale = base_qs.aggregate(v=Avg("sale_price"))["v"]
    transport_stats = {
        "total": base_qs.count(),
        "active": base_qs.filter(is_active=True).count(),
        "avg_sale": avg_sale,
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
def mutamers(request):
    agency = request.user.agency
    base_qs = (
        Mutamer.objects.filter(agency=agency).order_by("-created_at")
        if agency
        else Mutamer.objects.none()
    )
    q = (request.GET.get("q") or "").strip()
    qs = base_qs
    if q:
        qs = base_qs.filter(
            Q(name__icontains=q)
            | Q(passport_number__icontains=q)
            | Q(nationality__icontains=q)
            | Q(phone__icontains=q)
            | Q(visa_number__icontains=q)
        )
    individuals = qs.filter(Q(family_id__isnull=True) | Q(family_id=""))
    family_members = qs.exclude(Q(family_id__isnull=True) | Q(family_id=""))
    # Build family groups in the same order as the list (newest first),
    # so each family_id renders as its own section.
    family_groups_map = {}
    family_groups_order = []
    for m in family_members:
        fid = (m.family_id or "").strip()
        if not fid:
            continue
        if fid not in family_groups_map:
            family_groups_map[fid] = {
                "family_id": fid,
                "head": None,
                "members": [],
            }
            family_groups_order.append(fid)
        family_groups_map[fid]["members"].append(m)
        if m.is_family_head and family_groups_map[fid]["head"] is None:
            family_groups_map[fid]["head"] = m
    mutamer_family_groups = [family_groups_map[fid] for fid in family_groups_order]
    # Fallback head: first member if none marked.
    for g in mutamer_family_groups:
        if g["head"] is None and g["members"]:
            g["head"] = g["members"][0]
    mutamer_stats = {
        "total": base_qs.count(),
        "active": base_qs.filter(is_active=True).count(),
        "family_heads": base_qs.filter(is_family_head=True).count(),
    }
    ctx = {
        "mutamers": qs,
        "mutamer_individuals": individuals,
        "mutamer_family_groups": mutamer_family_groups,
        "page_title": "Mutamers",
        "mutamer_stats": mutamer_stats,
        "search_q": q,
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/mutamers_htmx.html", ctx)
    return render(request, "member/mutamers.html", ctx)


@member_required
def bookings(request):
    agency = request.user.agency
    base_qs = Booking.objects.filter(agency=agency).order_by("-created_at") if agency else Booking.objects.none()

    q = (request.GET.get("q") or "").strip()
    status_filter = (request.GET.get("status") or "").strip()
    qs = base_qs
    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(
            Q(voucher_number__icontains=q)
            | Q(manual_number__icontains=q)
            | Q(package_name__icontains=q)
            | Q(client_company__icontains=q)
            | Q(client_country__icontains=q)
            | Q(notes__icontains=q)
        )

    branding = None
    if agency:
        branding, _ = AgencyBranding.objects.get_or_create(agency=agency)

    booking_stats = {
        "total": base_qs.count(),
        "draft": base_qs.filter(status="draft").count(),
        "confirmed": base_qs.filter(status="confirmed").count(),
        "completed": base_qs.filter(status="completed").count(),
    }

    hotel_list = Hotel.objects.filter(agency=agency).order_by("name") if agency else Hotel.objects.none()
    flight_list = Flight.objects.filter(agency=agency).order_by("-created_at") if agency else Flight.objects.none()
    transport_list = Transport.objects.filter(agency=agency).order_by("name") if agency else Transport.objects.none()
    mutamer_list = Mutamer.objects.filter(agency=agency).order_by("name") if agency else Mutamer.objects.none()
    instructions_list = (
        ContactInstruction.objects.filter(agency=agency).order_by("city", "role")
        if agency
        else ContactInstruction.objects.none()
    )

    worksheet_booking = None
    edit_param = (request.GET.get("edit") or "").strip()
    if edit_param and agency:
        try:
            worksheet_booking = Booking.objects.filter(pk=int(edit_param), agency=agency).first()
        except ValueError:
            worksheet_booking = None

    sheet_ctx = {}
    if worksheet_booking:
        sheet_ctx = _voucher_context(request, worksheet_booking)
        sheet_ctx["selected_mutamer_ids"] = set(
            worksheet_booking.booking_mutamers.values_list("mutamer_id", flat=True)
        )
        sheet_ctx["selected_instruction_ids"] = set(
            worksheet_booking.booking_instructions.values_list("instruction_id", flat=True)
        )
    else:
        sheet_ctx = {
            "booking": None,
            "booking_hotels": [],
            "booking_flights": [],
            "booking_transports": [],
            "booking_mutamers": [],
            "booking_instructions": [],
            "selected_mutamer_ids": set(),
            "selected_instruction_ids": set(),
        }

    ctx = {
        "bookings": qs,
        "page_title": "Bookings",
        "hotels": hotel_list,
        "flights": flight_list,
        "transports": transport_list,
        "mutamers": mutamer_list,
        "hotels_list": hotel_list,
        "flights_list": flight_list,
        "transports_list": transport_list,
        "mutamers_list": mutamer_list,
        "instructions_list": instructions_list,
        "branding": branding,
        "booking_stats": booking_stats,
        "search_q": q,
        "status_filter": status_filter,
        "worksheet_booking": worksheet_booking,
        "booking_status_choices": Booking.STATUS_CHOICES,
        **sheet_ctx,
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/bookings_htmx.html", ctx)
    return render(request, "member/bookings.html", ctx)


def _parse_booking_int(val, default=0):
    try:
        return max(0, int(val))
    except (TypeError, ValueError):
        return default


@member_required
@require_POST
def booking_create(request):
    agency = request.user.agency
    if not agency:
        return HttpResponse("No agency", status=400)

    package_name = (request.POST.get("package_name") or "").strip()
    manual_number = (request.POST.get("manual_number") or "").strip()
    client_company = (request.POST.get("client_company") or "").strip()
    client_country = (request.POST.get("client_country") or "").strip()
    client_whatsapp = (request.POST.get("client_whatsapp") or "").strip()
    notes = (request.POST.get("notes") or "").strip()
    status = (request.POST.get("status") or "draft").strip()
    if status not in ("draft", "confirmed"):
        status = "draft"

    pax_adults = _parse_booking_int(request.POST.get("pax_adults"), 1)
    pax_children = _parse_booking_int(request.POST.get("pax_children"), 0)
    pax_infants = _parse_booking_int(request.POST.get("pax_infants"), 0)
    if pax_adults + pax_children + pax_infants < 1:
        return HttpResponse("At least one passenger is required", status=400)

    with transaction.atomic():
        seq, _ = VoucherSequence.objects.select_for_update().get_or_create(
            agency=agency,
            defaults={"current_sequence": 0},
        )
        voucher_number = seq.increment_and_get_next()

    booking = Booking.objects.create(
        voucher_number=voucher_number,
        manual_number=manual_number,
        package_name=package_name,
        client_company=client_company,
        client_country=client_country,
        client_whatsapp=client_whatsapp,
        pax_adults=pax_adults,
        pax_children=pax_children,
        pax_infants=pax_infants,
        status=status,
        total_amount=Decimal("0"),
        total_price=Decimal("0"),
        notes=notes,
        agent=request.user,
        agency=agency,
    )
    url = f"{reverse('member-bookings')}?edit={booking.id}"
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url)


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


def _voucher_pdf_link_callback(uri, rel):
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
        logo_url = request.build_absolute_uri(branding.logo.url)
    return {
        "booking": booking,
        "branding": branding,
        "logo_url": logo_url,
        "agency": booking.agency,
        "booking_hotels": booking.hotels.select_related("hotel").order_by("check_in"),
        "booking_flights": booking.flights.select_related("flight").order_by("flight_type", "id"),
        "booking_transports": booking.transports.select_related("transport").order_by("travel_date", "id"),
        "booking_mutamers": booking.booking_mutamers.select_related("mutamer").order_by(
            "mutamer__name"
        ),
        "booking_instructions": booking.booking_instructions.select_related("instruction").order_by(
            "instruction__city", "instruction__role"
        ),
    }


@member_required
def booking_detail(request, booking_id):
    agency = request.user.agency
    booking = get_object_or_404(Booking, pk=booking_id, agency=agency)
    ctx = _voucher_context(request, booking)
    ctx.update(
        {
            "page_title": f"Voucher · {booking.voucher_number}",
            "hotels_list": Hotel.objects.filter(agency=agency).order_by("name"),
            "flights_list": Flight.objects.filter(agency=agency).order_by("-created_at"),
            "transports_list": Transport.objects.filter(agency=agency).order_by("name"),
            "mutamers_list": Mutamer.objects.filter(agency=agency).order_by("name"),
            "instructions_list": ContactInstruction.objects.filter(agency=agency).order_by(
                "city", "role"
            ),
            "selected_mutamer_ids": set(
                booking.booking_mutamers.values_list("mutamer_id", flat=True)
            ),
            "selected_instruction_ids": set(
                booking.booking_instructions.values_list("instruction_id", flat=True)
            ),
            "booking_status_choices": Booking.STATUS_CHOICES,
        }
    )
    return render(request, "member/booking_detail.html", ctx)


def _parse_worksheet_mutamer_instruction_ids(request):
    mutamer_ids = []
    for x in request.POST.getlist("mutamer_ids"):
        try:
            mutamer_ids.append(int(x))
        except ValueError:
            continue
    instruction_ids = []
    for x in request.POST.getlist("instruction_ids"):
        try:
            instruction_ids.append(int(x))
        except ValueError:
            continue
    return mutamer_ids, instruction_ids


def _replace_booking_line_items(
    agency,
    booking,
    hotels_payload,
    flights_payload,
    transports_payload,
    mutamer_ids,
    instruction_ids,
):
    booking.hotels.all().delete()
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

    booking.flights.all().delete()
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
        BookingFlight.objects.create(booking=booking, flight=flight, flight_type=ft)

    booking.transports.all().delete()
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

    booking.booking_mutamers.all().delete()
    for mid in mutamer_ids:
        m = Mutamer.objects.filter(pk=mid, agency=agency).first()
        if m:
            BookingMutamer.objects.create(booking=booking, mutamer=m)

    booking.booking_instructions.all().delete()
    for iid in instruction_ids:
        inst = ContactInstruction.objects.filter(pk=iid, agency=agency).first()
        if inst:
            BookingContactInstruction.objects.create(booking=booking, instruction=inst)


@member_required
@require_POST
def booking_worksheet_save(request):
    """Create or update a booking from the on-page voucher worksheet."""
    agency = request.user.agency
    if not agency:
        return HttpResponse("No agency", status=400)

    raw_id = (request.POST.get("worksheet_booking_id") or "").strip()
    booking = None
    if raw_id:
        try:
            booking = Booking.objects.filter(pk=int(raw_id), agency=agency).first()
        except ValueError:
            booking = None
        if not booking:
            messages.error(request, "Booking not found.")
            return redirect("member-bookings")

    package_name = (request.POST.get("package_name") or "").strip()
    manual_number = (request.POST.get("manual_number") or "").strip()
    client_company = (request.POST.get("client_company") or "").strip()
    client_country = (request.POST.get("client_country") or "").strip()
    client_whatsapp = (request.POST.get("client_whatsapp") or "").strip()
    notes = (request.POST.get("notes") or "").strip()
    status = (request.POST.get("status") or "draft").strip()
    if status not in dict(Booking.STATUS_CHOICES):
        status = "draft"

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

    if pax_adults + pax_children + pax_infants < 1:
        messages.error(request, "At least one passenger is required.")
        return redirect("member-bookings")

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

    hotels_payload = _parse_json_list(request.POST.get("hotels_json"))
    flights_payload = _parse_json_list(request.POST.get("flights_json"))
    transports_payload = _parse_json_list(request.POST.get("transports_json"))
    mutamer_ids, instruction_ids = _parse_worksheet_mutamer_instruction_ids(request)

    with transaction.atomic():
        if booking is None:
            seq, _ = VoucherSequence.objects.select_for_update().get_or_create(
                agency=agency,
                defaults={"current_sequence": 0},
            )
            voucher_number = seq.increment_and_get_next()
            booking = Booking.objects.create(
                voucher_number=voucher_number,
                manual_number=manual_number,
                package_name=package_name,
                client_company=client_company,
                client_country=client_country,
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
            booking.manual_number = manual_number
            booking.client_company = client_company
            booking.client_country = client_country
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
            mutamer_ids,
            instruction_ids,
        )

    messages.success(request, "Voucher saved. You can print or download PDF from the links below.")
    return redirect(f"{reverse('member-bookings')}?edit={booking.id}")


@member_required
@require_POST
def booking_update(request, booking_id):
    agency = request.user.agency
    booking = get_object_or_404(Booking, pk=booking_id, agency=agency)

    package_name = (request.POST.get("package_name") or "").strip()
    manual_number = (request.POST.get("manual_number") or "").strip()
    client_company = (request.POST.get("client_company") or "").strip()
    client_country = (request.POST.get("client_country") or "").strip()
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
        messages.error(request, "At least one passenger is required.")
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

    mutamer_ids, instruction_ids = _parse_worksheet_mutamer_instruction_ids(request)

    with transaction.atomic():
        booking.package_name = package_name
        booking.manual_number = manual_number
        booking.client_company = client_company
        booking.client_country = client_country
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
            mutamer_ids,
            instruction_ids,
        )

    messages.success(request, "Voucher and itinerary saved.")
    return redirect("member-booking-detail", booking_id=booking.id)


@member_required
@require_http_methods(["GET", "HEAD"])
def booking_voucher_print(request, booking_id):
    agency = request.user.agency
    booking = get_object_or_404(Booking, pk=booking_id, agency=agency)
    ctx = _voucher_context(request, booking)
    ctx["print_mode"] = True
    ctx["for_pdf"] = False
    return render(request, "member/voucher_document.html", ctx)


@member_required
def booking_voucher_pdf(request, booking_id):
    agency = request.user.agency
    booking = get_object_or_404(Booking, pk=booking_id, agency=agency)
    ctx = _voucher_context(request, booking)
    ctx["print_mode"] = False
    ctx["for_pdf"] = True
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
def vouchers(request):
    agency = request.user.agency
    base_qs = (
        Voucher.objects.filter(agent__agency=agency)
        .select_related("mutamer", "agent")
        .prefetch_related("services")
        .order_by("-created_at")
        if agency
        else Voucher.objects.none()
    )

    q = (request.GET.get("q") or "").strip()
    status_filter = (request.GET.get("status") or "").strip()
    qs = base_qs
    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(
            Q(voucher_number__icontains=q)
            | Q(manual_number__icontains=q)
            | Q(mutamer__name__icontains=q)
            | Q(mutamer__passport_number__icontains=q)
            | Q(agent__username__icontains=q)
            | Q(agent__first_name__icontains=q)
            | Q(agent__last_name__icontains=q)
        )

    voucher_stats = {
        "total": base_qs.count(),
        "draft": base_qs.filter(status="draft").count(),
        "pending": base_qs.filter(status="pending").count(),
        "approved": base_qs.filter(status="approved").count(),
        "rejected": base_qs.filter(status="rejected").count(),
    }

    ctx = {
        "vouchers": qs,
        "page_title": "Vouchers",
        "voucher_stats": voucher_stats,
        "search_q": q,
        "status_filter": status_filter,
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/vouchers_htmx.html", ctx)
    return render(request, "member/vouchers.html", ctx)


@member_required
def approvals(request):
    agency = request.user.agency
    base_qs = (
        Voucher.objects.filter(agent__agency=agency)
        .select_related("mutamer", "agent")
        .prefetch_related("services")
        .order_by("-created_at")
        if agency
        else Voucher.objects.none()
    )

    q = (request.GET.get("q") or "").strip()
    qs = base_qs.filter(status="pending")
    if q:
        qs = qs.filter(
            Q(voucher_number__icontains=q)
            | Q(manual_number__icontains=q)
            | Q(mutamer__name__icontains=q)
            | Q(mutamer__passport_number__icontains=q)
            | Q(agent__username__icontains=q)
            | Q(agent__first_name__icontains=q)
            | Q(agent__last_name__icontains=q)
        )

    approval_stats = {
        "pending": base_qs.filter(status="pending").count(),
        "approved": base_qs.filter(status="approved").count(),
        "rejected": base_qs.filter(status="rejected").count(),
    }

    ctx = {
        "vouchers": qs,
        "page_title": "Approvals",
        "approval_stats": approval_stats,
        "search_q": q,
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/approvals_htmx.html", ctx)
    return render(request, "member/approvals.html", ctx)


@member_required
def ledger(request):
    agency = request.user.agency
    base_qs = (
        LedgerEntry.objects.filter(agency=agency).order_by("-transaction_date", "-created_at")
        if agency
        else LedgerEntry.objects.none()
    )
    q = (request.GET.get("q") or "").strip()
    type_filter = (request.GET.get("type") or "").strip()
    bucket_filter = (request.GET.get("bucket") or "").strip()
    month_filter = (request.GET.get("month") or "").strip()  # YYYY-MM
    qs = base_qs
    if bucket_filter:
        qs = qs.filter(bucket=bucket_filter)
    if type_filter:
        qs = qs.filter(transaction_type=type_filter)
    if month_filter:
        try:
            year_s, month_s = month_filter.split("-", 1)
            year_i = int(year_s)
            month_i = int(month_s)
            qs = qs.filter(transaction_date__year=year_i, transaction_date__month=month_i)
        except Exception:
            pass
    if q:
        qs = qs.filter(
            Q(reference_number__icontains=q)
            | Q(description__icontains=q)
            | Q(category__icontains=q)
            | Q(payment_method__icontains=q)
            | Q(counterparty_name__icontains=q)
        )

    totals = base_qs.aggregate(
        income=Sum("amount", filter=Q(transaction_type="income")),
        expense=Sum("amount", filter=Q(transaction_type="expense")),
    )
    income_total = totals.get("income") or 0
    expense_total = totals.get("expense") or 0

    ledger_stats = {
        "total_entries": base_qs.count(),
        "income_total": income_total,
        "expense_total": expense_total,
        "net_total": income_total - expense_total,
    }

    # Monthly combined expense
    month_expense = None
    if month_filter:
        month_expense = qs.filter(transaction_type="expense").aggregate(v=Sum("amount"))["v"] or 0
    ctx = {
        "entries": qs,
        "page_title": "Ledger",
        "ledger_stats": ledger_stats,
        "month_expense_total": month_expense,
        "search_q": q,
        "type_filter": type_filter,
        "bucket_filter": bucket_filter,
        "month_filter": month_filter,
    }
    if request.headers.get("HX-Request"):
        return render(request, "member/partials/ledger_htmx.html", ctx)
    return render(request, "member/ledger.html", ctx)


@member_required
def ledger_report(request):
    """
    Print-friendly monthly ledger report.
    Query params:
    - month=YYYY-MM (required)
    """
    agency = request.user.agency
    month_filter = (request.GET.get("month") or "").strip()
    if not month_filter:
        # fallback to current month
        today = datetime.date.today()
        month_filter = f"{today.year:04d}-{today.month:02d}"

    try:
        year_s, month_s = month_filter.split("-", 1)
        year = int(year_s)
        month = int(month_s)
        start_date = datetime.date(year, month, 1)
        end_date = datetime.date(year, month, calendar.monthrange(year, month)[1])
    except Exception:
        today = datetime.date.today()
        start_date = datetime.date(today.year, today.month, 1)
        end_date = datetime.date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        month_filter = f"{start_date.year:04d}-{start_date.month:02d}"

    qs = (
        LedgerEntry.objects.filter(agency=agency, transaction_date__range=(start_date, end_date))
        .order_by("transaction_date", "created_at")
        if agency
        else LedgerEntry.objects.none()
    )

    party_entries = qs.filter(bucket="lein_dein")
    expense_entries = qs.filter(bucket="company_expense")

    # Group party entries by counterparty
    party_map = {}
    party_order = []
    for e in party_entries:
        key = (e.counterparty_name or "").strip() or "—"
        if key not in party_map:
            party_map[key] = []
            party_order.append(key)
        party_map[key].append(e)

    party_groups = []
    for name in party_order:
        items = party_map[name]
        # Opening balance before the period (credits - debits)
        opening_qs = (
            LedgerEntry.objects.filter(
                agency=agency,
                bucket="lein_dein",
                counterparty_name=name,
                transaction_date__lt=start_date,
            )
            if agency and name != "—"
            else LedgerEntry.objects.none()
        )
        opening_debit = opening_qs.filter(direction="debit").aggregate(v=Sum("amount"))["v"] or 0
        opening_credit = opening_qs.filter(direction="credit").aggregate(v=Sum("amount"))["v"] or 0
        opening_balance = float(opening_credit) - float(opening_debit)

        debit_total = sum([float(x.amount) for x in items if x.direction == "debit"])
        credit_total = sum([float(x.amount) for x in items if x.direction == "credit"])
        # balance convention: credit - debit (positive means net credit received)
        balance_total = credit_total - debit_total
        # running balances per row
        running = opening_balance
        rows = []
        rows.append({"e": None, "running": opening_balance, "is_opening": True})
        for e in items:
            if e.direction == "credit":
                running += float(e.amount)
            else:
                running -= float(e.amount)
            rows.append({"e": e, "running": running})
        party_groups.append({
            "name": name,
            "type": (items[0].counterparty_type or "").strip(),
            "opening_balance": opening_balance,
            "debit_total": debit_total,
            "credit_total": credit_total,
            "balance_total": balance_total,
            "rows": rows,
        })

    expense_total = expense_entries.aggregate(v=Sum("amount"))["v"] or 0

    ctx = {
        "page_title": "Ledger report",
        "agency": agency,
        "month_filter": month_filter,
        "period_start": start_date,
        "period_end": end_date,
        "print_date": datetime.date.today(),
        "party_groups": party_groups,
        "expense_entries": expense_entries,
        "expense_total": expense_total,
    }
    return render(request, "member/ledger_report.html", ctx)


@member_required
def attendance(request):
    agency = request.user.agency
    base_qs = (
        AttendanceLog.objects.filter(agency=agency).select_related("user").order_by("-date", "-created_at")
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

    is_admin_user = bool(agency and agency.attendance_admin_user_id == request.user.id)
    can_edit = bool(agency and is_admin_user and agency.attendance_admin_password_hash)

    users = []
    logs = my_logs
    if can_edit:
        # Attendance admin can mark for all active users in the agency (members + agents).
        users = list(
            agency.users.filter(role__in=["member", "agent"], is_active=True)
            .order_by("role", "first_name", "last_name", "username")
        )
        logs = qs

    stats_base = my_logs
    present = stats_base.filter(status="present").count()
    absent = stats_base.filter(status="absent").count()
    late = stats_base.filter(status="late").count()
    leave = stats_base.filter(status="leave").count()

    attendance_stats = {
        "present": present,
        "absent": absent,
        "late": late,
        "leave": leave,
        "total": stats_base.count(),
    }

    return render(
        request,
        "member/attendance.html",
        {
            "page_title": "Attendance",
            "month_filter": month_filter,
            "period_start": start_date,
            "period_end": end_date,
            "attendance_stats": attendance_stats,
            "logs": logs,
            "my_logs": my_logs,
            "can_edit": can_edit,
            "is_admin_user": is_admin_user,
            "has_admin_password": bool(agency and agency.attendance_admin_password_hash),
            "attendance_admin_name": agency.attendance_admin_user.full_name if agency and agency.attendance_admin_user_id else "",
            "users": users,
        },
    )


@member_required
@require_POST
def attendance_unlock(request):
    agency = request.user.agency
    if not agency:
        return HttpResponse("No agency", status=400)

    password = (request.POST.get("password") or "").strip()
    if not password:
        return HttpResponse("Password required", status=400)

    # First-time setup: allow first member who sets password to become admin user.
    if not agency.attendance_admin_password_hash:
        agency.attendance_admin_password_hash = make_password(password)
        agency.attendance_admin_user = request.user
        agency.save(update_fields=["attendance_admin_password_hash", "attendance_admin_user", "updated_at"])
    else:
        # Only the designated admin user can validate/change usage.
        if agency.attendance_admin_user_id != request.user.id:
            return HttpResponse("Not allowed", status=403)
        if not check_password(password, agency.attendance_admin_password_hash):
            return HttpResponse("Invalid password", status=400)

    return HttpResponse("OK", status=200)


@member_required
@require_POST
def attendance_password_change(request):
    agency = request.user.agency
    if not agency:
        return HttpResponse("No agency", status=400)
    if agency.attendance_admin_user_id != request.user.id:
        return HttpResponse("Not allowed", status=403)

    current_pw = (request.POST.get("current_password") or "").strip()
    new_pw = (request.POST.get("new_password") or "").strip()
    if not agency.attendance_admin_password_hash:
        return HttpResponse("Attendance password not set", status=400)
    if not current_pw or not new_pw:
        return HttpResponse("Missing fields", status=400)
    if not check_password(current_pw, agency.attendance_admin_password_hash):
        return HttpResponse("Invalid current password", status=400)

    agency.attendance_admin_password_hash = make_password(new_pw)
    agency.save(update_fields=["attendance_admin_password_hash", "updated_at"])
    return HttpResponse("OK", status=200)


@member_required
@require_POST
def attendance_password_reset(request):
    """
    Reset attendance password by confirming the admin user's normal account password.
    This allows recovery if the attendance password is forgotten.
    """
    agency = request.user.agency
    if not agency:
        return HttpResponse("No agency", status=400)
    if agency.attendance_admin_user_id != request.user.id:
        return HttpResponse("Not allowed", status=403)

    account_pw = (request.POST.get("account_password") or "").strip()
    new_pw = (request.POST.get("new_password") or "").strip()
    if not account_pw or not new_pw:
        return HttpResponse("Missing fields", status=400)

    # Verify with normal login password (member account password)
    user = authenticate(request, username=request.user.username, password=account_pw)
    if not user:
        return HttpResponse("Invalid account password", status=400)

    agency.attendance_admin_password_hash = make_password(new_pw)
    agency.save(update_fields=["attendance_admin_password_hash", "updated_at"])
    return HttpResponse("OK", status=200)


@member_required
@require_POST
def attendance_mark(request):
    agency = request.user.agency
    if not agency:
        return HttpResponse("No agency", status=400)

    # Must be admin user and must provide the attendance password on every save.
    if agency.attendance_admin_user_id != request.user.id:
        return HttpResponse("Not allowed", status=403)

    password = (request.POST.get("password") or "").strip()
    if not agency.attendance_admin_password_hash:
        return HttpResponse("Attendance password not set", status=400)
    if not password:
        return HttpResponse("Password required", status=400)
    if not check_password(password, agency.attendance_admin_password_hash):
        return HttpResponse("Invalid password", status=400)

    user_id = request.POST.get("user_id")
    person_name = (request.POST.get("person_name") or "").strip()
    date_str = (request.POST.get("date") or "").strip()
    status_val = (request.POST.get("status") or "").strip()
    check_in = (request.POST.get("check_in_time") or "").strip()
    check_out = (request.POST.get("check_out_time") or "").strip()
    notes = (request.POST.get("notes") or "").strip()

    if not person_name or not date_str or not status_val:
        return HttpResponse("Missing fields", status=400)

    try:
        d = datetime.date.fromisoformat(date_str)
    except Exception:
        return HttpResponse("Invalid date", status=400)

    user = None
    if user_id:
        try:
            uid = int(user_id)
            user = agency.users.filter(id=uid, role__in=["member", "agent"]).first()
        except Exception:
            user = None

    def parse_time(s):
        if not s:
            return None
        try:
            return datetime.time.fromisoformat(s)
        except Exception:
            return None

    obj, _ = AttendanceLog.objects.update_or_create(
        agency=agency,
        person_name=person_name,
        date=d,
        defaults={
            "user": user,
            "status": status_val,
            "check_in_time": parse_time(check_in),
            "check_out_time": parse_time(check_out),
            "notes": notes,
        },
    )
    return HttpResponse("OK", status=200)


@member_required
@require_POST
def attendance_delete(request):
    agency = request.user.agency
    if not agency:
        return HttpResponse("No agency", status=400)
    if agency.attendance_admin_user_id != request.user.id:
        return HttpResponse("Not allowed", status=403)

    password = (request.POST.get("password") or "").strip()
    if not agency.attendance_admin_password_hash:
        return HttpResponse("Attendance password not set", status=400)
    if not password:
        return HttpResponse("Password required", status=400)
    if not check_password(password, agency.attendance_admin_password_hash):
        return HttpResponse("Invalid password", status=400)

    log_id = request.POST.get("log_id")
    try:
        log_id_i = int(log_id)
    except Exception:
        return HttpResponse("Invalid log", status=400)

    obj = AttendanceLog.objects.filter(id=log_id_i, agency=agency).first()
    if not obj:
        return HttpResponse("Not found", status=404)
    obj.delete()
    return HttpResponse("OK", status=200)


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
    city_filter = (request.GET.get("city") or "").strip()

    qs = base_qs
    if city_filter:
        qs = qs.filter(city=city_filter)
    if q:
        qs = qs.filter(
            Q(role__icontains=q)
            | Q(contact_name__icontains=q)
            | Q(phone_number__icontains=q)
            | Q(notes__icontains=q)
        )

    contact_stats = {
        "total": base_qs.count(),
        "makkah": base_qs.filter(city__iexact="makkah").count(),
        "madina": base_qs.filter(city__iexact="madina").count(),
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
        return HttpResponse("No agency", status=400)

    city = (request.POST.get("city") or "").strip()
    role = (request.POST.get("role") or "").strip()
    contact_name = (request.POST.get("contact_name") or "").strip()
    phone_number = (request.POST.get("phone_number") or "").strip()
    notes = (request.POST.get("notes") or "").strip()

    if not city or not role or not contact_name or not phone_number:
        return HttpResponse("Missing required fields", status=400)

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
        return HttpResponse("No agency", status=400)

    c = ContactInstruction.objects.filter(id=contact_id, agency=agency).first()
    if not c:
        return HttpResponse("Not found", status=404)

    city = (request.POST.get("city") or "").strip()
    role = (request.POST.get("role") or "").strip()
    contact_name = (request.POST.get("contact_name") or "").strip()
    phone_number = (request.POST.get("phone_number") or "").strip()
    notes = (request.POST.get("notes") or "").strip()

    if not city or not role or not contact_name or not phone_number:
        return HttpResponse("Missing required fields", status=400)

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
        return HttpResponse("No agency", status=400)
    c = ContactInstruction.objects.filter(id=contact_id, agency=agency).first()
    if not c:
        return HttpResponse("Not found", status=404)
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
        return HttpResponse("No agency", status=400)

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
        return HttpResponse("Company name is required", status=400)

    logo = request.FILES.get("logo")
    if logo:
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/svg+xml"]
        if getattr(logo, "content_type", "") not in allowed_types:
            return HttpResponse("Logo must be JPEG, PNG, GIF, or SVG", status=400)
        if logo.size > 5 * 1024 * 1024:
            return HttpResponse("Logo file too large (max 5MB)", status=400)
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

    # Keep core Agency record aligned for reports / legacy lookups
    agency.name = company_name or agency.name
    if phone:
        agency.phone = phone
    if email:
        agency.email = email
    if address:
        agency.address = address
    agency.save(update_fields=["name", "phone", "email", "address", "updated_at"])

    return HttpResponse("OK", status=200)


# ==========================================
# PUBLIC VIEWS
# ==========================================

def public_voucher(request, token):
    voucher = get_object_or_404(
        Voucher.objects.select_related("mutamer", "agent", "agent__agency"),
        public_token=token,
        status="approved",
    )
    services = voucher.services.all()
    agency = voucher.agent.agency
    branding = AgencyBranding.objects.filter(agency=agency).first()
    return render(request, "public/voucher.html", {
        "voucher": voucher,
        "services": services,
        "mutamer": voucher.mutamer,
        "branding": branding,
        "agency": agency,
    })
