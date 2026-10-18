"""Packages: API create/edit/validation, tenant isolation, and the page."""
from decimal import Decimal
from urllib.parse import urlencode

from utils.tenancy import tenant_context


def _payload(**kw):
    data = {
        "name": "15 Days Economy Umrah", "package_type": "umrah",
        "makkah_nights": "10", "madina_nights": "5",
        "inclusions": ["visa", "hotel", "ticket"],
        "price_quad": "285000", "price_double": "340000",
        "departure_date": "2026-12-01", "return_date": "2026-12-16",
        "total_seats": "40", "is_active": "true",
    }
    data.update(kw)
    return data


def test_create_and_edit_package(client_a, agency_a, hotel_a):
    from member.models import Package
    r = client_a.post("/api/v1/packages/", _payload(makkah_hotel=hotel_a.id))
    assert r.status_code == 201, r.content
    pid = r.json()["id"]
    with tenant_context(agency_id=agency_a.id):
        p = Package.objects.get(pk=pid)
    assert p.inclusions == ["visa", "ticket", "hotel"]  # stored in catalogue order
    assert p.total_nights == 15
    assert p.starting_price == Decimal("285000")
    assert p.makkah_hotel_id == hotel_a.id

    # Unchecking every inclusion via a full PUT clears them.
    data = _payload(name="Renamed", is_active="false")
    data.pop("inclusions")
    r = client_a.generic(
        "PUT", f"/api/v1/packages/{pid}/",
        data=urlencode(data),
        content_type="application/x-www-form-urlencoded",
    )
    assert r.status_code == 200, r.content
    with tenant_context(agency_id=agency_a.id):
        p.refresh_from_db()
    assert p.name == "Renamed" and p.inclusions == [] and p.is_active is False


def test_package_requires_a_price_and_valid_dates(client_a):
    r = client_a.post("/api/v1/packages/", _payload(price_quad="", price_double=""))
    assert r.status_code == 400 and "price_quad" in r.json()
    r = client_a.post("/api/v1/packages/", _payload(return_date="2026-11-01"))
    assert r.status_code == 400 and "return_date" in r.json()


def test_cannot_attach_another_agencys_hotel(client_a, hotel_b):
    r = client_a.post("/api/v1/packages/", _payload(makkah_hotel=hotel_b.id))
    assert r.status_code == 400 and "makkah_hotel" in r.json()


def test_packages_are_private_to_each_agency(client_a, client_b):
    assert client_a.post("/api/v1/packages/", _payload()).status_code == 201
    assert client_b.get("/api/v1/packages/").json()["count"] == 0


def test_packages_page_renders(client_a, hotel_a):
    client_a.post("/api/v1/packages/", _payload(makkah_hotel=hotel_a.id))
    r = client_a.get("/member/packages/")
    assert r.status_code == 200
    body = r.content.decode()
    assert "15 Days Economy Umrah" in body and "Hotel A" in body
    htmx = client_a.get("/member/packages/", {"q": "nothing-matches"}, HTTP_HX_REQUEST="true")
    assert b"No matches" in htmx.content


def test_package_has_the_details_of_a_real_offer(client_a, agency_a, user_a, hotel_a):
    """Group leader, hotel distances, outbound + return flight, baggage, sharing + child/infant prices, extra services."""
    from member.models import Flight, Package
    with tenant_context(agency_id=agency_a.id):
        out = Flight.objects.create(agency=agency_a, created_by=user_a, airline="Saudia", flight_number="SV735",
                                    departure_city="Lahore", arrival_city="Jeddah", sale_price=0, purchase_price=0)
        back = Flight.objects.create(agency=agency_a, created_by=user_a, airline="Saudia", flight_number="SV738",
                                     departure_city="Jeddah", arrival_city="Lahore", sale_price=0, purchase_price=0)
    r = client_a.post("/api/v1/packages/", _payload(
        name="21 Days Umrah Package — October 2026", group_leader="Qari Muhammad Saleem Asim",
        makkah_hotel=hotel_a.id, makkah_nights="12", makkah_distance="700", makkah_shuttle="true",
        madina_nights="8", madina_distance="200", flight=out.id, return_flight=back.id, baggage="23 + 23 kg", return_baggage="30 kg",
        price_sharing="305000", price_quad="316199", price_triple="341900", price_double="393199",
        price_child="250000", price_infant="40000", inclusions=["taif", "ihram", "zamzam", "private_bus"],
        extra_services="Local ziyarat by bus\nScarf and shoe bag"))
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["code"].startswith("UP-1") and body["group_leader"] == "Qari Muhammad Saleem Asim"
    with tenant_context(agency_id=agency_a.id):
        p = Package.objects.get(pk=body["id"])
    assert p.total_nights == 20 and p.makkah_distance == 700 and p.makkah_shuttle and not p.madina_shuttle
    assert p.return_flight_id == back.id and p.baggage == "23 + 23 kg" and p.return_baggage == "30 kg"
    assert p.starting_price == Decimal("305000") and [label for label, _p in p.sharing_prices][:2] == ["Sharing", "Double"]
    assert p.get_inclusions_display()[-2:] == ["Local ziyarat by bus", "Scarf and shoe bag"]
    assert "Umrah from Taif" in p.get_inclusions_display() and "Private luxury bus" in p.get_inclusions_display()

    # The catalogue table shows only the main info ...
    table = client_a.get("/member/packages/", HTTP_HX_REQUEST="true").content.decode()      # just the table
    for text in (p.code, "21 Days Umrah Package", "Hotel A", "305,000"):
        assert text in table, text
    assert "SV738" not in table and "Qari Muhammad Saleem Asim" not in table and "Scarf" not in table   # the rest is behind View
    assert 'class="vx vx--view"' in table and 'class="vx vx--edit"' in table and ">Edit</button>" not in table
    page = client_a.get("/member/packages/").content.decode()
    assert "Upcoming departures" not in page and "Ready-made Umrah" not in page
    assert "pkg-drawer" in page and 'aria-label="Package type"' not in page            # View is a side drawer; no type filter
    # The View button opens everything about the package.
    detail = client_a.get(f"/member/packages/{p.id}/").content.decode()
    for text in (p.code, "Qari Muhammad Saleem Asim", "700 m from the Haram", "shuttle", "SV738", "23 + 23 kg", "Sharing",
                 "Child without bed", "Infant", "Umrah from Taif", "Local ziyarat by bus", "Scarf and shoe bag"):
        assert text in detail, text
    # ... and the voucher form's package picker fills both flights.
    form = client_a.get("/member/bookings/new/").content.decode()
    assert f'"return_flight": {back.id}' in form or f'"return_flight":{back.id}' in form


def test_new_packages_get_their_own_code(client_a):
    first = client_a.post("/api/v1/packages/", _payload()).json()
    second = client_a.post("/api/v1/packages/", _payload(name="Second")).json()
    assert first["code"] and second["code"] and first["code"] != second["code"]


def test_return_flight_must_belong_to_the_agency(client_a, agency_b, user_b):
    from member.models import Flight
    with tenant_context(agency_id=agency_b.id):
        other = Flight.objects.create(agency=agency_b, created_by=user_b, airline="Other", sale_price=0, purchase_price=0,
                                      departure_city="A", arrival_city="B")
    r = client_a.post("/api/v1/packages/", _payload(return_flight=other.id))
    assert r.status_code == 400 and "return_flight" in r.json()


def test_package_details_are_private_to_the_agency(client_a, client_b):
    pid = client_a.post("/api/v1/packages/", _payload()).json()["id"]
    assert client_a.get(f"/member/packages/{pid}/").status_code == 200
    assert client_b.get(f"/member/packages/{pid}/").status_code == 404


def test_custom_inclusions_are_saved_shown_and_offered_again(client_a):
    r = client_a.post("/api/v1/packages/", _payload(extra_services="Local ziyarat by bus\nHot lunch box"))
    assert r.status_code == 201, r.content
    assert r.json()["extra_services"] == "Local ziyarat by bus\nHot lunch box"
    page = client_a.get("/member/packages/").content.decode()
    # items already used by this agency come back as chips that can be ticked on a new package
    assert 'class="pkg-custom" value="Local ziyarat by bus"' in page
    assert 'class="pkg-custom" value="Hot lunch box"' in page
    assert "More options" not in page and "Other services" not in page
