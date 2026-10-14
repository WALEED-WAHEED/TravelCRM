"""Agents create vouchers with the team's own form and submit them; the team approves, edits or sends them back."""
import datetime
import json

import pytest
from django.test import Client
from django.utils import timezone

from member.models import Booking, Hotel
from utils.tenancy import tenant_context


@pytest.fixture
def agent_a(agency_a):
    from accounts.models import User
    with tenant_context(bypass=True):
        return User.objects.create_user(username="agent_a", password="TestPass123!", role="agent", agency=agency_a)


@pytest.fixture
def agent_client(agent_a):
    c = Client()
    c.force_login(agent_a)
    return c


@pytest.fixture
def hotel_a(agency_a, user_a):
    with tenant_context(agency_id=agency_a.id):
        return Hotel.objects.create(agency=agency_a, created_by=user_a, name="Al Safwah", city="Makkah",
                                    sale_price=0, purchase_price=0)


def _form(hotel, save_as, booking=None, **extra):
    data = {
        "save_as": save_as, "package_name": "Agent Umrah", "client_whatsapp": "+92 300 1112223",
        "pax_adults": "2", "pax_children": "0", "pax_infants": "0",
        "mutamers_json": json.dumps([{"name": "Ali Khan", "passport_number": "AB123", "gender": "male", "pax_type": "adult"},
                                     {"name": "Sara Khan", "passport_number": "AB124", "gender": "female", "pax_type": "adult"}]),
        "hotels_json": json.dumps([{"hotel_id": hotel.id, "check_in": "2026-11-03", "check_out": "2026-11-10",
                                    "room_type": "Double", "meal_plan": "BB", "view": "Standard"}]),
        "notes_json": json.dumps(["agents must not be able to write internal notes"]),
    }
    if booking is not None:
        data["worksheet_booking_id"] = str(booking.id)
    data.update(extra)
    return data


def _submit(agent_client, hotel, booking=None):
    r = agent_client.post("/agent/vouchers/save/", _form(hotel, "submit", booking))
    assert r.status_code == 302
    with tenant_context(bypass=True):
        return Booking.all_tenants.filter(package_name="Agent Umrah").order_by("-id").first()


def test_agent_uses_the_same_form_and_submits_for_approval(client_a, agent_client, agent_a, hotel_a):
    page = agent_client.get("/agent/vouchers/new/").content.decode()
    assert "Submit for approval" in page and "Save as draft" in page
    assert "Client WhatsApp" in page and "Team contacts" in page and 'id="vn-data"' not in page   # same form, no team notes

    r = agent_client.post("/agent/vouchers/save/", _form(hotel_a, "draft"))
    assert r.status_code == 302
    with tenant_context(bypass=True):
        b = Booking.all_tenants.get(package_name="Agent Umrah")
        assert b.status == "draft" and b.agent_id == agent_a.id and b.voucher_notes.count() == 0
        assert b.hotels.count() == 1 and b.booking_mutamers.count() == 2
    assert agent_client.get(f"/agent/vouchers/{b.id}/edit/").status_code == 200

    b = _submit(agent_client, hotel_a, b)
    assert b.status == "pending" and b.submitted_at is not None
    # It is in the team's Approvals queue, and not in their Vouchers list.
    assert b.voucher_number.encode() in client_a.get("/member/approvals/").content
    assert b.voucher_number.encode() not in client_a.get("/member/bookings/").content


def test_team_edits_with_the_same_form_and_approves(client_a, agent_client, hotel_a, user_a):
    b = _submit(agent_client, hotel_a)
    page = client_a.get(f"/member/bookings/{b.id}/").content.decode()
    assert 'value="approve"' in page and 'value="keep"' in page and "Ali Khan" in page   # Save / Save & approve
    r = client_a.post("/member/bookings/save/", _form(hotel_a, "approve", b, package_name="Agent Umrah"))
    assert r.status_code == 302
    with tenant_context(bypass=True):
        b.refresh_from_db()
    assert b.status == "confirmed" and b.decided_by_id == user_a.id and b.decided_at is not None
    # Approved: now in the Vouchers list and on the Approvals page as approved; the agent can no longer change it.
    assert b.voucher_number.encode() in client_a.get("/member/bookings/").content
    assert b"Approved" in client_a.get("/member/approvals/").content
    assert agent_client.post("/agent/vouchers/save/", _form(hotel_a, "submit", b)).status_code == 302
    with tenant_context(bypass=True):
        b.refresh_from_db()
    assert b.status == "confirmed"


def test_approve_and_send_back_with_a_reason(client_a, agent_client, hotel_a):
    first, second = _submit(agent_client, hotel_a), None
    assert client_a.post(f"/member/approvals/{first.id}/approve/").status_code == 200
    second = _submit(agent_client, hotel_a)
    reject = f"/member/approvals/{second.id}/reject/"
    assert client_a.post(reject, data=json.dumps({"reason": "  "}), content_type="application/json").status_code == 400
    assert client_a.post(reject, data=json.dumps({"reason": "Passport number is missing"}),
                         content_type="application/json").status_code == 200
    with tenant_context(bypass=True):
        first.refresh_from_db()
        second.refresh_from_db()
    assert first.status == "confirmed" and second.status == "rejected" and second.rejection_reason == "Passport number is missing"
    # The agent sees the reason, fixes the voucher with the same form and resubmits it.
    assert "Passport number is missing" in agent_client.get("/agent/vouchers/").content.decode()
    assert "Passport number is missing" in agent_client.get(f"/agent/vouchers/{second.id}/edit/").content.decode()
    _submit(agent_client, hotel_a, second)
    with tenant_context(bypass=True):
        second.refresh_from_db()
    assert second.status == "pending" and second.rejection_reason == ""
    # Already decided vouchers cannot be decided again.
    assert client_a.post(f"/member/approvals/{first.id}/approve/").status_code == 400


def test_an_agent_only_touches_their_own_vouchers_and_cannot_approve(client_a, agent_client, agency_a, hotel_a, user_a):
    from accounts.models import User
    with tenant_context(bypass=True):
        other = User.objects.create_user(username="agent_other", password="TestPass123!", role="agent", agency=agency_a)
    oc = Client()
    oc.force_login(other)
    mine = _submit(agent_client, hotel_a)
    assert oc.get(f"/agent/vouchers/{mine.id}/edit/").status_code == 404
    assert oc.post("/agent/vouchers/save/", _form(hotel_a, "draft", mine)).status_code == 302
    with tenant_context(bypass=True):
        mine.refresh_from_db()
    assert mine.status == "pending"                                     # the other agent's save did nothing
    # Posting a status or an approve action as an agent never approves.
    agent_client.post("/agent/vouchers/save/", _form(hotel_a, "approve", mine, status="confirmed"))
    with tenant_context(bypass=True):
        mine.refresh_from_db()
    assert mine.status == "draft"
    assert agent_client.post(f"/member/approvals/{mine.id}/approve/").status_code in (302, 403)


def test_other_agency_cannot_decide(client_b, agent_client, hotel_a):
    b = _submit(agent_client, hotel_a)
    assert client_b.post(f"/member/approvals/{b.id}/approve/").status_code == 404
    assert client_b.post(f"/member/approvals/{b.id}/reject/", data="{}", content_type="application/json").status_code == 404
    assert b.voucher_number.encode() not in client_b.get("/member/approvals/").content


def test_approvals_lists_every_pending_voucher_and_nothing_else(client_a, agent_client, hotel_a):
    old = timezone.now() - datetime.timedelta(days=90)
    waiting, approved, sent_back = _submit(agent_client, hotel_a), _submit(agent_client, hotel_a), _submit(agent_client, hotel_a)
    client_a.post(f"/member/approvals/{approved.id}/approve/")
    client_a.post(f"/member/approvals/{sent_back.id}/reject/", data=json.dumps({"reason": "Fix dates"}), content_type="application/json")
    with tenant_context(bypass=True):
        Booking.all_tenants.filter(pk=waiting.id).update(submitted_at=old, created_at=old)      # waiting for 3 months
    page = client_a.get("/member/approvals/").content.decode()
    assert waiting.voucher_number in page                       # however old, a waiting voucher is always here
    assert approved.voucher_number not in page                  # approved ones moved to the Vouchers page
    assert sent_back.voucher_number not in page                 # sent-back ones went back to their agent
    assert approved.voucher_number in client_a.get("/member/bookings/").content.decode()
    assert sent_back.voucher_number in agent_client.get("/agent/vouchers/").content.decode()
    # The history lives in the insights, for whatever period is chosen.
    today = timezone.localdate()
    r = client_a.get("/member/approvals/insights/", {"preset": "custom", "from": str(today - datetime.timedelta(days=120)), "to": str(today)})
    k = r.context["data"]["kpis"]
    assert (k["submitted"], k["approved"], k["rejected"], k["pending"]) == (3, 1, 1, 1)


def test_vouchers_page_can_filter_agent_submitted_vouchers(client_a, agent_client, hotel_a, user_a):
    approved = _submit(agent_client, hotel_a)
    client_a.post(f"/member/approvals/{approved.id}/approve/")
    team = client_a.post("/member/bookings/save/", _form(hotel_a, "save", package_name="Team Umrah"))
    assert team.status_code == 302
    with tenant_context(bypass=True):
        team_b = Booking.all_tenants.get(package_name="Team Umrah")
    both = client_a.get("/member/bookings/").content.decode()
    assert approved.voucher_number in both and team_b.voucher_number in both
    agents_only = client_a.get("/member/bookings/", {"source": "agent"}).content.decode()
    assert approved.voucher_number in agents_only and team_b.voucher_number not in agents_only
    team_only = client_a.get("/member/bookings/", {"source": "team"}).content.decode()
    assert team_b.voucher_number in team_only and approved.voucher_number not in team_only
    assert "agent_a" in agents_only                             # who submitted it is shown on the row


def test_preview_of_a_pending_voucher_is_for_the_team_only(client_a, client_b, agent_client, hotel_a):
    b = _submit(agent_client, hotel_a)
    assert client_a.get(f"/member/bookings/{b.id}/voucher/").status_code == 200
    assert client_b.get(f"/member/bookings/{b.id}/voucher/").status_code == 404
    assert agent_client.get(f"/agent/vouchers/{b.id}/view/").status_code == 200


def test_dashboard_counts_the_real_approvals_queue(client_a, agent_client, hotel_a):
    _submit(agent_client, hotel_a)
    _submit(agent_client, hotel_a)
    page = client_a.get("/member/dashboard/")
    assert page.status_code == 200
    assert page.context["pending_vouchers"] == 2
