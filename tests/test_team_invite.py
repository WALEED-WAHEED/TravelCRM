"""Add a teammate: the form renders with a role preview, creates the user, and re-renders on errors."""
import json
import re

from rbac.models import Role
from utils.tenancy import tenant_context


def _summary(response):
    raw = re.search(r'<script id="role-summary" type="application/json">(.*?)</script>', response.content.decode(), re.S)
    assert raw, "role summary missing from the page"
    return json.loads(raw.group(1))


def test_invite_page_previews_what_each_role_can_do(client_a, agency_a):
    r = client_a.get("/member/team/invite/")
    assert r.status_code == 200
    summary = _summary(r)
    owner = Role.all_tenants.get(agency=agency_a, name="Owner")
    read_only = Role.all_tenants.get(agency=agency_a, name="Read-only")
    assert {c["level"] for c in summary[str(owner.id)]["caps"]} == {"manage"}
    assert {c["level"] for c in summary[str(read_only.id)]["caps"]} == {"view"}
    assert "Back to team" in r.content.decode()


def test_invite_creates_the_user_with_the_chosen_role(client_a, agency_a):
    from accounts.models import User

    client_a.get("/member/team/invite/")  # the agency's own roles are created on first use
    role = Role.all_tenants.get(agency=agency_a, name="Agent")
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


def _teammate(agency, username="helper"):
    from accounts.models import User
    role = Role.objects.get(agency__isnull=True, name="Agent")
    return User.objects.create(username=username, agency=agency, role="agent", custom_role=role)


def test_team_page_lists_bookings_and_last_sign_in(client_a, agency_a, booking_a):
    r = client_a.get("/member/team/")
    page = r.content.decode()
    assert r.status_code == 200 and "Last sign-in" in page and "Bookings" in page
    assert [u.booking_count for u in r.context["staff"] if u.username == "owner_a"] == [1]


def test_deactivate_then_reactivate_a_teammate(client_a, agency_a):
    helper = _teammate(agency_a)
    client_a.post(f"/member/team/{helper.id}/deactivate/")
    helper.refresh_from_db()
    assert helper.is_active is False
    client_a.post(f"/member/team/{helper.id}/reactivate/")
    helper.refresh_from_db()
    assert helper.is_active is True


def test_delete_removes_the_teammate_but_keeps_everything_they_created(client_a, agency_a, user_a, booking_a):
    from accounts.models import User
    from member.models import Booking
    helper = _teammate(agency_a)
    with tenant_context(bypass=True):
        Booking.objects.filter(pk=booking_a.pk).update(agent=helper)
    r = client_a.post(f"/member/team/{helper.id}/delete/")
    assert r.status_code == 302
    helper.refresh_from_db()
    assert helper.deleted_at is not None and helper.is_active is False  # cannot sign in, hidden from the team
    assert helper.pk not in [u.pk for u in client_a.get("/member/team/").context["staff"]]
    with tenant_context(bypass=True):
        assert Booking.objects.get(pk=booking_a.pk).agent_id == helper.id  # history untouched
    # you cannot delete yourself
    client_a.post(f"/member/team/{user_a.id}/delete/")
    assert User.objects.get(pk=user_a.id).deleted_at is None


def _role(agency, name):
    return Role.all_tenants.get(agency=agency, name=name)


def test_roles_page_gives_the_agency_its_own_editable_roles(client_a, agency_a):
    helper = _teammate(agency_a)  # starts on the shared Agent template
    r = client_a.get("/member/roles/")
    assert {"Owner", "Manager", "Agent", "Read-only"} <= {row["role"].name for row in r.context["rows"]}
    helper.refresh_from_db()
    assert helper.custom_role_id == _role(agency_a, "Agent").id  # teammates move onto the agency's copy


def test_add_edit_and_delete_a_role(client_a, agency_a):
    client_a.get("/member/roles/")
    r = client_a.post("/member/roles/save/", {"name": "Accountant", "permissions": ["ledger:manage", "bookings:view"]})
    assert r.status_code == 302
    acc = _role(agency_a, "Accountant")
    assert {(p.capability, p.action) for p in acc.permissions.all()} == {("ledger", "manage"), ("ledger", "view"), ("bookings", "view")}
    # edit it: rename and change what it can do
    client_a.post("/member/roles/save/", {"role_id": acc.id, "name": "Senior accountant", "permissions": ["ledger:view"]})
    acc.refresh_from_db()
    assert acc.name == "Senior accountant" and {(p.capability, p.action) for p in acc.permissions.all()} == {("ledger", "view")}
    # duplicate names are refused
    client_a.post("/member/roles/save/", {"name": "agent", "permissions": []})
    assert Role.all_tenants.filter(agency=agency_a, name__iexact="agent").count() == 1
    # anyone holding it keeps working after it is deleted; their records are untouched
    helper = _teammate(agency_a)
    helper.custom_role = acc
    helper.save(update_fields=["custom_role"])
    client_a.post(f"/member/roles/{acc.id}/delete/")
    assert not Role.all_tenants.filter(pk=acc.id).exists()
    helper.refresh_from_db()
    assert helper.custom_role_id is None and helper.is_active


def test_standard_roles_can_be_deleted_too_but_not_your_own_or_the_last(client_a, agency_a, user_a):
    client_a.get("/member/roles/")
    mine = user_a.custom_role or _role(agency_a, "Owner")
    client_a.post(f"/member/roles/{mine.id}/delete/")
    assert Role.all_tenants.filter(pk=mine.id).exists()  # you are using it
    client_a.post(f"/member/roles/{_role(agency_a, 'Read-only').id}/delete/")
    assert not Role.all_tenants.filter(agency=agency_a, name="Read-only").exists()


def test_you_cannot_remove_your_own_team_access(client_a, agency_a, user_a):
    client_a.get("/member/roles/")
    user_a.refresh_from_db()
    mine = user_a.custom_role
    assert mine is not None
    client_a.post("/member/roles/save/", {"role_id": mine.id, "name": mine.name, "permissions": ["bookings:view"]})
    assert ("team", "manage") in {(p.capability, p.action) for p in mine.permissions.all()}


def test_old_role_page_opens_the_pop_up_instead(client_a, agency_a):
    client_a.get("/member/roles/")
    role = _role(agency_a, "Agent")
    r = client_a.get(f"/member/roles/{role.id}/")
    assert r.status_code == 302 and r["Location"].endswith(f"/member/roles/?edit={role.id}")
