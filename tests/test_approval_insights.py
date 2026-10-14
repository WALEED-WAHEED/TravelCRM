import datetime
import io

import openpyxl
import pytest
from django.test import Client
from django.utils import timezone

from member import approval_insights as ai
from member.models import Booking, BookingHotel, BookingMutamer
from reports import analytics
from utils.tenancy import tenant_context


@pytest.fixture
def agent_a(agency_a):
    from accounts.models import User
    with tenant_context(bypass=True):
        return User.objects.create_user(username="agent_ins", password="TestPass123!", role="agent",
                                        agency=agency_a, first_name="Hira", last_name="Agent")


def _voucher(agency, agent, number, status, pax=2, package="Umrah 10", hours_to_decide=None, decider=None, reason=""):
    now = timezone.now()
    with tenant_context(bypass=True):
        b = Booking.all_tenants.create(
            agency=agency, agent=agent, voucher_number=number, status=status, pax_adults=pax, package_name=package,
            submitted_at=now - datetime.timedelta(hours=(hours_to_decide or 0) + 1), rejection_reason=reason,
            decided_by=decider, decided_at=(now - datetime.timedelta(hours=1)) if decider else None)
        BookingMutamer.objects.create(booking=b, name=f"Head {number}", passport_number="P" + number[-1])
        BookingHotel.objects.create(booking=b, city="Makkah", hotel_name="H", check_in=now.date(),
                                    check_out=now.date() + datetime.timedelta(days=5), nights=5)
    return b


def test_numbers_tables_and_reasons(agency_a, agent_a, user_a):
    _voucher(agency_a, agent_a, "AI-1", "confirmed", hours_to_decide=2, decider=user_a)
    _voucher(agency_a, agent_a, "AI-2", "rejected", pax=6, hours_to_decide=30, decider=user_a, reason="Passport missing")
    _voucher(agency_a, agent_a, "AI-3", "pending", package="")
    _voucher(agency_a, agent_a, "AI-4", "draft")                    # never submitted: not part of approvals
    period = analytics.resolve_period({"preset": "this_year"})
    with tenant_context(agency_id=agency_a.id):
        data = ai.build(agency_a, period)
    k = data["kpis"]
    assert (k["submitted"], k["approved"], k["rejected"], k["pending"]) == (3, 1, 1, 1)
    assert k["approval_rate"] == 50 and k["pax"] == 10 and k["avg_hours"] == 16.0 and k["avg_text"]
    agent_row = data["tables"]["agents"][0]
    assert agent_row["agent"] == "Hira Agent" and agent_row["submitted"] == 3 and agent_row["rate"] == 50
    assert data["tables"]["deciders"][0]["decisions"] == 2
    assert [r["reason"] for r in data["tables"]["reasons"]] == ["Passport missing"]
    assert data["tables"]["reasons"][0]["head"] == "Head AI-2"
    assert {r["package"] for r in data["tables"]["packages"]} == {"Umrah 10", "Custom trip"}
    assert sum(data["charts"]["speed"]["values"]) == 2 and data["charts"]["cities"]["labels"] == ["Makkah"]


def test_page_export_and_isolation(client_a, agency_a, agent_a, agency_b, user_a):
    from accounts.models import User
    with tenant_context(bypass=True):
        other_agent = User.objects.create_user(username="agent_b", password="TestPass123!", role="agent", agency=agency_b)
    _voucher(agency_a, agent_a, "AI-9", "confirmed", decider=user_a)
    _voucher(agency_b, other_agent, "OTHER-1", "pending", package="Other agency package")
    r = client_a.get("/member/approvals/insights/", {"preset": "this_year"})
    assert r.status_code == 200
    body = r.content.decode()
    assert "Approval insights" in body and "Other agency package" not in body
    assert r.context["data"]["kpis"]["submitted"] == 1
    x = client_a.get("/member/approvals/insights/", {"preset": "this_year", "export": "xlsx"})
    assert x.status_code == 200 and "spreadsheetml" in x["Content-Type"]
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    assert wb.sheetnames == ["Summary", "Trends", "Agents", "Decisions", "Sent back", "Packages", "Group"]
    assert wb["Summary"]["B6"].value == 1
    # every date range works
    for preset in analytics.PRESETS:
        if preset != "custom":
            assert client_a.get("/member/approvals/insights/", {"preset": preset}).status_code == 200
    # agents cannot open the team's insights
    c = Client()
    c.force_login(agent_a)
    assert c.get("/member/approvals/insights/").status_code in (302, 403)
