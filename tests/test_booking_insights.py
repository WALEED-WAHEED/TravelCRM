import datetime
import io

import openpyxl
from django.http import QueryDict

from member import booking_insights as bi
from member.models import Booking, BookingHotel
from reports import analytics
from utils.tenancy import tenant_context


def _make(agency, user, status, value, adults, start=None, package="Umrah 15", country="Pakistan"):
    with tenant_context(agency_id=agency.id):
        b = Booking.objects.create(agency=agency, agent=user, status=status, total_price=value, pax_adults=adults,
                                   package_name=package, client_country=country, voucher_number=f"T-{status}-{value}")
        if start:
            BookingHotel.objects.create(booking=b, city="Makkah", hotel_name="H1", check_in=start,
                                        check_out=start + datetime.timedelta(days=7), nights=7)
    return b


def test_kpis_and_sections(agency_a, user_a):
    soon = datetime.date.today() + datetime.timedelta(days=5)
    _make(agency_a, user_a, "confirmed", 100_000, 4, start=soon)
    _make(agency_a, user_a, "draft", 50_000, 2, package="")
    _make(agency_a, user_a, "cancelled", 30_000, 1)
    period = analytics.resolve_period(QueryDict("preset=this_year"))
    with tenant_context(agency_id=agency_a.id):
        data = bi.build(agency_a, period)
        k = data["kpis"]
        assert k["vouchers"] == 2 and k["saved"] == 1 and k["drafts"] == 1      # cancelled is hidden
        assert k["saved_rate"] == 50.0 and k["pax"] == 6 and k["avg_nights"] == 7 and k["hotel_nights"] == 7
        # Packages table lists the custom trip too; team table counts the creator.
        names = {r["package"] for r in data["tables"]["packages"]}
        assert "Umrah 15" in names and "Custom trip" in names
        assert data["tables"]["team"][0]["vouchers"] == 2
        assert data["tables"]["hotels"][0]["nights"] == 7


def test_page_export_and_isolation(client_a, agency_a, user_a, agency_b, user_b):
    _make(agency_a, user_a, "confirmed", 100_000, 4)
    _make(agency_b, user_b, "confirmed", 999_000, 9, package="Other agency")
    r = client_a.get("/member/bookings/insights/", {"preset": "this_year"})
    assert r.status_code == 200
    body = r.content.decode()
    assert "Voucher insights" in body and "Other agency" not in body
    x = client_a.get("/member/bookings/insights/", {"preset": "this_year", "export": "xlsx"})
    assert x.status_code == 200 and "spreadsheetml" in x["Content-Type"]
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    assert wb.sheetnames == ["Summary", "Trends", "Travellers", "Stay", "Travel", "Packages", "Team"]
    assert wb["Summary"]["B6"].value == 1          # one voucher: agency A's, not agency B's


def test_every_date_range_works(client_a, agency_a, user_a):
    _make(agency_a, user_a, "confirmed", 1, 3)          # created now
    today = datetime.date.today()

    def count(params):
        r = client_a.get("/member/bookings/insights/", params)
        assert r.status_code == 200
        return r.context["data"]["kpis"]["vouchers"], r.context["period"]

    for preset in analytics.PRESETS:
        if preset != "custom":
            assert client_a.get("/member/bookings/insights/", {"preset": preset}).status_code == 200
    # Ranges that contain today include the voucher, ranges in the past don't.
    for preset in ("today", "this_week", "this_month", "this_year", "last_7", "last_6_months"):
        assert count({"preset": preset})[0] == 1, preset
    for preset in ("last_month", "last_year"):
        assert count({"preset": preset})[0] == 0, preset
    n, period = count({"preset": "custom", "from": str(today - datetime.timedelta(days=3)), "to": str(today)})
    assert n == 1 and period["start"] == today - datetime.timedelta(days=3)
    assert count({"preset": "custom", "from": "2020-01-01", "to": "2020-01-31"})[0] == 0
    # The filter row is gone: old query strings are simply ignored.
    assert count({"preset": "this_year", "status": "draft", "package": "x"})[0] == 1
