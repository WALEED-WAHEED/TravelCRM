import json

import pytest
from django.test import Client

from member.models import Booking, BookingNote
from utils.tenancy import tenant_context


def _post(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def test_add_list_and_delete_notes(client_a, booking_a, user_a):
    url = f"/member/bookings/{booking_a.id}/notes/"
    assert _post(client_a, url, {"text": "   "}).status_code == 400

    r = _post(client_a, url, {"text": "Client wants a quad room\nAsk the hotel"})
    assert r.status_code == 201
    note = r.json()["note"]
    assert note["author"] == user_a.username and note["mine"] is True and note["at"] and note["initial"]

    listed = client_a.get(url).json()["notes"]
    assert [n["text"] for n in listed] == ["Client wants a quad room\nAsk the hotel"]

    # The edit page hands the same notes to the pop-up.
    page = client_a.get(f"/member/bookings/{booking_a.id}/").content.decode()
    assert 'id="vn-data"' in page and "Client wants a quad room" in page

    assert client_a.post(f"/member/notes/{note['id']}/delete/").status_code == 200
    assert client_a.get(url).json()["notes"] == []


def test_only_the_author_can_delete(client_a, agency_a, booking_a):
    from accounts.models import User
    with tenant_context(bypass=True):
        other = User.objects.create_user(username="colleague", password="TestPass123!", role="member", agency=agency_a)
    r = _post(client_a, f"/member/bookings/{booking_a.id}/notes/", {"text": "mine"})
    nid = r.json()["note"]["id"]
    c2 = Client()
    c2.force_login(other)
    listed = c2.get(f"/member/bookings/{booking_a.id}/notes/").json()["notes"]
    assert listed[0]["mine"] is False
    assert c2.post(f"/member/notes/{nid}/delete/").status_code == 403
    with tenant_context(agency_id=agency_a.id):
        assert BookingNote.objects.filter(pk=nid).exists()


def test_notes_are_private_to_the_agency(client_a, client_b, agency_a, agency_b, booking_a, booking_b):
    _post(client_a, f"/member/bookings/{booking_a.id}/notes/", {"text": "agency A secret"})
    # Agency B can neither read nor write notes on agency A's voucher ...
    assert client_b.get(f"/member/bookings/{booking_a.id}/notes/").status_code == 404
    assert _post(client_b, f"/member/bookings/{booking_a.id}/notes/", {"text": "intruder"}).status_code == 404
    with tenant_context(agency_id=agency_a.id):
        note_id = BookingNote.objects.get().id
    assert client_b.post(f"/member/notes/{note_id}/delete/").status_code == 404
    # ... and the ORM tenant filter hides them as well.
    with tenant_context(agency_id=agency_b.id):
        assert BookingNote.objects.count() == 0


@pytest.mark.django_db
def test_notes_written_on_the_create_page_are_saved_with_the_voucher(client_a, agency_a, user_a):
    r = client_a.post("/member/bookings/save/", {
        "save_as": "draft", "package_name": "With notes", "pax_adults": "0", "pax_children": "0", "pax_infants": "0",
        "mutamers_json": "[]", "hotels_json": "[]",
        "notes_json": json.dumps(["first note", "second note"]),
    })
    assert r.status_code == 302
    with tenant_context(agency_id=agency_a.id):
        b = Booking.objects.get(package_name="With notes")
        texts = [n.text for n in b.voucher_notes.order_by("created_at", "id")]
        assert texts == ["first note", "second note"]
        assert all(n.author_id == user_a.id for n in b.voucher_notes.all())
