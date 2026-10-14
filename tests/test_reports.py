"""Reports: period resolution/bucketing, the single analytics page, CSV, legacy URLs."""
import datetime
import io

import openpyxl
from django.core.management import call_command
from django.http import QueryDict

from reports import analytics


def _period(qs, today=datetime.date(2026, 10, 8)):
    return analytics.resolve_period(QueryDict(qs), today=today)


def test_presets_and_previous_period():
    p = _period("preset=this_month")
    assert (p["start"], p["end"]) == (datetime.date(2026, 10, 1), datetime.date(2026, 10, 31))
    assert p["granularity"] == "week"
    assert (p["prev_start"], p["prev_end"]) == (datetime.date(2026, 8, 31), datetime.date(2026, 9, 30))

    p = _period("preset=last_6_months")
    assert (p["start"], p["end"]) == (datetime.date(2026, 5, 1), datetime.date(2026, 10, 31))
    assert p["granularity"] == "month"

    p = _period("preset=custom&from=2026-01-01&to=2026-03-31&group=week")
    assert p["granularity"] == "week" and p["start"] == datetime.date(2026, 1, 1)

    assert _period("")["preset"] == analytics.DEFAULT_PRESET


def test_grouping_follows_the_date_range():
    expected = {"today": "day", "last_7": "day", "this_week": "day", "this_month": "week",
                "last_month": "week", "last_6_months": "month",
                "this_year": "month", "last_year": "month"}
    for preset, granularity in expected.items():
        assert _period(f"preset={preset}")["granularity"] == granularity, preset
    # Quarter is no longer offered; an old ?preset=this_quarter link falls back to the default.
    assert _period("preset=this_quarter")["preset"] == analytics.DEFAULT_PRESET
    # A stray ?group= from an old link is ignored.
    assert _period("preset=this_year&group=quarter")["granularity"] == "month"


def test_granularity_steps_up_when_too_many_bars():
    p = _period("preset=custom&from=2020-01-01&to=2026-12-31&group=day")
    assert len(analytics.bucket_starts(p["start"], p["end"], p["granularity"])) <= analytics.MAX_BUCKETS
    assert p["granularity"] in ("month", "quarter")


def test_bucket_labels():
    d = datetime.date(2026, 10, 8)
    assert analytics.bucket_label(analytics.bucket_key(d, "quarter"), "quarter") == "Q4 2026"
    assert analytics.bucket_label(analytics.bucket_key(d, "month"), "month") == "Oct 2026"
    assert analytics.bucket_key(d, "week") == datetime.date(2026, 10, 5)


def test_report_numbers_match_ledger(agency_a, user_a):
    from utils.tenancy import tenant_context
    call_command("seed_ledger_sample", agency="Agency A")
    period = _period("preset=custom&from=2025-07-01&to=2025-10-31&group=month", today=datetime.date(2025, 12, 1))
    with tenant_context(agency_id=agency_a.id):
        report = analytics.build_report(agency_a, period)
    # Supplier statement: NAHD paid out 3,787,600 in Jul–Oct 2025 (incl. the 7,600 JV,
    # which is a journal, not a cash payment).
    s = report["series"]
    assert sum(s["cash_out"]) >= 3780000
    assert "Hotel" in report["breakdowns"]["services"]["labels"]
    tones = {tone for tone, _text in report["insights"]}
    texts = " ".join(text for _tone, text in report["insights"])
    assert tones <= {"good", "bad", "neutral"} and "Gross margin" in texts
    assert report["deltas"]["cash_in"] is None or report["deltas"]["cash_in"]["dir"] in ("up", "down", "flat")


def test_reports_page_renders_and_exports(client_a, agency_a, user_a):
    call_command("seed_ledger_sample", agency="Agency A")
    r = client_a.get("/member/reports/", {"preset": "last_6_months"})
    assert r.status_code == 200
    body = r.content.decode()
    assert "Money in vs money out" in body and 'id="rpt-data"' in body
    xlsx = client_a.get("/member/reports/", {"preset": "this_year", "export": "xlsx"})
    assert xlsx.status_code == 200 and "spreadsheetml" in xlsx["Content-Type"]
    wb = openpyxl.load_workbook(io.BytesIO(xlsx.content))
    assert wb.sheetnames == ["Summary", "Over time", "Bookings", "Party balances", "Breakdowns", "Attendance", "Installments"]
    assert [c.value for c in wb["Over time"][1]][:2] == ["Period", "Bookings"]


def test_legacy_report_urls_redirect(client_a):
    r = client_a.get("/member/reports/revenue/", {"months": "6"})
    assert r.status_code == 302 and r["Location"].endswith("/member/reports/")


def test_attendance_in_report(agency_a, user_a, client_a):
    from member.models import AttendanceLog
    from utils.tenancy import tenant_context
    d = datetime.date(2026, 10, 7)
    with tenant_context(agency_id=agency_a.id):
        AttendanceLog.objects.create(agency=agency_a, person_name="A", date=d, status="present", work_hours=8)
        AttendanceLog.objects.create(agency=agency_a, person_name="A", date=d + datetime.timedelta(days=1), status="late", work_hours=7)
        AttendanceLog.objects.create(agency=agency_a, person_name="B", date=d, status="absent")
        AttendanceLog.objects.create(agency=agency_a, person_name="B", date=d + datetime.timedelta(days=1), status="leave")
        period = _period("preset=this_month", today=d)
        report = analytics.build_report(agency_a, period)
    k = report["attendance"]["kpis"]
    assert k["rate"] == round(2 * 100 / 3, 1) and k["late"] == 1 and k["absent"] == 1 and k["avg_hours"] == 7.5
    people = {r["name"]: r for r in report["attendance"]["people"]}
    assert people["A"]["rate"] == 100 and people["B"]["rate"] == 0
    assert any("attendance" in t for _tone, t in report["insights"])
