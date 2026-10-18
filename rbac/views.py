from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext
from django.views.decorators.http import require_POST

from .catalog import CAPABILITIES, MAX_CUSTOM_ROLES_PER_AGENCY
from .decorators import permission_required
from .models import Permission, Role

User = get_user_model()


def _tenant_roles(agency):
    """Templates (usable as-is) + this agency's own custom roles."""
    return Role.objects.filter(agency__isnull=True, is_template=True) | Role.objects.filter(agency=agency)


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
    staff = User.objects.filter(agency=agency).select_related('custom_role').order_by('-created_at')
    return render(request, 'rbac/team_list.html', {
        'staff': staff,
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
        summary[str(role.id)] = {'name': role.name, 'caps': caps}
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
        elif User.objects.filter(username=username).exists():
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


@permission_required('team', 'view')
def roles_list(request):
    if (guard := _require_agency(request)) is not None:
        return guard
    agency = request.user.agency
    templates = Role.objects.filter(agency__isnull=True, is_template=True).order_by('-level')
    custom_roles = Role.objects.filter(agency=agency).order_by('name')
    return render(request, 'rbac/roles_list.html', {
        'templates': templates,
        'custom_roles': custom_roles,
        'at_cap': custom_roles.count() >= MAX_CUSTOM_ROLES_PER_AGENCY,
        'max_custom_roles': MAX_CUSTOM_ROLES_PER_AGENCY,
    })


@permission_required('team', 'manage')
def role_clone(request, role_id):
    if (guard := _require_agency(request)) is not None:
        return guard
    agency = request.user.agency
    if Role.objects.filter(agency=agency).count() >= MAX_CUSTOM_ROLES_PER_AGENCY:
        messages.error(request, gettext("You've reached the limit of %(max)s custom roles.") % {'max': MAX_CUSTOM_ROLES_PER_AGENCY})
        return redirect('member-roles')

    source = get_object_or_404(_tenant_roles(agency), pk=role_id)
    base_name = f"{source.name} (custom)"
    name = base_name
    suffix = 2
    while Role.objects.filter(agency=agency, name=name).exists():
        name = f"{base_name} {suffix}"
        suffix += 1

    with transaction.atomic():
        clone = Role.objects.create(agency=agency, name=name, is_template=False, level=source.level, cloned_from=source)
        clone.permissions.set(source.permissions.all())

    messages.success(request, gettext("Cloned '%(source)s' as '%(clone)s'. Adjust its permissions below.") % {'source': source.name, 'clone': clone.name})
    return redirect('member-role-detail', role_id=clone.id)


@permission_required('team', 'view')
def role_detail(request, role_id):
    if (guard := _require_agency(request)) is not None:
        return guard
    agency = request.user.agency
    role = get_object_or_404(_tenant_roles(agency), pk=role_id)
    is_editable = role.agency_id == agency.id

    if request.method == 'POST':
        if not is_editable:
            messages.error(request, gettext("Templates can't be edited directly — clone it first."))
            return redirect('member-role-detail', role_id=role.id)
        if not _can_manage(request.user):
            messages.error(request, gettext("You don't have permission to edit roles."))
            return redirect('member-role-detail', role_id=role.id)
        selected_pairs = set()
        for raw in request.POST.getlist('permissions'):
            capability, _, action = raw.partition(':')
            if capability and action:
                selected_pairs.add((capability, action))
        matching_ids = [
            pk for pk, capability, action in Permission.objects.values_list('pk', 'capability', 'action')
            if (capability, action) in selected_pairs
        ]
        role.permissions.set(matching_ids)
        messages.success(request, gettext("Updated permissions for '%(role)s'.") % {'role': role.name})
        return redirect('member-role-detail', role_id=role.id)

    granted = set(role.permissions.values_list('capability', 'action'))
    matrix = [
        {
            'capability': cap,
            'label': label,
            'view': (cap, 'view') in granted,
            'manage': (cap, 'manage') in granted,
        }
        for cap, label in CAPABILITIES
    ]
    return render(request, 'rbac/role_detail.html', {
        'role': role,
        'is_editable': is_editable,
        'matrix': matrix,
    })


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
        "when_date": timezone.localtime(e.timestamp, tz).strftime("%d %b %Y"),
        "when_time": timezone.localtime(e.timestamp, tz).strftime("%I:%M %p").lstrip("0"),
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
