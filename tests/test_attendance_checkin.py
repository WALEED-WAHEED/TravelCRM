"""Self check-in attendance: QR codes, network/GPS checks, office hours, corrections, kiosk."""
import datetime
import zoneinfo

import pytest
from django.test import Client, RequestFactory, override_settings

from member import attendance as att
from utils.tenancy import tenant_context

KHI = zoneinfo.ZoneInfo("Asia/Karachi")
OFFICE = (31.520400, 74.358700)  # Lahore


@pytest.fixture
def agent_a(agency_a):
    from accounts.models import User
    with tenant_context(bypass=True):
        return User.objects.create_user(username="agent_a", password="TestPass123!", role="agent",
                                        agency=agency_a, first_name="Ali", last_name="Khan")


@pytest.fixture
def agent_client(agent_a):
    c = Client()
    c.force_login(agent_a)
    return c


@pytest.fixture
def settings_a(agency_a):
    with tenant_context(agency_id=agency_a.id):
        s = att.get_settings(agency_a)
        s.office_ips = ["203.0.113.7"]
        s.office_lat, s.office_lng = OFFICE
        s.save()
        return s


def _at(monkeypatch, hour, minute=0, day=datetime.date(2026, 10, 7)):  # a Wednesday
    fixed = datetime.datetime.combine(day, datetime.time(hour, minute), tzinfo=KHI)
    monkeypatch.setattr(att, "office_now", lambda s: fixed)
    return fixed


# --- QR -------------------------------------------------------------------------

def test_qr_token_rotates_and_is_signed(settings_a, agency_b):
    now = 1_800_000_000
    tok = att.current_qr_token(settings_a, now)
    assert att.verify_qr_token(settings_a, tok, now)
    assert att.verify_qr_token(settings_a, tok, now + att.QR_WINDOW_SECONDS)       # previous window: grace
    assert not att.verify_qr_token(settings_a, tok, now + 2 * att.QR_WINDOW_SECONDS + 1)  # too old
    w, sig = tok.split(".")
    assert not att.verify_qr_token(settings_a, f"{w}.{'0' * len(sig)}", now)      # forged
    assert not att.verify_qr_token(settings_a, f"{int(w) + 5}.{sig}", now)        # future window
    with tenant_context(agency_id=agency_b.id):
        other = att.get_settings(agency_b)
    assert not att.verify_qr_token(other, tok, now)                                 # another agency's code
    assert not att.verify_qr_token(settings_a, "garbage", now)


# --- Checks ----------------------------------------------------------------------

def test_network_and_location_checks(settings_a, agent_a):
    settings_a.require_network = settings_a.require_location = True
    ok, field, results, meta = att.evaluate(settings_a, agent_a, "203.0.113.7", "", 31.5205, 74.3588, 20)
    assert ok and not field and meta["distance_m"] < 50
    ok, _f, results, _m = att.evaluate(settings_a, agent_a, "198.51.100.1", "", 31.5205, 74.3588, 20)
    assert not ok and [r["key"] for r in results if not r["ok"]] == ["network"]
    ok, _f, results, _m = att.evaluate(settings_a, agent_a, "203.0.113.7", "", 31.60, 74.36, 20)  # ~9 km away
    assert not ok and "km from the office" in results[-1]["message"]
    ok, _f, results, _m = att.evaluate(settings_a, agent_a, "203.0.113.7", "", 31.5205, 74.3588, 900)
    assert not ok and "too vague" in results[-1]["message"]


def test_field_staff_need_location_not_office(settings_a, agent_a):
    settings_a.require_network = settings_a.require_qr = True
    with tenant_context(agency_id=settings_a.agency_id):
        settings_a.field_staff.add(agent_a)
        ok, field, results, _m = att.evaluate(settings_a, agent_a, "1.2.3.4", "", 21.67, 39.15, 30)  # Jeddah
        assert ok and field and [r["key"] for r in results] == ["location"]
        ok, _f, _r, _m = att.evaluate(settings_a, agent_a, "1.2.3.4", "", None, None, None)
        assert not ok


# --- Check in / out ----------------------------------------------------------------

def test_check_in_on_time_late_and_out(settings_a, agent_a, agency_a, monkeypatch):
    settings_a.require_network = True
    settings_a.save()
    with tenant_context(agency_id=agency_a.id):
        _at(monkeypatch, 9, 5)
        r = att.check(agency_a, agent_a, "in", "203.0.113.7", "", None, None, None)
        assert r["ok"] and r["status"] == "present"
        assert not att.check(agency_a, agent_a, "in", "203.0.113.7", "", None, None, None)["ok"]  # once a day
        r = att.check(agency_a, agent_a, "out", "203.0.113.7", "", None, None, None)
        assert r["ok"]
        log = att.todays_log(agency_a, agent_a, datetime.date(2026, 10, 7))
        assert log.source == "self" and log.check_in_meta["checks"] == {"network": True}

        # From home: blocked, nothing recorded.
        _at(monkeypatch, 9, 30, day=datetime.date(2026, 10, 8))
        r = att.check(agency_a, agent_a, "in", "198.51.100.1", "", None, None, None)
        assert not r["ok"] and att.todays_log(agency_a, agent_a, datetime.date(2026, 10, 8)) is None
        r = att.check(agency_a, agent_a, "in", "203.0.113.7", "", None, None, None)
        assert r["ok"] and r["status"] == "late"


def test_absences_are_automatic_and_not_backfilled(settings_a, agent_a, agency_a, user_a, monkeypatch):
    from member.models import AttendanceLog, AttendanceSettings
    with tenant_context(agency_id=agency_a.id):
        settings_a.exempt_staff.add(user_a)  # the owner isn't tracked
        AttendanceSettings.all_tenants.filter(pk=settings_a.pk).update(
            created_at=datetime.datetime(2026, 10, 5, 8, 0, tzinfo=KHI))
        settings_a.refresh_from_db()
        _at(monkeypatch, 13, 0)  # Wed 7 Oct, after the 12:00 cut-off
        att.ensure_absences(agency_a, settings_a, datetime.date(2026, 10, 1), datetime.date(2026, 10, 31))
        days = set(AttendanceLog.objects.filter(user=agent_a, status="absent").values_list("date", flat=True))
        assert days == {datetime.date(2026, 10, 5), datetime.date(2026, 10, 6), datetime.date(2026, 10, 7)}
        assert not AttendanceLog.objects.filter(user=user_a).exists()


def test_owner_is_not_tracked_by_default(agency_b, user_b):
    with tenant_context(agency_id=agency_b.id):
        s = att.get_settings(agency_b)
        assert list(s.exempt_staff.all()) == [user_b]
        assert att.tracked_staff(agency_b, s) == []


def test_correction_approval_updates_record(settings_a, agent_a, agency_a, user_a):
    from member.models import AttendanceCorrection
    with tenant_context(agency_id=agency_a.id):
        c = AttendanceCorrection.objects.create(
            agency=agency_a, user=agent_a, date=datetime.date(2026, 10, 6), requested_status="present",
            requested_check_in=datetime.time(9, 0), reason="Phone died",
        )
        log = att.review_correction(c, True, user_a, "ok")
        assert log.status == "present" and log.source == "correction" and log.check_in_time == datetime.time(9, 0)
        c.refresh_from_db()
        assert c.status == "approved" and c.reviewed_by == user_a


# --- Pages & permissions -----------------------------------------------------------

def test_agent_can_check_in_page_but_not_settings(agent_client, settings_a):
    assert agent_client.get("/member/attendance/me/").status_code == 200
    assert agent_client.get("/member/settings/attendance/").status_code == 403


def test_settings_hub_routes_by_role(client_a, agent_client):
    assert client_a.get("/member/settings/")["Location"] == "/member/settings/attendance/"
    assert agent_client.get("/member/settings/")["Location"] == "/settings/language/"
    assert client_a.get("/member/attendance/settings/").status_code == 301  # old link still works
    page = client_a.get("/member/settings/attendance/").content.decode()
    assert "settings-tabs" in page and "Company profile" in page


def test_check_endpoint_returns_reasons(agent_client, settings_a):
    settings_a.require_network = True
    settings_a.save()
    r = agent_client.post("/member/attendance/check/", {"action": "in"}, REMOTE_ADDR="198.51.100.1")
    assert r.status_code == 400 and r.json()["results"][0]["key"] == "network"
    r = agent_client.post("/member/attendance/check/", {"action": "in"}, REMOTE_ADDR="203.0.113.7")
    assert r.status_code == 200 and r.json()["ok"]


def test_kiosk_display_needs_qr_enabled_and_valid_token(settings_a, client_a):
    anon = Client()
    assert anon.get(f"/attendance/display/{settings_a.kiosk_token}/").status_code == 404  # QR off
    settings_a.require_qr = True
    settings_a.save()
    assert anon.get(f"/attendance/display/{settings_a.kiosk_token}/").status_code == 200
    qr = anon.get(f"/attendance/display/{settings_a.kiosk_token}/qr.svg")
    assert qr.status_code == 200 and qr["Content-Type"] == "image/svg+xml" and int(qr["X-Rotates-In"]) > 0
    assert anon.get("/attendance/display/not-the-token/").status_code == 404


def test_settings_page_saves(client_a, settings_a, agent_a):
    r = client_a.post("/member/settings/attendance/", {
        "require_qr": "on", "radius_m": "200", "max_accuracy_m": "100", "late_after_minutes": "10",
        "workday_start": "09:30", "absent_after": "12:00", "workday_end": "18:00",
        "work_days": ["0", "1", "2", "3", "4"], "time_zone": "Asia/Karachi", "field_staff": [str(agent_a.id)],
        "office_lat": "31.5204", "office_lng": "74.3587",
    })
    assert r.status_code == 302
    settings_a.refresh_from_db()
    assert settings_a.require_qr and not settings_a.require_network and settings_a.radius_m == 200
    assert settings_a.workday_start == datetime.time(9, 30) and settings_a.work_days == [0, 1, 2, 3, 4]
    with tenant_context(agency_id=settings_a.agency_id):
        assert list(settings_a.field_staff.all()) == [agent_a]


@override_settings(ATTENDANCE_TRUSTED_PROXIES=1)
def test_client_ip_trusts_only_configured_proxies():
    req = RequestFactory().get("/", REMOTE_ADDR="10.0.0.2", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.7")
    assert att.client_ip(req) == "203.0.113.7"


def test_client_ip_ignores_forwarded_header_without_proxies():
    req = RequestFactory().get("/", REMOTE_ADDR="198.51.100.1", HTTP_X_FORWARDED_FOR="203.0.113.7")
    assert att.client_ip(req) == "198.51.100.1"


def test_login_next_is_not_an_open_redirect(user_a):
    c = Client()
    r = c.post("/login/?next=https://evil.example/", {"username": "owner_a", "password": "TestPass123!"})
    assert r.status_code == 302 and "evil.example" not in r["Location"]
    c = Client()
    r = c.post("/login/?next=/member/attendance/me/", {"username": "owner_a", "password": "TestPass123!"})
    assert r["Location"] == "/member/attendance/me/"


def test_records_filters(client_a, agency_a, agent_a, user_a, settings_a):
    from member.models import AttendanceLog
    today = att.office_now(settings_a).date()
    with tenant_context(agency_id=agency_a.id):
        AttendanceLog.objects.create(agency=agency_a, user=agent_a, person_name=agent_a.full_name, date=today,
                                     status="late", source="self")
        AttendanceLog.objects.create(agency=agency_a, user=user_a, person_name="Owner Person", date=today,
                                     status="present", source="manual")
    month = today.strftime("%Y-%m")
    def names(**params):
        r = client_a.get("/member/attendance/", {"month": month, **params})
        return [log.person_name for log in r.context["logs"]]
    assert sorted(names()) == sorted([agent_a.full_name, "Owner Person"])
    assert names(status="late") == [agent_a.full_name]
    assert names(source="manual") == ["Owner Person"]
    assert names(staff="Owner Person", day="today") == ["Owner Person"]
    # Current month opens on "today only"; another month always shows every day.
    assert client_a.get("/member/attendance/").context["rec_filters"]["day"] == "today"
    assert client_a.get("/member/attendance/", {"month": "2020-01"}).context["rec_filters"]["day"] == "month"
    page = client_a.get("/member/attendance/", {"month": month, "status": "leave"}).content.decode()
    assert "No matching records" in page and "Live board" not in page


def test_seed_attendance_sample(agency_a, user_a, client_a):
    from django.core.management import call_command

    from member.models import AttendanceCorrection, AttendanceLog
    call_command("seed_attendance_sample", agency="Agency A")
    call_command("seed_attendance_sample", agency="Agency A")  # idempotent
    with tenant_context(agency_id=agency_a.id):
        s = att.get_settings(agency_a)
        assert s.require_network and s.require_qr and "127.0.0.1" in s.office_ips
        assert AttendanceLog.objects.filter(check_in_meta__sample=True).exists()
        assert AttendanceCorrection.objects.filter(status="pending").count() == 2
    page = client_a.get("/member/attendance/").content.decode()
    assert "Bilal Ahmed" in page and "Correction requests" in page
    assert "Manual entry" not in page  # manual entry is gone
    assert client_a.post("/member/attendance/mark/").status_code == 404
