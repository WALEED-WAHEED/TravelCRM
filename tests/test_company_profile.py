"""Company profile: the company and its Shirka (partner) details are saved and shown back."""
from django.urls import reverse

from system_config.models import AgencyBranding
from utils.tenancy import tenant_context


def test_shirka_contact_details_are_saved_and_shown_back(client_a, agency_a):
    r = client_a.post(reverse("profile-update-branding"), {
        "company_name": "Nahd Travels", "shirka_company_name": "Noori Kaki Co.", "shirka_company_country": "Pakistan",
        "shirka_company_whatsapp": "03001234567", "shirka_company_phone": "042-111-222", "shirka_company_email": "info@noori.example",
        "shirka_company_website": "https://noori.example", "shirka_company_address": "12 Mall Road\nLahore",
    })
    assert r.status_code == 200, r.content
    with tenant_context(agency_id=agency_a.id):
        b = AgencyBranding.objects.get(agency=agency_a)
    assert (b.shirka_company_phone, b.shirka_company_email, b.shirka_company_website) == ("042-111-222", "info@noori.example", "https://noori.example")
    assert b.shirka_company_address == "12 Mall Road\nLahore"
    page = client_a.get("/profile/").content.decode()
    for value in ("042-111-222", "info@noori.example", "https://noori.example", "12 Mall Road"):
        assert value in page


def test_company_country_and_whatsapp_are_saved_like_the_partner_ones(client_a, agency_a):
    client_a.post(reverse("profile-update-branding"), {"company_name": "Nahd Travels", "company_country": "Pakistan", "company_whatsapp": "03001112222"})
    with tenant_context(agency_id=agency_a.id):
        b = AgencyBranding.objects.get(agency=agency_a)
    assert (b.company_country, b.company_whatsapp) == ("Pakistan", "03001112222")
    page = client_a.get("/profile/").content.decode()
    assert "Company country" in page and "Company WhatsApp" in page and "03001112222" in page
