"""Shared analytics helpers: period resolution/bucketing; the removed Reports page stays gone."""
import datetime

from django.http import QueryDict

from member import analytics


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


def test_reports_section_is_gone(client_a):
    # Every section has its own insights page; the standalone Reports page was removed.
    assert client_a.get("/member/reports/").status_code == 404
    page = client_a.get("/member/dashboard/").content.decode()
    assert "/member/reports/" not in page


def test_activity_log_capability_replaced_reports():
    from rbac.catalog import CAPABILITIES

    keys = [k for k, _label in CAPABILITIES]
    assert "activity_log" in keys and "reports" not in keys
