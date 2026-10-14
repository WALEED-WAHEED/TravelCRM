"""Self check-in attendance pages. Rules live in member/attendance.py."""
import datetime
from io import BytesIO

from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from rbac.decorators import permission_required
from utils.tenancy import apply_db_session_context, tenant_context

from . import attendance as att
from .models import AttendanceCorrection, AttendanceLog, AttendanceSettings


def _month_bounds(day):
    start = day.replace(day=1)
    nxt = (start + datetime.timedelta(days=32)).replace(day=1)
    return start, nxt - datetime.timedelta(days=1)


# ---------------------------------------------------------------------------
# Staff: my attendance + check in/out
# ---------------------------------------------------------------------------

@permission_required("attendance", "view")
def my_attendance(request, qr_token=""):
    agency = request.user.agency
    if not agency:
        return redirect("root")
    s = att.get_settings(agency)
    now_local = att.office_now(s)
    start, end = _month_bounds(now_local.date())
    att.ensure_absences(agency, s, start, end)
    field = att.is_field_staff(s, request.user)
    logs = AttendanceLog.objects.filter(agency=agency, user=request.user, date__range=(start, end)).order_by("-date")
    required = []
    if field:
        required = [_("Your location (field staff)")]
    else:
        if s.require_network:
            required.append(_("Office Wi-Fi"))
        if s.require_qr:
            required.append(_("Office QR code"))
        if s.require_location:
            required.append(_("Being at the office (location)"))
    return render(request, "member/attendance_me.html", {
        "page_title": "My attendance",
        "settings_obj": s,
        "today": now_local.date(),
        "today_log": att.todays_log(agency, request.user, now_local.date()),
        "logs": logs,
        "summary": {k: logs.filter(status=k).count() for k in ("present", "late", "absent", "leave")},
        "field": field,
        "required": required,
        "needs_location": field or s.require_location,
        "needs_qr": (not field) and s.require_qr,
        "qr_token": qr_token,
        "late_cutoff": att.late_cutoff(s),
        "corrections": AttendanceCorrection.objects.filter(agency=agency, user=request.user)[:10],
        "status_choices": AttendanceLog.STATUS_CHOICES,
    })


@permission_required("attendance", "view")
def attendance_scan(request):
    """Where the office display's QR code points. Opens My attendance with the code attached."""
    return my_attendance(request, qr_token=(request.GET.get("t") or "").strip())


@permission_required("attendance", "view")
@require_POST
def attendance_check(request):
    agency = request.user.agency
    if not agency:
        return JsonResponse({"ok": False, "error": "No agency"}, status=400)
    result = att.check(
        agency, request.user,
        action=request.POST.get("action"),
        ip=att.client_ip(request),
        qr_token=(request.POST.get("qr") or "").strip(),
        lat=request.POST.get("lat"), lng=request.POST.get("lng"), accuracy=request.POST.get("accuracy"),
    )
    return JsonResponse(result, status=200 if result["ok"] else 400)


@permission_required("attendance", "view")
@require_POST
def attendance_correction_request(request):
    agency = request.user.agency
    try:
        day = datetime.date.fromisoformat(request.POST.get("date", ""))
    except ValueError:
        messages.error(request, _("Choose a valid date."))
        return redirect("attendance-me")
    status = request.POST.get("requested_status", "")
    reason = (request.POST.get("reason") or "").strip()
    if status not in dict(AttendanceLog.STATUS_CHOICES) or not reason:
        messages.error(request, _("Choose a status and explain the reason."))
        return redirect("attendance-me")
    if day > timezone.localdate():
        messages.error(request, _("Corrections can only be requested for today or earlier."))
        return redirect("attendance-me")

    def t(name):
        try:
            return datetime.time.fromisoformat(request.POST.get(name, ""))
        except ValueError:
            return None

    AttendanceCorrection.objects.create(
        agency=agency, user=request.user, date=day, requested_status=status,
        requested_check_in=t("requested_check_in"), requested_check_out=t("requested_check_out"),
        reason=reason[:1000],
    )
    messages.success(request, _("Correction request sent to your manager."))
    return redirect("attendance-me")


# ---------------------------------------------------------------------------
# Office display (kiosk) — no login; the secret token in the URL is the key
# ---------------------------------------------------------------------------

def _settings_for_kiosk(token):
    # No logged-in user here, so no tenant context: look the token up with an
    # explicit, narrow bypass (ORM + Postgres RLS), then scope to that agency.
    with tenant_context(bypass=True):
        apply_db_session_context(True, None)
        s = AttendanceSettings.all_tenants.select_related("agency").filter(kiosk_token=token).first()
    apply_db_session_context(False, s.agency_id if s else None)
    if not s or not s.require_qr:
        raise Http404
    return s


@never_cache
def attendance_display(request, token):
    s = _settings_for_kiosk(token)
    return render(request, "member/attendance_display.html", {
        "agency": s.agency,
        "token": token,
        "window": att.QR_WINDOW_SECONDS,
    })


@never_cache
def attendance_display_qr(request, token):
    """Current QR code as SVG + seconds until it rotates (header), polled by the display page."""
    import qrcode
    import qrcode.image.svg

    s = _settings_for_kiosk(token)
    url = request.build_absolute_uri(reverse("attendance-scan")) + "?t=" + att.current_qr_token(s)
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2)
    buf = BytesIO()
    img.save(buf)
    response = HttpResponse(buf.getvalue(), content_type="image/svg+xml")
    response["X-Rotates-In"] = str(att.seconds_until_rotation())
    return response


# ---------------------------------------------------------------------------
# Manager: settings + corrections
# ---------------------------------------------------------------------------

@permission_required("attendance", "manage")
def attendance_settings(request):
    agency = request.user.agency
    s = att.get_settings(agency)
    staff = list(agency.users.filter(is_active=True, role__in=["member", "agent"]).order_by("first_name", "username"))
    current_ip = att.client_ip(request)

    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "add_ip":
            if current_ip and current_ip not in s.office_ips:
                s.office_ips = list(s.office_ips) + [current_ip]
                s.save(update_fields=["office_ips", "updated_at"])
            messages.success(request, _("Saved %(ip)s as an office network.") % {"ip": current_ip})
            return redirect("attendance-settings")
        if action == "remove_ip":
            ip = request.POST.get("ip", "")
            s.office_ips = [x for x in s.office_ips if x != ip]
            s.save(update_fields=["office_ips", "updated_at"])
            return redirect("attendance-settings")
        if action == "rotate_kiosk":
            s.kiosk_token = AttendanceSettings._meta.get_field("kiosk_token").default()
            s.save(update_fields=["kiosk_token", "updated_at"])
            messages.success(request, _("New office display link created. Open it on the office screen — the old link no longer works."))
            return redirect("attendance-settings")

        s.require_network = request.POST.get("require_network") == "on"
        s.require_qr = request.POST.get("require_qr") == "on"
        s.require_location = request.POST.get("require_location") == "on"

        def num(name, default, lo, hi):
            try:
                return max(lo, min(hi, int(request.POST.get(name, default))))
            except (TypeError, ValueError):
                return default

        s.radius_m = num("radius_m", s.radius_m, 20, 5000)
        s.max_accuracy_m = num("max_accuracy_m", s.max_accuracy_m, 10, 2000)
        s.late_after_minutes = num("late_after_minutes", s.late_after_minutes, 0, 240)
        for name in ("office_lat", "office_lng"):
            raw = (request.POST.get(name) or "").strip()
            try:
                setattr(s, name, round(float(raw), 6) if raw else None)
            except ValueError:
                pass
        for name in ("workday_start", "absent_after", "workday_end"):
            try:
                setattr(s, name, datetime.time.fromisoformat(request.POST.get(name, "")))
            except ValueError:
                pass
        s.work_days = sorted({int(d) for d in request.POST.getlist("work_days") if d.isdigit() and int(d) < 7})
        tz = (request.POST.get("time_zone") or "").strip()
        if tz:
            try:
                att.zoneinfo.ZoneInfo(tz)
                s.time_zone = tz
            except (att.zoneinfo.ZoneInfoNotFoundError, ValueError):
                messages.error(request, _("Unknown timezone %(tz)s — kept %(old)s.") % {"tz": tz, "old": s.time_zone})
        s.save()
        ids = {u.id for u in staff}
        s.field_staff.set([int(i) for i in request.POST.getlist("field_staff") if i.isdigit() and int(i) in ids])
        s.exempt_staff.set([int(i) for i in request.POST.getlist("exempt_staff") if i.isdigit() and int(i) in ids])
        messages.success(request, _("Attendance settings saved."))
        return redirect("attendance-settings")

    return render(request, "member/attendance_settings.html", {
        "page_title": "Attendance settings",
        "s": s,
        "staff": staff,
        "field_ids": set(s.field_staff.values_list("id", flat=True)),
        "exempt_ids": set(s.exempt_staff.values_list("id", flat=True)),
        "current_ip": current_ip,
        "display_url": request.build_absolute_uri(reverse("attendance-display", args=[s.kiosk_token])),
        "weekdays": [(0, _("Mon")), (1, _("Tue")), (2, _("Wed")), (3, _("Thu")), (4, _("Fri")), (5, _("Sat")), (6, _("Sun"))],
        "no_checks": not (s.require_network or s.require_qr or s.require_location),
        # Zones a Pakistan/Gulf travel agency realistically uses, plus whatever is saved.
        "time_zones": sorted({"Asia/Karachi", "Asia/Riyadh", "Asia/Dubai", "Asia/Qatar", "Asia/Kuwait",
                              "Asia/Bahrain", "Asia/Muscat", "Asia/Kolkata", "Asia/Dhaka", "Europe/London",
                              "Europe/Istanbul", "America/New_York", "UTC", s.time_zone}),
    })


@permission_required("attendance", "manage")
@require_POST
def attendance_correction_review(request, correction_id):
    c = get_object_or_404(AttendanceCorrection, pk=correction_id, agency=request.user.agency, status="pending")
    approve = request.POST.get("decision") == "approve"
    att.review_correction(c, approve, request.user, request.POST.get("note", ""))
    messages.success(request, _("Correction approved.") if approve else _("Correction rejected."))
    return redirect(reverse("member-attendance") + "#corrections")
