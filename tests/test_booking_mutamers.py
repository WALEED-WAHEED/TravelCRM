"""
Travelers are entered directly on a booking (name/passport/visa/nationality/
gender/phone/email/family_label) — there's no separate Mutamer catalog to
pick from any more, so `_replace_booking_line_items` just wipes and
recreates `BookingMutamer` rows straight from the submitted JSON payload
on every save.
"""
import pytest

from utils.tenancy import tenant_context


@pytest.mark.django_db
def test_saving_a_booking_with_a_mutamers_payload_creates_matching_rows(booking_a):
    from member.views import _replace_booking_line_items

    agency = booking_a.agency
    payload = [
        {
            "name": "Amina Yusuf", "passport_number": "P1234567", "visa_number": "V1",
            "nationality": "Pakistani", "gender": "female", "phone": "0300-1112222",
            "email": "amina@example.com", "family_label": "Yusuf family",
        },
        {
            "name": "Bilal Yusuf", "passport_number": "P7654321",
            "nationality": "Pakistani", "gender": "male", "family_label": "Yusuf family",
        },
    ]
    with tenant_context(bypass=True):
        _replace_booking_line_items(agency, booking_a, [], [], [], payload, [])

        rows = list(booking_a.booking_mutamers.order_by("name"))
        assert len(rows) == 2
        amina, bilal = rows
        assert amina.name == "Amina Yusuf"
        assert amina.passport_number == "P1234567"
        assert amina.visa_number == "V1"
        assert amina.nationality == "Pakistani"
        assert amina.gender == "female"
        assert amina.phone == "0300-1112222"
        assert amina.email == "amina@example.com"
        assert amina.family_label == "Yusuf family"
        assert bilal.name == "Bilal Yusuf"
        assert bilal.passport_number == "P7654321"
        assert bilal.family_label == "Yusuf family"


@pytest.mark.django_db
def test_resaving_with_an_empty_payload_clears_existing_rows(booking_a):
    from member.views import _replace_booking_line_items

    agency = booking_a.agency
    with tenant_context(bypass=True):
        _replace_booking_line_items(
            agency, booking_a, [], [], [],
            [{"name": "Temp Traveler", "nationality": "Pakistani"}], [],
        )
        assert booking_a.booking_mutamers.count() == 1

        _replace_booking_line_items(agency, booking_a, [], [], [], [], [])
        assert booking_a.booking_mutamers.count() == 0


@pytest.mark.django_db
def test_a_row_with_a_blank_name_is_skipped(booking_a):
    from member.views import _replace_booking_line_items

    agency = booking_a.agency
    payload = [
        {"name": "", "nationality": "Pakistani"},
        {"name": "  ", "nationality": "Pakistani"},
        {"nationality": "Pakistani"},
    ]
    with tenant_context(bypass=True):
        _replace_booking_line_items(agency, booking_a, [], [], [], payload, [])
        assert booking_a.booking_mutamers.count() == 0
