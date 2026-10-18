"""Settings → My profile: details, picture, password and language for whoever is signed in."""
import io

from PIL import Image


def _png(size=(600, 300)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, format="PNG")
    buf.seek(0)
    buf.name = "me.png"
    return buf


def test_profile_is_the_first_settings_tab_for_everyone(client_a, agency_a):
    from django.test import Client

    from accounts.models import User
    owner_page = client_a.get("/member/settings/me/").content.decode()
    assert owner_page.index('href="/member/settings/me/"') < owner_page.index('href="/profile/"')  # My profile, then Company profile
    agent = User.objects.create(username="plain.agent", agency=agency_a, role="agent")
    c = Client()
    c.force_login(agent)
    page = c.get("/member/settings/me/")
    assert page.status_code == 200 and "Change password" in page.content.decode()
    assert 'href="/profile/"' not in page.content.decode()  # company settings stay owner-only


def test_edit_own_details_and_username_must_stay_unique(client_a, user_a, user_b):
    r = client_a.post("/member/settings/me/", {"action": "details", "username": "owner.renamed", "first_name": "Ayesha", "last_name": "Khan", "email": "a@x.com", "phone": "0300"})
    assert r.status_code == 302
    user_a.refresh_from_db()
    assert (user_a.username, user_a.first_name, user_a.phone) == ("owner.renamed", "Ayesha", "0300")
    client_a.post("/member/settings/me/", {"action": "details", "username": user_b.username})
    user_a.refresh_from_db()
    assert user_a.username == "owner.renamed"  # taken by someone else


def test_upload_and_remove_a_profile_picture(client_a, user_a, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    client_a.post("/member/settings/me/", {"action": "avatar", "avatar": _png()})
    user_a.refresh_from_db()
    assert user_a.avatar
    with Image.open(user_a.avatar.path) as img:
        assert img.size == (320, 320)  # square-cropped and shrunk
    assert user_a.avatar.url in client_a.get("/member/settings/me/").content.decode()
    client_a.post("/member/settings/me/", {"action": "remove_avatar"})
    user_a.refresh_from_db()
    assert not user_a.avatar


def test_a_non_image_is_refused(client_a, user_a, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    fake = io.BytesIO(b"not an image")
    fake.name = "x.png"
    client_a.post("/member/settings/me/", {"action": "avatar", "avatar": fake})
    user_a.refresh_from_db()
    assert not user_a.avatar


def test_change_password_needs_the_current_one_and_keeps_you_signed_in(client_a, user_a):
    user_a.set_password("old-pass-123")
    user_a.save()
    client_a.force_login(user_a)
    client_a.post("/member/settings/me/", {"action": "password", "current_password": "wrong", "new_password": "brand-new-456", "confirm_password": "brand-new-456"})
    user_a.refresh_from_db()
    assert user_a.check_password("old-pass-123")
    client_a.post("/member/settings/me/", {"action": "password", "current_password": "old-pass-123", "new_password": "brand-new-456", "confirm_password": "brand-new-456"})
    user_a.refresh_from_db()
    assert user_a.check_password("brand-new-456")
    assert client_a.get("/member/settings/me/").status_code == 200  # still signed in


def test_language_is_saved_from_the_profile_and_old_url_redirects(client_a, user_a):
    r = client_a.post("/settings/language/", {"language": "ur"})
    assert r.status_code == 302 and r["Location"] == "/member/settings/me/"
    user_a.refresh_from_db()
    assert user_a.preferred_language == "ur"
    assert client_a.get("/settings/language/")["Location"] == "/member/settings/me/"
