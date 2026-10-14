"""Activity Log page: filters, readable changes, CSV, and no login noise."""
import pytest

from utils.tenancy import tenant_context


@pytest.fixture
def logged(agency_a, user_a, hotel_a):
    from system_config.models import AuditLog
    with tenant_context(agency_id=agency_a.id):
        AuditLog.all_tenants.create(agency=agency_a, user=user_a, action="update", model_name="Booking",
                                    object_id="1", object_repr="A-VCH-001",
                                    changes={"status": {"old": "draft", "new": "confirmed"},
                                             "updated_at": {"old": "2026-10-08T03:06:19+00:00", "new": "2026-10-08T18:23:37+00:00"}})
        AuditLog.all_tenants.create(agency=agency_a, user=None, action="create", model_name="LedgerEntry",
                                    object_id="2", object_repr="expense - 85000", changes={})


def test_page_shows_readable_changes(client_a, logged):
    r = client_a.get("/member/activity-log/")
    assert r.status_code == 200
    body = r.content.decode()
    assert "Draft" in body and "Confirmed" in body          # choice labels, not raw codes
    assert "08 Oct 2026" in body or "09 Oct 2026" in body     # local, readable timestamps
    assert "System" in body and "Ledger entry" in body        # no blank "who"; friendly type names


def test_filters(client_a, logged, user_a):
    def reprs(**p):
        return [row["e"].object_repr for row in client_a.get("/member/activity-log/", p).context["rows"]]
    # Creating the test's own users/hotel is (correctly) logged too, so check membership.
    assert "expense - 85000" in reprs(action="create") and "A-VCH-001" not in reprs(action="create")
    assert reprs(model="Booking") == ["A-VCH-001"]
    assert "expense - 85000" in reprs(who="system") and "A-VCH-001" not in reprs(who="system")
    assert reprs(who=str(user_a.id)) == ["A-VCH-001"]
    assert reprs(q="vch") == ["A-VCH-001"]
    r = client_a.get("/member/activity-log/", {"action": "create"})
    assert r.context["counts"]["update"] == 1  # cards ignore the action filter


def test_csv_export(client_a, logged):
    r = client_a.get("/member/activity-log/", {"export": "csv"})
    text = r.content.decode("utf-8-sig")
    assert r["Content-Type"].startswith("text/csv") and "Status: Draft -> Confirmed" in text


def test_login_does_not_create_noise(user_a):
    from django.test import Client

    from system_config.models import AuditLog
    with tenant_context(bypass=True):
        before = AuditLog.all_tenants.count()
    Client().post("/login/", {"username": "owner_a", "password": "TestPass123!"})
    with tenant_context(bypass=True):
        assert AuditLog.all_tenants.count() == before


def test_times_are_in_office_timezone(client_a, agency_a, user_a):
    import datetime

    from system_config.models import AuditLog
    with tenant_context(agency_id=agency_a.id):
        e = AuditLog.all_tenants.create(agency=agency_a, user=user_a, action="create", model_name="Hotel",
                                        object_id="9", object_repr="TZ check")
        AuditLog.all_tenants.filter(pk=e.pk).update(
            timestamp=datetime.datetime(2026, 10, 8, 21, 35, tzinfo=datetime.timezone.utc))
    row = next(r for r in client_a.get("/member/activity-log/").context["rows"] if r["e"].object_repr == "TZ check")
    assert (row["when_date"], row["when_time"]) == ("09 Oct 2026", "2:35 AM")  # UTC+5


def test_contacts_corrections_and_voucher_content_are_logged(client_a, agency_a, user_a, hotel_a):
    import datetime
    import json

    from member.models import AttendanceCorrection, Booking, ContactInstruction
    from system_config.models import AuditLog
    with tenant_context(agency_id=agency_a.id):
        c = ContactInstruction.objects.create(agency=agency_a, created_by=user_a, city="Makkah", role="Group Leader",
                                              contact_name="Ahmed", phone_number="1")
        c.phone_number = "2"
        c.save()
        AttendanceCorrection.objects.create(agency=agency_a, user=user_a, date=datetime.date.today(),
                                            requested_status="present", reason="forgot")
    with tenant_context(agency_id=agency_a.id):
        kinds = {(e.model_name, e.action) for e in AuditLog.objects.all()}
    assert ("ContactInstruction", "create") in kinds and ("ContactInstruction", "update") in kinds
    assert ("AttendanceCorrection", "create") in kinds

    def payload(**kw):
        d = {"save_as": "save", "package_name": "Log test", "pax_adults": "1",
             "mutamers_json": json.dumps([{"name": "Ali", "passport_number": "A1", "pax_type": "adult"}]),
             "hotels_json": json.dumps([{"hotel_id": hotel_a.id, "check_in": "2026-11-03", "check_out": "2026-11-08", "room_type": "Quad", "meal_plan": "BB"}])}
        d.update(kw)
        return d
    assert client_a.post("/member/bookings/save/", payload()).status_code == 302
    with tenant_context(agency_id=agency_a.id):
        b = Booking.objects.get(package_name="Log test")
    # Changing only the hotel (no voucher field changes) still leaves a readable entry.
    client_a.post("/member/bookings/save/", payload(worksheet_booking_id=str(b.id), hotels_json=json.dumps([])))
    with tenant_context(agency_id=agency_a.id):
        entry = AuditLog.objects.filter(model_name="Booking", action="update", object_id=str(b.id)).order_by("-id").first()
    assert entry is not None and "Hotels" in entry.changes and "Hotel A" in entry.changes["Hotels"]["old"] and entry.changes["Hotels"]["new"] == "—"
    assert entry.object_repr.startswith(b.voucher_number)
    # Searching by the friendly type name finds them.
    rows = client_a.get("/member/activity-log/", {"q": "contact instruction"}).context["rows"]
    assert rows and all(r["e"].model_name == "ContactInstruction" for r in rows)
