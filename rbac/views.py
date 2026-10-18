from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import dateformat, timezone
from django.utils.translation import gettext
from django.views.decorators.http import require_POST

from member.models import Booking

from .catalog import CAPABILITIES, LEGACY_ROLE_TEMPLATE
from .decorators import permission_required
from .models import Permission, Role

User = get_user_model()


def _seed_agency_roles(agency):
    """Give the agency its own editable copy of every standard role (once) and move its teammates onto them."""
    templates = list(Role.all_tenants.filter(agency__isnull=True, is_template=True))
    with transaction.atomic():
        for template in templates:
            if Role.all_tenants.filter(agency=agency, name=template.name).exists():
                continue
            copy = Role.all_tenants.create(agency=agency, name=template.name, is_template=False, level=template.level, cloned_from=template)
            copy.permissions.set(template.permissions.all())
            legacy = [k for k, v in LEGACY_ROLE_TEMPLATE.items() if v == template.name]
            User.objects.filter(agency=agency).filter(Q(custom_role=template) | Q(custom_role__isnull=True, role__in=legacy)).update(custom_role=copy)
        type(agency).objects.filter(pk=agency.pk).update(roles_seeded=True)
        agency.roles_seeded = True


def _tenant_roles(agency):
    """This agency's own roles (the standard ones are copied in on first use, then they are just roles)."""
    if not agency.roles_seeded:
        _seed_agency_roles(agency)
    return Role.objects.filter(agency=agency)


def _level_for(perm_pairs, current=None):
    """Coarse seniority bridge for legacy pages: 75 when the role can manage the team, 25 with any manage right, else 10."""
    tier = 75 if ('team', 'manage') in perm_pairs else 25 if any(a == 'manage' for _c, a in perm_pairs) else 10
    if current is not None and (current >= 75) == (tier >= 75) and (current >= 25) == (tier >= 25):
        return current
    return tier


def _require_agency(request):
    """
    These screens are tenant self-service (Team & Roles), not platform
    administration — a Super Admin bypasses has_capability() but has no
    agency of their own, so guard against that landing here with
    agency=None and silently querying platform-wide.
    """
    if request.user.agency_id:
        return None
    messages.error(request, gettext("This is a tenant screen — use Platform Admin to manage agencies."))
    return redirect('platform_admin:dashboard' if request.user.is_superuser else 'root')


@permission_required('team', 'view')
def team_list(request):
    if (guard := _require_agency(request)) is not None:
        return guard
    agency = request.user.agency
    staff = list(User.objects.filter(agency=agency, deleted_at__isnull=True).select_related('custom_role').order_by('-is_active', '-created_at'))
    booking_counts = dict(
        Booking._base_manager.filter(agent__in=staff).values_list('agent').annotate(n=Count('id')).values_list('agent', 'n')
    )
    for u in staff:
        u.booking_count = booking_counts.get(u.pk, 0)
    return render(request, 'rbac/team_list.html', {
        'staff': staff,
        'active_count': sum(1 for u in staff if u.is_active),
        'roles': _tenant_roles(agency).order_by('-level', 'name'),
        'can_manage': request.user.is_superuser or _can_manage(request.user),
    })


def _can_manage(user):
    from .engine import has_capability
    return has_capability(user, 'team', 'manage')


def _role_summary(roles):
    """{role_id: {name, caps: [{label, level}]}} so the invite form can preview a role."""
    summary = {}
    for role in roles.prefetch_related('permissions'):
        granted = {(p.capability, p.action) for p in role.permissions.all()}
        caps = []
        for cap, label in CAPABILITIES:
            level = 'manage' if (cap, 'manage') in granted else 'view' if (cap, 'view') in granted else 'none'
            caps.append({'label': str(label), 'level': level})
        summary[str(role.id)] = {'name': gettext(role.name), 'caps': caps}
    return summary


@permission_required('team', 'manage')
def staff_invite(request):
    if (guard := _require_agency(request)) is not None:
        return guard
    agency = request.user.agency
    roles = _tenant_roles(agency).order_by('-level', 'name')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        role_id = request.POST.get('role_id')

        from billing.usage import check_seat_limit
        seat_ok, seat_message = check_seat_limit(agency)

        errors = []
        if not seat_ok:
            errors.append(seat_message)
        if not username:
            errors.append(gettext("Username is required."))
        elif (existing := User.objects.filter(username=username).first()) is not None:
            if existing.deleted_at:
                errors.append(gettext("The username '%(username)s' belonged to a teammate who was removed. Choose a different one.") % {'username': username})
            else:
                errors.append(gettext("Username '%(username)s' is already taken.") % {'username': username})
        if not password or len(password) < 8:
            errors.append(gettext("Password must be at least 8 characters."))
        role = roles.filter(pk=role_id).first()
        if not role:
            errors.append(gettext("Choose a valid role."))

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'rbac/staff_invite.html', {'roles': roles, 'form_data': request.POST, 'role_summary': _role_summary(roles)})

        legacy_role = 'member' if role.level >= 75 else 'agent'
        User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            agency=agency,
            role=legacy_role,
            custom_role=role,
        )
        messages.success(request, gettext("'%(username)s' added to your team as %(role)s.") % {'username': username, 'role': role.name})
        return redirect('member-team')

    return render(request, 'rbac/staff_invite.html', {'roles': roles, 'form_data': {}, 'role_summary': _role_summary(roles)})


@permission_required('team', 'manage')
@require_POST
def staff_update_role(request, user_id):
    if (guard := _require_agency(request)) is not None:
        return guard
    agency = request.user.agency
    staff_user = get_object_or_404(User, pk=user_id, agency=agency)
    role = _tenant_roles(agency).filter(pk=request.POST.get('role_id')).first()
    if not role:
        messages.error(request, gettext("Choose a valid role."))
        return redirect('member-team')
    staff_user.custom_role = role
    staff_user.role = 'member' if role.level >= 75 else 'agent'
    staff_user.save(update_fields=['custom_role', 'role'])
    messages.success(request, gettext("%(username)s is now %(role)s.") % {'username': staff_user.username, 'role': role.name})
    return redirect('member-team')


@permission_required('team', 'manage')
@require_POST
def staff_deactivate(request, user_id):
    if (guard := _require_agency(request)) is not None:
        return guard
    agency = request.user.agency
    staff_user = get_object_or_404(User, pk=user_id, agency=agency)
    if staff_user.pk == request.user.pk:
        messages.error(request, gettext("You can't deactivate your own account."))
        return redirect('member-team')
    staff_user.is_active = False
    staff_user.save(update_fields=['is_active'])
    messages.success(request, gettext("%(username)s has been deactivated.") % {'username': staff_user.username})
    return redirect('member-team')


@permission_required('team', 'manage')
@require_POST
def staff_reactivate(request, user_id):
    if (guard := _require_agency(request)) is not None:
        return guard
    staff_user = get_object_or_404(User, pk=user_id, agency=request.user.agency)
    staff_user.is_active = True
    staff_user.save(update_fields=['is_active'])
    messages.success(request, gettext("%(username)s is active again.") % {'username': staff_user.username})
    return redirect('member-team')


@permission_required('team', 'manage')
@require_POST
def staff_delete(request, user_id):
    """Remove a teammate. Nothing they created is deleted: the account is switched off and hidden, so their
    bookings, payments and vouchers stay in the database (and visible on the admin side)."""
    if (guard := _require_agency(request)) is not None:
        return guard
    staff_user = get_object_or_404(User, pk=user_id, agency=request.user.agency, deleted_at__isnull=True)
    if staff_user.pk == request.user.pk:
        messages.error(request, gettext("You can't delete your own account."))
        return redirect('member-team')
    staff_user.is_active = False
    staff_user.deleted_at = timezone.now()
    staff_user.save(update_fields=['is_active', 'deleted_at', 'updated_at'])
    messages.success(request, gettext("%(username)s has been removed from the team. Their bookings, payments and vouchers are kept.") % {'username': staff_user.username})
    return redirect('member-team')


@permission_required('team', 'view')
def roles_list(request):
    if (guard := _require_agency(request)) is not None:
        return guard
    agency = request.user.agency
    roles = list(_tenant_roles(agency).prefetch_related('permissions').order_by('-level', 'name'))
    holders = dict(User.objects.filter(agency=agency).exclude(custom_role__isnull=True).values_list('custom_role').annotate(n=Count('id')).values_list('custom_role', 'n'))
    rows, role_data = [], {}
    for r in roles:
        granted = {(p.capability, p.action) for p in r.permissions.all()}
        counts = {'manage': 0, 'view': 0, 'none': 0}
        for cap, _label in CAPABILITIES:
            counts['manage' if (cap, 'manage') in granted else 'view' if (cap, 'view') in granted else 'none'] += 1
        parts = []
        if counts['manage']:
            parts.append(f"{gettext('Manage')} {counts['manage']}")
        if counts['view']:
            parts.append(f"{gettext('View only')} {counts['view']}")
        if counts['none']:
            parts.append(f"{gettext('No access')} {counts['none']}")
        rows.append({'role': r, 'summary': ' · '.join(parts), 'members': holders.get(r.pk, 0)})
        role_data[str(r.pk)] = {'name': r.name, 'perms': sorted(f"{c}:{a}" for c, a in granted)}
    return render(request, 'rbac/roles_list.html', {
        'rows': rows,
        'role_data': role_data,
        'capabilities': CAPABILITIES,
        'can_manage': request.user.is_superuser or _can_manage(request.user),
    })


@permission_required('team', 'manage')
@require_POST
def role_save(request):
    """Create a role, or update an existing one (name and permissions), from the pop-up on the Roles page."""
    if (guard := _require_agency(request)) is not None:
        return guard
    agency = request.user.agency
    role_id = request.POST.get('role_id')
    role = get_object_or_404(_tenant_roles(agency), pk=role_id) if role_id else None
    name = ' '.join((request.POST.get('name') or '').split())
    if not name:
        messages.error(request, gettext("Give the role a name."))
        return redirect('member-roles')
    name = name[:100]
    if Role.all_tenants.filter(agency=agency, name__iexact=name).exclude(pk=role.pk if role else None).exists():
        messages.error(request, gettext("You already have a role called “%(role)s”.") % {'role': name})
        return redirect('member-roles')
    selected = set()
    for raw in request.POST.getlist('permissions'):
        capability, _, action = raw.partition(':')
        if capability and action:
            selected.add((capability, action))
    selected |= {(c, 'view') for c, a in selected if a == 'manage'}  # managing something implies seeing it
    if role and request.user.custom_role_id == role.id and ('team', 'manage') not in selected:
        messages.error(request, gettext("You can't remove your own access to Team & roles."))
        return redirect('member-roles')
    perm_ids = [pk for pk, c, a in Permission.objects.values_list('pk', 'capability', 'action') if (c, a) in selected]
    with transaction.atomic():
        if role is None:
            role = Role.all_tenants.create(agency=agency, name=name, is_template=False, level=_level_for(selected))
        else:
            role.name = name
            role.level = _level_for(selected, role.level)
            role.save(update_fields=['name', 'level', 'updated_at'])
        role.permissions.set(perm_ids)
        User.objects.filter(agency=agency, custom_role=role).update(role='member' if role.level >= 75 else 'agent')
    messages.success(request, gettext("Saved the role “%(role)s”.") % {'role': role.name})
    return redirect('member-roles')


@permission_required('team', 'manage')
@require_POST
def role_delete(request, role_id):
    """Delete one of the agency's roles. Teammates holding it keep working on the standard access for their
    account type; no bookings, payments or vouchers are touched."""
    if (guard := _require_agency(request)) is not None:
        return guard
    agency = request.user.agency
    role = get_object_or_404(_tenant_roles(agency), pk=role_id)
    if request.user.custom_role_id == role.id:
        messages.error(request, gettext("You can't delete the role you are using yourself."))
        return redirect('member-roles')
    if _tenant_roles(agency).count() <= 1:
        messages.error(request, gettext("Keep at least one role."))
        return redirect('member-roles')
    name = role.name
    role.delete()
    messages.success(request, gettext("Role “%(role)s” has been deleted.") % {'role': name})
    return redirect('member-roles')


@permission_required('team', 'view')
def role_detail(request, role_id):
    """Old per-role page: roles are edited in the pop-up on the Roles page now."""
    return redirect(f"{reverse('member-roles')}?edit={role_id}")


@permission_required('activity_log', 'view')
def activity_log(request):
    """Every create / edit / delete in the agency, recorded automatically by utils/audit.py."""
    if (guard := _require_agency(request)) is not None:
        return guard
    import csv

    from django.core.paginator import Paginator
    from django.http import HttpResponse

    from member import attendance as att

    from . import activity

    agency = request.user.agency
    tz = att.office_tz(att.get_settings(agency))
    f = activity.read_filters(request.GET)
    qs, counts = activity.filtered(agency, f, tz)

    def who(entry):
        return entry.user.full_name if entry.user_id else gettext("System")

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="activity-log.csv"'
        response.write("﻿")
        writer = csv.writer(response)
        writer.writerow(["When", "Who", "Action", "Type", "Record", "Changes", "IP address"])
        for e in qs[:5000]:
            changes = "; ".join(f"{c['label']}: {c['old']} -> {c['new']}" for c in activity.readable_changes(e, tz))
            writer.writerow([timezone.localtime(e.timestamp, tz).strftime("%Y-%m-%d %H:%M:%S"), who(e),
                             e.get_action_display(), activity.model_label(e.model_name), e.object_repr,
                             changes, e.ip_address or ""])
        return response

    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    rows = [{
        "e": e,
        # Pre-formatted: the |date filter would convert back to the server's UTC.
        "when_date": dateformat.format(timezone.localtime(e.timestamp, tz), "d M Y"),
        "when_time": dateformat.format(timezone.localtime(e.timestamp, tz), "g:i A"),
        "who": who(e),
        "type": activity.model_label(e.model_name),
        "changes": activity.readable_changes(e, tz),
    } for e in page.object_list]
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, 'rbac/activity_log.html', {
        'page_title': 'Activity Log',
        'rows': rows,
        'page': page,
        'f': f,
        'filtered': any(f.values()),
        'counts': {k: counts.get(k, 0) for k in ("create", "update", "delete")},
        'total': sum(counts.values()),
        'options': activity.options(agency),
        'presets': activity.PRESETS,
        'actions': [("create", gettext("Created")), ("update", gettext("Edited")), ("delete", gettext("Deleted"))],
        'query': query.urlencode(),
    })
