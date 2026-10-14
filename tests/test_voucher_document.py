import json

from member.models import Booking, Flight, Hotel, Transport
from utils.tenancy import tenant_context


def test_create_voucher_and_print_it(client_a, agency_a, user_a):
    with tenant_context(agency_id=agency_a.id):
        hotel = Hotel.objects.create(agency=agency_a, created_by=user_a, name="Mather Al Jiwar", city="Makkah",
                                     sale_price=0, purchase_price=0)
        flight = Flight.objects.create(agency=agency_a, created_by=user_a, airline="Saudia", flight_number="SV-733",
                                       departure_city="Lahore", arrival_city="Jeddah", departure_airport="LHE",
                                       arrival_airport="JED", sale_price=0, purchase_price=0)
        transport = Transport.objects.create(agency=agency_a, created_by=user_a, name="Company Transport", capacity=40,
                                             sale_price=0, purchase_price=0)

    mutamers = [
        {"name": "Hassan Ahmad", "passport_number": "JA1185471", "gender": "male", "pax_type": "adult", "bed": True,
         "mofa_number": "M1", "group_number": "G1", "visa_number": "V1", "pnr": "P1"},
        {"name": "Ali Hassan", "passport_number": "JW1201241", "gender": "male", "pax_type": "child", "bed": False},
    ]
    r = client_a.post("/member/bookings/save/", {
        "package_name": "20 Standard",
        "pax_adults": "1", "pax_children": "1", "pax_infants": "0", "total_beds": "1", "status": "confirmed",
        "total_amount": "0", "total_price": "0",
        "mutamers_json": json.dumps(mutamers),
        "hotels_json": json.dumps([{"hotel_id": hotel.id, "check_in": "2026-10-25", "check_out": "2026-11-03",
                                    "room_type": "Sharing (Gender)", "meal_plan": "RO", "view": "Standard"}]),
        "flights_json": json.dumps([{"flight_id": flight.id, "flight_type": "outbound",
                                     "departure_at": "2026-10-25T16:20", "arrival_at": "2026-10-25T19:30"}]),
        "transports_json": json.dumps([{"transport_id": transport.id, "travel_date": "2026-10-25",
                                        "transporter": "Company Transport", "vehicle_type": "Economy By Bus",
                                        "description": "JED-MAK-MED-MAK-JED"}]),
    })
    assert r.status_code == 302
    with tenant_context(agency_id=agency_a.id):
        b = Booking.objects.get(package_name="20 Standard")
        m = list(b.booking_mutamers.order_by("id"))
        assert [x.pax_type for x in m] == ["adult", "child"] and m[0].mofa_number == "M1" and m[1].bed is False
        f = b.flights.get()
        assert f.departure_at is not None and f.departure_at.hour == 16

    page = client_a.get(f"/member/bookings/{b.id}/voucher/").content.decode()
    for text in ("HASSAN AHMAD", "Voucher No:", "MATHER AL JIWAR", "Total Nights:", "LHE-JED", "SV-733",
                 "JED-MAK-MED-MAK-JED", "data:image/png;base64,"):
        assert text in page, text
    pdf = client_a.get(f"/member/bookings/{b.id}/voucher.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_create_page_renders(client_a):
    r = client_a.get("/member/bookings/new/")
    assert r.status_code == 200
    body = r.content.decode()
    assert "Hotel Voucher" in body and "Departure" in body and "Save as draft" in body and "Office use" not in body


def test_edit_page_uses_voucher_layout_and_saves(client_a, agency_a, user_a):
    with tenant_context(agency_id=agency_a.id):
        hotel = Hotel.objects.create(agency=agency_a, created_by=user_a, name="Miramar", city="Madinah",
                                     sale_price=0, purchase_price=0)
    client_a.post("/member/bookings/save/", {
        "package_name": "10 Days", "pax_adults": "1", "status": "draft",
        "total_amount": "0", "total_price": "0",
        "mutamers_json": json.dumps([{"name": "Fozia Bibi", "passport_number": "KX3117792", "gender": "female",
                                      "pax_type": "adult", "bed": True, "mofa_number": "MF9"}]),
        "hotels_json": json.dumps([{"hotel_id": hotel.id, "check_in": "2026-11-03", "check_out": "2026-11-11",
                                    "room_type": "Quad", "meal_plan": "BB", "view": "Standard"}]),
    })
    with tenant_context(agency_id=agency_a.id):
        b = Booking.objects.get(package_name="10 Days")
    page = client_a.get(f"/member/bookings/{b.id}/").content.decode()
    for text in ("Hotel Voucher", "Fozia Bibi", "KX3117792", "MF9", 'value="Quad" selected', "Save as draft",
                 f'name="worksheet_booking_id" value="{b.id}"'):
        assert text in page, text
    # Saving from the edit page updates the same voucher (no new number).
    r = client_a.post("/member/bookings/save/", {
        "worksheet_booking_id": str(b.id), "package_name": "10 Days", "pax_adults": "1",
        "status": "confirmed", "total_amount": "0", "total_price": "0",
        "mutamers_json": json.dumps([{"name": "Fozia Bibi", "passport_number": "KX3117792", "pax_type": "adult",
                                      "bed": True, "mofa_number": "MF9-NEW"}]),
        "hotels_json": "[]",
    })
    assert r.status_code == 302 and r["Location"].endswith(f"/member/bookings/{b.id}/")
    with tenant_context(agency_id=agency_a.id):
        b.refresh_from_db()
        assert b.status == "confirmed" and Booking.objects.filter(package_name="10 Days").count() == 1
        assert b.booking_mutamers.get().mofa_number == "MF9-NEW"


def test_save_as_draft_and_save_voucher_buttons(client_a, agency_a, user_a):
    # "Save as draft" works even with nothing filled in yet.
    r = client_a.post("/member/bookings/save/", {"save_as": "draft", "package_name": "Draft only",
                                                   "pax_adults": "0", "pax_children": "0", "pax_infants": "0",
                                                   "mutamers_json": "[]", "hotels_json": "[]"})
    assert r.status_code == 302
    with tenant_context(agency_id=agency_a.id):
        d = Booking.objects.get(package_name="Draft only")
        assert d.status == "draft" and d.pax_adults + d.pax_children + d.pax_infants == 0

    # "Save voucher" needs a traveller and makes the voucher final (confirmed).
    refused = client_a.post("/member/bookings/save/", {"save_as": "save", "package_name": "No travellers",
                                                         "pax_adults": "0", "pax_children": "0", "pax_infants": "0",
                                                         "mutamers_json": "[]", "hotels_json": "[]"})
    assert refused.status_code == 302
    with tenant_context(agency_id=agency_a.id):
        assert not Booking.objects.filter(package_name="No travellers").exists()
    ok = client_a.post("/member/bookings/save/", {
        "save_as": "save", "worksheet_booking_id": str(d.id), "package_name": "Draft only", "pax_adults": "1",
        "mutamers_json": json.dumps([{"name": "Ali Khan", "pax_type": "adult", "bed": True}]), "hotels_json": "[]"})
    assert ok.status_code == 302
    with tenant_context(agency_id=agency_a.id):
        d.refresh_from_db()
        assert d.status == "confirmed" and d.booking_mutamers.count() == 1
        # An existing note and price are untouched by a save from the (note-less, price-less) form.
        d.notes, d.total_price = "keep me", 500
        d.save()
    client_a.post("/member/bookings/save/", {
        "save_as": "save", "worksheet_booking_id": str(d.id), "package_name": "Draft only", "pax_adults": "1",
        "mutamers_json": json.dumps([{"name": "Ali Khan", "pax_type": "adult", "bed": True}]), "hotels_json": "[]"})
    with tenant_context(agency_id=agency_a.id):
        d.refresh_from_db()
        assert d.notes == "keep me" and d.total_price == 500


def _saved_voucher(client, **extra):
    data = {"save_as": "save", "package_name": "20 Standard", "pax_adults": "2",
            "mutamers_json": json.dumps([{"name": "Hassan Ahmad", "passport_number": "JA1185471", "pax_type": "adult", "bed": True},
                                         {"name": "Malaika Ameen", "passport_number": "JW1201241", "pax_type": "adult", "bed": True}]),
            "hotels_json": "[]"}
    data.update(extra)
    client.post("/member/bookings/save/", data)
    return Booking.all_tenants.get(package_name=data["package_name"])


def test_vouchers_table_shows_the_form_fields_and_searches_them(client_a, agency_a, user_a):
    with tenant_context(agency_id=agency_a.id):
        hotel = Hotel.objects.create(agency=agency_a, created_by=user_a, name="Miramar", city="Madinah",
                                     sale_price=0, purchase_price=0)
    client_a.post("/member/bookings/save/", {
        "save_as": "save", "package_name": "Table test", "pax_adults": "2",
        "mutamers_json": json.dumps([{"name": "Hassan Ahmad", "passport_number": "JA1185471", "pax_type": "adult"},
                                     {"name": "Malaika Ameen", "passport_number": "JW1201241", "pax_type": "adult"}]),
        "hotels_json": json.dumps([{"hotel_id": hotel.id, "check_in": "2026-10-25", "check_out": "2026-11-03"}]),
    })
    page = client_a.get("/member/bookings/").content.decode()
    for text in ("Hassan Ahmad", "JA1185471", "+1 more", "Table test", "25 Oct → 03 Nov 2026", "9 nights", "Saved"):
        assert text in page, text
    assert "Total (PKR)" not in page and "Client" not in page.split("<thead>")[1].split("</thead>")[0]
    # Search by a travelling family member's passport finds the voucher; an unknown one finds nothing.
    assert "Table test" in client_a.get("/member/bookings/", {"q": "JW1201241"}).content.decode()
    assert "Table test" not in client_a.get("/member/bookings/", {"q": "ZZ9999"}).content.decode()


def test_delete_voucher_with_confirmation_rules(client_a, client_b, agency_a, user_a):
    b = _saved_voucher(client_a)
    page = client_a.get("/member/bookings/").content.decode()
    assert f'data-delete="{b.id}"' in page and "Delete this voucher?" in page and 'id="del-modal"' in page
    # Only POST deletes; another agency can't touch it.
    assert client_a.get(f"/member/bookings/{b.id}/delete/").status_code == 405
    assert client_b.post(f"/member/bookings/{b.id}/delete/").status_code == 404
    with tenant_context(agency_id=agency_a.id):
        assert Booking.objects.filter(pk=b.id).exists()
        # Money recorded against the voucher protects it.
        from member.models import BookingPayment
        BookingPayment.objects.create(booking=b, agent=user_a, amount=100, status="paid", idempotency_key="k-del-1")
    r = client_a.post(f"/member/bookings/{b.id}/delete/", follow=True)
    assert "can&#x27;t be deleted" in r.content.decode() or "can't be deleted" in r.content.decode()
    with tenant_context(agency_id=agency_a.id):
        assert Booking.objects.filter(pk=b.id).exists()
        # Recording a payment also writes a ledger entry; both protect the voucher.
        from member.models import LedgerEntry
        BookingPayment.objects.all().delete()
        assert b.ledger_entries.exists()
        LedgerEntry.objects.all().delete()
    r = client_a.post(f"/member/bookings/{b.id}/delete/")
    assert r.status_code == 302
    with tenant_context(agency_id=agency_a.id):
        assert not Booking.objects.filter(pk=b.id).exists()


def test_voucher_without_a_package_reads_as_a_custom_trip(client_a, agency_a, user_a):
    with tenant_context(agency_id=agency_a.id):
        hotel = Hotel.objects.create(agency=agency_a, created_by=user_a, name="Miramar", city="Madinah",
                                     sale_price=0, purchase_price=0)
    client_a.post("/member/bookings/save/", {
        "save_as": "save", "package_name": "", "pax_adults": "1",
        "mutamers_json": json.dumps([{"name": "Solo Traveller", "pax_type": "adult"}]),
        "hotels_json": json.dumps([{"hotel_id": hotel.id, "check_in": "2026-11-01", "check_out": "2026-11-05"}]),
    })
    page = client_a.get("/member/bookings/").content.decode()
    assert "Custom trip" in page and "Madinah" in page
    with tenant_context(agency_id=agency_a.id):
        b = Booking.objects.get(booking_mutamers__name="Solo Traveller")
    assert "Custom trip" in client_a.get(f"/member/bookings/{b.id}/voucher/").content.decode()


def test_flight_class_is_chosen_on_the_voucher_and_printed(client_a, agency_a, user_a):
    with tenant_context(agency_id=agency_a.id):
        flight = Flight.objects.create(agency=agency_a, created_by=user_a, airline="Saudia", flight_number="SV-734",
                                       departure_city="Lahore", arrival_city="Jeddah", sale_price=0, purchase_price=0)
    # The catalogue no longer asks for a class ...
    page = client_a.get("/member/flights/").content.decode()
    assert 'name="flight_class"' not in page and "flight-class" not in page
    assert 'name="sale_price"' in page and 'name="purchase_price"' in page and 'name="airline"' in page   # the rest of the form is intact
    # ... the voucher form does, per flight ...
    form = client_a.get("/member/bookings/new/").content.decode()
    assert "js-class" in form and 'value="business"' in form
    r = client_a.post("/member/bookings/save/", {
        "save_as": "save", "package_name": "Class test", "pax_adults": "1",
        "mutamers_json": json.dumps([{"name": "Ali Khan", "passport_number": "AB1", "pax_type": "adult"}]),
        "flights_json": json.dumps([
            {"flight_id": flight.id, "flight_type": "outbound", "flight_class": "business", "departure_at": "2026-11-03T04:45"},
            {"flight_id": flight.id, "flight_type": "return", "flight_class": "bogus", "departure_at": "2026-11-14T23:30"}]),
    })
    assert r.status_code == 302
    with tenant_context(agency_id=agency_a.id):
        b = Booking.objects.get(package_name="Class test")
        classes = {f.flight_type: f.flight_class for f in b.flights.all()}
    assert classes == {"outbound": "business", "return": "economy"}        # unknown values fall back to economy
    # ... it is remembered when the voucher is edited and printed on the voucher.
    assert 'value="business" selected' in client_a.get(f"/member/bookings/{b.id}/").content.decode()
    printed = client_a.get(f"/member/bookings/{b.id}/voucher/").content.decode()
    assert "Business" in printed and "Economy" in printed
