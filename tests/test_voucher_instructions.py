"""Voucher instructions: managed on Contacts, printed at the end of every voucher."""
from member.instruction_views import STANDARD_UMRAH
from utils.tenancy import tenant_context


def _texts(agency):
    from member.models import VoucherInstruction
    with tenant_context(agency_id=agency.id):
        return list(VoucherInstruction.objects.order_by("sort_order", "id").values_list("text", "is_active"))


def test_manage_instructions(client_a, agency_a):
    from member.models import VoucherInstruction
    for t in ("First rule", "Second rule", "Third rule"):
        assert client_a.post("/member/contacts/instructions/add/", {"text": t}).status_code == 302
    with tenant_context(agency_id=agency_a.id):
        first, second, third = VoucherInstruction.objects.order_by("sort_order")
    client_a.post(f"/member/contacts/instructions/{third.id}/move/", {"direction": "up"})
    assert [t for t, _a in _texts(agency_a)] == ["First rule", "Third rule", "Second rule"]
    client_a.post(f"/member/contacts/instructions/{first.id}/update/", {"text": "First rule (edited)"})
    client_a.post(f"/member/contacts/instructions/{second.id}/update/", {"is_active": "0"})
    client_a.post(f"/member/contacts/instructions/{third.id}/delete/")
    assert _texts(agency_a) == [("First rule (edited)", True), ("Second rule", False)]
    page = client_a.get("/member/contacts/").content.decode()
    assert "Voucher instructions" in page and "First rule (edited)" in page and "Hidden from vouchers" in page


def test_standard_set_is_added_once(client_a, agency_a):
    client_a.post("/member/contacts/instructions/standard/")
    client_a.post("/member/contacts/instructions/standard/")
    assert len(_texts(agency_a)) == len(STANDARD_UMRAH)


def test_other_agency_cannot_touch(client_a, client_b, agency_a):
    from member.models import VoucherInstruction
    client_a.post("/member/contacts/instructions/add/", {"text": "Private"})
    with tenant_context(agency_id=agency_a.id):
        item = VoucherInstruction.objects.get()
    assert client_b.post(f"/member/contacts/instructions/{item.id}/delete/").status_code == 404
    assert _texts(agency_a) == [("Private", True)]


def test_printed_on_voucher(client_a, agency_a, booking_a):
    client_a.post("/member/contacts/instructions/add/", {"text": "Keep your voucher with you"})
    client_a.post("/member/contacts/instructions/add/", {"text": STANDARD_UMRAH[0]})
    from member.models import VoucherInstruction
    with tenant_context(agency_id=agency_a.id):
        hidden = VoucherInstruction.objects.create(agency=agency_a, text="Hidden one", is_active=False)
    body = client_a.get(f"/member/bookings/{booking_a.id}/voucher/").content.decode()
    assert "Special Instructions" in body and "Keep your voucher with you" in body
    assert STANDARD_UMRAH[0] in body and 'dir="auto"' in body and hidden.text not in body


def test_pdf_still_generates_with_urdu(client_a, booking_a):
    client_a.post("/member/contacts/instructions/standard/")
    r = client_a.get(f"/member/bookings/{booking_a.id}/voucher.pdf")
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf" and r.content[:4] == b"%PDF"


def test_contacts_search_matches_name_city_role_phone_and_notes(client_a, agency_a, user_a):
    from member.models import ContactInstruction
    from utils.tenancy import tenant_context
    with tenant_context(agency_id=agency_a.id):
        ContactInstruction.objects.create(agency=agency_a, created_by=user_a, city="Makkah", role="Group Leader",
                                          contact_name="Ahmed Raza", phone_number="+966 50 123 4501", notes="night shift")
        ContactInstruction.objects.create(agency=agency_a, created_by=user_a, city="Jeddah", role="Airport Representative",
                                          contact_name="Salman Tariq", phone_number="+966 53 890 1208", notes="")

    def found(q):
        body = client_a.get("/member/contacts/", {"q": q}, HTTP_HX_REQUEST="true").content.decode()
        return ("Ahmed Raza" in body, "Salman Tariq" in body)

    assert found("ahmed") == (True, False)            # name
    assert found("jedd") == (False, True)             # city
    assert found("representative") == (False, True)   # role
    assert found("123 4501") == (True, False)         # phone
    assert found("night") == (True, False)            # notes
    page = client_a.get("/member/contacts/").content.decode()
    assert "All cities" not in page and "contacts-city-filter" not in page and "Madina" not in page.split("Directory")[0]
