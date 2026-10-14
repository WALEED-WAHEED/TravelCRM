"""
Self check-in attendance: verification rules, QR codes, office hours.

A check-in is accepted only when every check the agency switched on passes:

  network   the request comes from one of the office's public IPs
  qr        the person scanned the office display's QR code within the last ~60s
  location  the phone's GPS reading is inside the office radius (and precise enough)

Field staff (airport reps, Makkah/Madina team) skip those and instead must share
a precise location, which is stored with the record. Times always come from the
server clock; staff can never type or edit them — fixes go through a correction
request that a manager approves.
"""
import datetime
import hashlib
import hmac
import math
import time
import zoneinfo
from decimal import Decimal

from django.conf import settings as django_settings
from django.db import transaction
from django.utils import timezone

from .models import AttendanceCorrection, AttendanceLog, AttendanceSettings

QR_WINDOW_SECONDS = 30
QR_GRACE_WINDOWS = 1  # also accept the previous code, so a scan near the rollover still works


# ---------------------------------------------------------------------------
# Settings / time
# ---------------------------------------------------------------------------

def get_settings(agency):
    s, created = AttendanceSettings.objects.get_or_create(agency=agency)
    if created:
        # Owners usually don't check in — don't mark them absent every day by default.
        from rbac.engine import role_level
        owners = [u for u in agency.users.filter(is_active=True) if role_level(u) >= 100]
        if owners:
            s.exempt_staff.add(*owners)
    return s


def office_tz(s):
    try:
        return zoneinfo.ZoneInfo(s.time_zone or "Asia/Karachi")
    except zoneinfo.ZoneInfoNotFoundError:
        return zoneinfo.ZoneInfo("Asia/Karachi")


def office_now(s):
    return timezone.now().astimezone(office_tz(s))


def late_cutoff(s):
    start = datetime.datetime.combine(datetime.date.today(), s.workday_start)
    return (start + datetime.timedelta(minutes=s.late_after_minutes)).time()


def status_for_arrival(s, local_time):
    return "late" if local_time > late_cutoff(s) else "present"


def tracked_staff(agency, s):
    """Active staff expected to check in (exempt users excluded)."""
    exempt = set(s.exempt_staff.values_list("id", flat=True))
    return [
        u for u in agency.users.filter(is_active=True, role__in=["member", "agent"]).select_related("custom_role")
        .order_by("first_name", "username")
        if u.id not in exempt
    ]


def is_field_staff(s, user):
    return s.field_staff.filter(pk=user.pk).exists()


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

def client_ip(request):
    """The caller's public IP. Behind N trusted reverse proxies (ATTENDANCE_TRUSTED_PROXIES),
    take the address the last trusted proxy saw; never trust X-Forwarded-For otherwise,
    or anyone could claim to be on the office network."""
    proxies = int(getattr(django_settings, "ATTENDANCE_TRUSTED_PROXIES", 0) or 0)
    if proxies > 0:
        chain = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
        if len(chain) >= proxies:
            return chain[-proxies]
    return request.META.get("REMOTE_ADDR", "")


# ---------------------------------------------------------------------------
# QR codes (rotating, HMAC-signed — only the server can mint a valid one)
# ---------------------------------------------------------------------------

def _qr_secret(s):
    return hmac.new(
        django_settings.SECRET_KEY.encode(), f"attendance-qr:{s.kiosk_token}".encode(), hashlib.sha256,
    ).digest()


def _qr_sig(s, window):
    return hmac.new(_qr_secret(s), f"{s.agency_id}:{window}".encode(), hashlib.sha256).hexdigest()[:20]


def current_window(now=None):
    return int((now if now is not None else time.time()) // QR_WINDOW_SECONDS)


def current_qr_token(s, now=None):
    w = current_window(now)
    return f"{w}.{_qr_sig(s, w)}"


def seconds_until_rotation(now=None):
    now = now if now is not None else time.time()
    return QR_WINDOW_SECONDS - int(now % QR_WINDOW_SECONDS)


def verify_qr_token(s, token, now=None):
    try:
        w_str, sig = (token or "").split(".", 1)
        w = int(w_str)
    except ValueError:
        return False
    cur = current_window(now)
    if not (cur - QR_GRACE_WINDOWS <= w <= cur):
        return False
    return hmac.compare_digest(sig, _qr_sig(s, w))


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

def distance_m(lat1, lng1, lat2, lng2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _float(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _fmt_distance(m):
    return f"{m / 1000:.1f} km" if m >= 1000 else f"{int(m)} m"


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def evaluate(s, user, ip, qr_token, lat, lng, accuracy, now=None):
    """Run the checks that apply to this user. Returns (ok, field, results, meta)."""
    lat, lng, accuracy = _float(lat), _float(lng), _float(accuracy)
    field = is_field_staff(s, user)
    results = []
    meta = {"ip": ip}
    has_location = lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180
    if has_location:
        meta.update({"lat": round(lat, 6), "lng": round(lng, 6), "accuracy": round(accuracy or 0)})

    def add(key, label, ok, message):
        results.append({"key": key, "label": label, "ok": ok, "message": message})

    if field:
        if not has_location:
            add("location", "Location", False, "Allow location access — field check-in records where you are.")
        elif accuracy is None or accuracy > s.max_accuracy_m:
            add("location", "Location", False,
                f"Location is too vague (±{int(accuracy or 0)} m). Move outdoors or turn on GPS and try again.")
        else:
            add("location", "Location", True, f"Location recorded (±{int(accuracy)} m).")
    else:
        if s.require_network:
            ok = bool(ip) and ip in (s.office_ips or [])
            add("network", "Office network", ok,
                "Connected to the office network." if ok else "You must be on the office Wi-Fi to check in.")
        if s.require_qr:
            ok = verify_qr_token(s, qr_token, now)
            add("qr", "Office QR code", ok,
                "QR code verified." if ok else
                ("Scan the QR code on the office display." if not qr_token else
                 "That QR code has expired — scan the one on screen now."))
        if s.require_location:
            if s.office_lat is None or s.office_lng is None:
                add("location", "Office location", False, "The office location hasn't been set up yet — ask your manager.")
            elif not has_location:
                add("location", "Office location", False, "Allow location access so we can confirm you're at the office.")
            elif accuracy is None or accuracy > s.max_accuracy_m:
                add("location", "Office location", False,
                    f"Location is too vague (±{int(accuracy or 0)} m). Turn on GPS and try again.")
            else:
                d = distance_m(lat, lng, float(s.office_lat), float(s.office_lng))
                meta["distance_m"] = round(d)
                ok = d <= s.radius_m
                add("location", "Office location", ok,
                    f"At the office ({_fmt_distance(d)} away)." if ok else
                    f"You're {_fmt_distance(d)} from the office — check in when you arrive.")
    meta["checks"] = {r["key"]: r["ok"] for r in results}
    meta["mode"] = "field" if field else "office"
    return all(r["ok"] for r in results), field, results, meta


def todays_log(agency, user, day):
    return (
        AttendanceLog.objects.filter(agency=agency, date=day, user=user).first()
        or AttendanceLog.objects.filter(agency=agency, date=day, person_name=user.full_name, user__isnull=True).first()
    )


def _hours(start_at, end_at):
    return (Decimal((end_at - start_at).total_seconds()) / Decimal(3600)).quantize(Decimal("0.01"))


@transaction.atomic
def check(agency, user, action, ip, qr_token, lat, lng, accuracy):
    """Perform a check-in or check-out. Returns a dict for the JSON response."""
    s = get_settings(agency)
    ok, field, results, meta = evaluate(s, user, ip, qr_token, lat, lng, accuracy)
    now_local = office_now(s)
    day = now_local.date()
    log = todays_log(agency, user, day)
    response = {"ok": False, "results": results, "field": field}

    if action == "in":
        if log and log.check_in_at:
            response["error"] = f"You already checked in today at {log.check_in_at.astimezone(office_tz(s)):%I:%M %p}."
            return response
        if not ok:
            response["error"] = "Check-in blocked — see the reason below."
            return response
        status = status_for_arrival(s, now_local.time())
        fields = {
            "user": user, "person_name": user.full_name, "status": status,
            "source": "field" if field else "self",
            "check_in_at": timezone.now(), "check_in_time": now_local.time().replace(microsecond=0),
            "check_in_meta": meta,
        }
        if log:  # e.g. an automatic "absent" row created earlier — arriving overrides it
            for k, v in fields.items():
                setattr(log, k, v)
            log.save()
        else:
            log = AttendanceLog.objects.create(agency=agency, date=day, **fields)
        response.update({"ok": True, "status": status, "time": f"{now_local:%I:%M %p}",
                         "message": "Checked in — late." if status == "late" else "Checked in — on time."})
        return response

    if action == "out":
        if not log or not log.check_in_at:
            response["error"] = "You haven't checked in today."
            return response
        if not ok:
            response["error"] = "Check-out blocked — see the reason below."
            return response
        log.check_out_at = timezone.now()
        log.check_out_time = now_local.time().replace(microsecond=0)
        log.check_out_meta = meta
        log.work_hours = _hours(log.check_in_at, log.check_out_at)
        log.save()
        response.update({"ok": True, "status": log.status, "time": f"{now_local:%I:%M %p}",
                         "message": f"Checked out — {log.work_hours} hours today."})
        return response

    response["error"] = "Unknown action."
    return response


# ---------------------------------------------------------------------------
# Automatic absences, board, summary
# ---------------------------------------------------------------------------

def ensure_absences(agency, s, start, end):
    """Persist 'absent' for tracked staff with no record on past work days (and today
    once the absent cut-off has passed). Never earlier than when settings were created,
    so turning the feature on doesn't backfill months of absences."""
    now_local = office_now(s)
    today = now_local.date()
    first = max(start, timezone.localtime(s.created_at, office_tz(s)).date())
    last = min(end, today if now_local.time() >= s.absent_after else today - datetime.timedelta(days=1))
    if first > last:
        return 0
    staff = tracked_staff(agency, s)
    existing = set(
        AttendanceLog.objects.filter(agency=agency, date__range=(first, last)).values_list("user_id", "date")
    )
    # Same key as the table's unique constraint (agency, person_name, date), so rows that already exist are
    # skipped here instead of being re-fetched one by one by get_or_create on every page load.
    names = set(
        AttendanceLog.objects.filter(agency=agency, date__range=(first, last)).values_list("person_name", "date")
    )
    created = 0
    d = first
    while d <= last:
        if d.weekday() in (s.work_days or []):
            for u in staff:
                if (u.id, d) in existing or (u.full_name, d) in names:
                    continue
                _log, made = AttendanceLog.objects.get_or_create(
                    agency=agency, person_name=u.full_name, date=d,
                    defaults={"user": u, "status": "absent", "source": "auto",
                              "notes": "No check-in by the absent cut-off."},
                )
                created += made
        d += datetime.timedelta(days=1)
    return created


def board(agency, s, day):
    """One row per tracked staff member for `day`, including people not in yet."""
    now_local = office_now(s)
    logs = {lg.user_id: lg for lg in AttendanceLog.objects.filter(agency=agency, date=day).select_related("user")}
    by_name = {lg.person_name: lg for lg in logs.values()}
    field_ids = set(s.field_staff.values_list("id", flat=True))
    rows = []
    work_day = day.weekday() in (s.work_days or [])
    for u in tracked_staff(agency, s):
        lg = logs.get(u.id) or by_name.get(u.full_name)
        if not lg and not work_day:
            continue  # day off: nobody is expected, so nobody is "absent" or "not in"
        if lg:
            state = lg.status
        elif day < now_local.date() or (day == now_local.date() and now_local.time() >= s.absent_after):
            state = "absent"
        else:
            state = "not_in"
        rows.append({"user": u, "log": lg, "state": state, "field": u.id in field_ids})
    order = {"late": 0, "absent": 1, "not_in": 2, "present": 3, "leave": 4}
    rows.sort(key=lambda r: (order.get(r["state"], 9), r["user"].full_name.lower()))
    return rows


@transaction.atomic
def review_correction(correction, approve, reviewer, note=""):
    correction.status = "approved" if approve else "rejected"
    correction.reviewed_by = reviewer
    correction.reviewed_at = timezone.now()
    correction.review_note = note[:300]
    correction.save()
    if not approve:
        return None
    u = correction.user
    log = todays_log(correction.agency, u, correction.date)
    fields = {
        "status": correction.requested_status, "source": "correction",
        "notes": f"Correction approved by {reviewer.full_name}: {correction.reason}"[:1000],
    }
    if correction.requested_check_in:
        fields["check_in_time"] = correction.requested_check_in
    if correction.requested_check_out:
        fields["check_out_time"] = correction.requested_check_out
    if log:
        for k, v in fields.items():
            setattr(log, k, v)
        log.save()
    else:
        log = AttendanceLog.objects.create(
            agency=correction.agency, user=u, person_name=u.full_name, date=correction.date, **fields,
        )
    return log


def pending_corrections(agency):
    return AttendanceCorrection.objects.filter(agency=agency, status="pending").select_related("user", "user__custom_role")
