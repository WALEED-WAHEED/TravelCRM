"""Add a teammate: the form renders with a role preview, creates the user, and re-renders on errors."""
import json
import re

from rbac.models import Role


def _summary(response):
    raw = re.search(r'<script id="role-summary" type="application/json">(.*?)</script>', response.content.decode(), re.S)
    assert raw, "role summary missing from the page"
    return json.loads(raw.group(1))


def test_invite_page_previews_what_each_role_can_do(client_a):
    r = client_a.get("/member/team/invite/")
    assert r.status_code == 200
    summary = _summary(r)
    owner = Role.objects.get(agency__isnull=True, name="Owner")
    read_only = Role.objects.get(agency__isnull=True, name="Read-only")
    assert {c["level"] for c in summary[str(owner.id)]["caps"]} == {"manage"}
    assert {c["level"] for c in summary[str(read_only.id)]["caps"]} == {"view"}
    assert "Back to team" in r.content.decode()


def test_invite_creates_the_user_with_the_chosen_role(client_a, agency_a):
    from accounts.models import User

    role = Role.objects.get(agency__isnull=True, name="Agent")
    r = client_a.post("/member/team/invite/", {
        "username": "new.teammate", "email": "n@example.com", "password": "longenough1", "role_id": role.id,
    })
    assert r.status_code == 302 and r["Location"].endswith("/member/team/")
    u = User.objects.get(username="new.teammate")
    assert u.agency_id == agency_a.id and u.custom_role_id == role.id and u.check_password("longenough1")


def test_invite_with_a_short_password_shows_the_form_again(client_a):
    role = Role.objects.get(agency__isnull=True, name="Agent")
    r = client_a.post("/member/team/invite/", {"username": "short.pw", "password": "abc", "role_id": role.id})
    assert r.status_code == 200
    assert "short.pw" in r.content.decode()  # the entered username is kept
    assert _summary(r)  # and the role preview still works
