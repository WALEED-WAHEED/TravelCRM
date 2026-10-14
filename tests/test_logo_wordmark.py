import io

from django.core.files.base import ContentFile
from PIL import Image

from system_config.models import AgencyBranding
from utils.tenancy import tenant_context


def _png(w, h):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (40, 100, 200)).save(buf, "PNG")
    return ContentFile(buf.getvalue())


def test_wide_logo_is_shown_alone_square_logo_gets_the_name(client_a, agency_a):
    with tenant_context(agency_id=agency_a.id):
        b, _ = AgencyBranding.objects.get_or_create(agency=agency_a, defaults={"company_name": "Acme Travels"})
        b.company_name = "Acme Travels"
        assert not b.logo_is_wordmark                           # no logo at all
        b.logo.save("wide.png", _png(600, 200), save=True)
        assert b.logo_is_wordmark
        b.logo.save("square.png", _png(200, 200), save=True)
        assert not b.logo_is_wordmark
    page = client_a.get("/member/dashboard/").content.decode()
    assert "topnav-brand__logo--icon" in page and "Acme Travels" in page   # icon logo -> name beside it
