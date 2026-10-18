import json

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext
from django.views.decorators.http import require_POST

from agencies.models import Agency
from billing.models import PaymentRecord, Plan, Subscription
from billing.usage import get_booking_usage_this_month, get_seat_usage
from rbac.models import Role
from system_config.models import (
    AgencyBranding,
    APIKey,
    AuditLog,
    EmailTemplate,
    NotificationSettings,
    SystemConfiguration,
)
from travelcrm.health import check_database, check_redis

from . import analytics
from .catalog import CAPABILITIES
from .decorators import has_platform_capability, platform_staff_required, superadmin_required
from .management.commands.verify_backup import BACKUP_STATUS_KEY
from .models import Announcement, ImpersonationSession, StaffAccess

User = get_user_model()


def _log(request, action, obj):
    """
    For models NOT covered by the generic signal-based audit trail
    (utils/audit.py) — currently just ImpersonationSession and StaffAccess.
    """
    AuditLog.all_tenants.create(
        user=request.user,
        action=action,
        model_name=obj.__class__.__name__,
        object_id=str(obj.pk),
        object_repr=str(obj)[:200],
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )


@platform_staff_required('tenants.view')
def dashboard(request):
    agencies = (
        Agency.objects.all()
        .order_by('-created_at')
    )
    active_subs = Subscription.all_tenants.filter(status='active').select_related('plan')
    # Simple MRR: monthly plans counted at face value, yearly plans divided
    # by 12 — a proxy from locally-tracked subscriptions, not a live
    # payment ledger (there's no processor generating one).
    mrr = sum(
        (s.plan.price_amount / 12 if s.plan.billing_interval == 'yearly' else s.plan.price_amount)
        for s in active_subs
    )
    stats = {
        'total_agencies': agencies.count(),
        'active_agencies': agencies.filter(is_active=True).count(),
        'suspended_agencies': agencies.filter(is_active=False).count(),
        'total_users': User.objects.count(),
        'trialing': Subscription.all_tenants.filter(status='trialing').count(),
        'paying': active_subs.count(),
        'mrr': mrr,
        'pending_payments': PaymentRecord.all_tenants.filter(status='pending').count(),
        'past_due': Subscription.all_tenants.filter(status='past_due').count(),
    }
    return render(request, 'platform_admin/dashboard.html', {
        'agencies': agencies,
        'stats': stats,
    })


@platform_staff_required('analytics.view')
def analytics_view(request):
    labels, values = analytics.agency_growth(months=6)
    return render(request, 'platform_admin/analytics.html', {
        'growth_labels_json': json.dumps(labels),
        'growth_values_json': json.dumps(values),
        'plan_mix': analytics.plan_mix(),
        'mrr_by_plan': analytics.mrr_by_plan(),
    })


@platform_staff_required('tenants.view')
def tenant_detail(request, agency_id):
    agency = get_object_or_404(Agency, pk=agency_id)
    users = agency.users.all().order_by('-created_at')
    recent_activity = AuditLog.objects.filter(
        model_name='Agency', object_id=str(agency.pk)
    )[:20]
    subscription = Subscription.all_tenants.filter(agency=agency).select_related('plan').first()
    plans = Plan.objects.filter(is_active=True).order_by('sort_order')
    branding = AgencyBranding.all_tenants.filter(agency=agency).first()

    usage = None
    if subscription:
        seats_used = get_seat_usage(agency)
        bookings_used = get_booking_usage_this_month(agency)
        usage = {
            'seats_used': seats_used,
            'seats_max': subscription.plan.max_seats,
            'bookings_used': bookings_used,
            'bookings_max': subscription.plan.max_bookings_per_month,
        }

    return render(request, 'platform_admin/tenant_detail.html', {
        'agency': agency,
        'users': users,
        'recent_activity': recent_activity,
        'subscription': subscription,
        'plans': plans,
        'branding': branding,
        'usage': usage,
        'can_manage': has_platform_capability(request.user, 'tenants.manage'),
    })


@platform_staff_required('tenants.manage')
@require_POST
def tenant_branding_update(request, agency_id):
    agency = get_object_or_404(Agency, pk=agency_id)
    branding, _created = AgencyBranding.all_tenants.get_or_create(agency=agency)
    branding.company_name = request.POST.get('company_name', '').strip()
    branding.tagline = request.POST.get('tagline', '').strip()
    branding.primary_color = request.POST.get('primary_color', branding.primary_color).strip()
    branding.secondary_color = request.POST.get('secondary_color', branding.secondary_color).strip()
    branding.phone = request.POST.get('phone', '').strip()
    branding.email = request.POST.get('email', '').strip()
    branding.website = request.POST.get('website', '').strip()
    branding.is_active = request.POST.get('is_active') == 'on'
    if request.FILES.get('logo'):
        branding.logo = request.FILES['logo']
    branding.save()
    messages.success(request, gettext("Branding updated for '%(agency)s'.") % {'agency': agency.name})
    return redirect('platform_admin:tenant-detail', agency_id=agency.pk)


@platform_staff_required('billing.manage')
@require_POST
def tenant_assign_plan(request, agency_id):
    """Manual override — grandfather an agency in, comp a plan, or fix a
    stuck subscription without routing through the payment-claim flow."""
    agency = get_object_or_404(Agency, pk=agency_id)
    plan = get_object_or_404(Plan, pk=request.POST.get('plan_id'))
    status = request.POST.get('status', 'active')
    if status not in dict(Subscription.STATUS_CHOICES):
        status = 'active'

    period_days = 365 if plan.billing_interval == 'yearly' else 30
    sub, _ = Subscription.all_tenants.update_or_create(
        agency=agency,
        defaults={
            'plan': plan,
            'status': status,
            'current_period_end': timezone.now() + timezone.timedelta(days=period_days) if status == 'active' else None,
            'trial_ends_at': timezone.now() + timezone.timedelta(days=plan.trial_days) if status == 'trialing' else None,
        },
    )
    messages.success(request, gettext("'%(agency)s' is now on the %(plan)s plan (%(status)s).") % {'agency': agency.name, 'plan': plan.name, 'status': status})
    return redirect('platform_admin:tenant-detail', agency_id=agency.pk)


@platform_staff_required('tenants.manage')
def tenant_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        owner_username = request.POST.get('owner_username', '').strip()
        owner_email = request.POST.get('owner_email', '').strip()
        owner_password = request.POST.get('owner_password', '').strip()

        errors = []
        if not name:
            errors.append("Agency name is required.")
        if not code:
            errors.append("Agency code is required.")
        elif Agency.objects.filter(code=code).exists():
            errors.append(f"Agency code '{code}' is already in use.")
        if not owner_username:
            errors.append("Owner username is required.")
        elif User.objects.filter(username=owner_username).exists():
            errors.append(f"Username '{owner_username}' is already taken.")
        if not owner_password or len(owner_password) < 8:
            errors.append("Owner password must be at least 8 characters.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'platform_admin/tenant_create.html', {'form_data': request.POST})

        with transaction.atomic():
            agency = Agency.objects.create(
                name=name,
                code=code,
                email=email,
                phone=phone,
                address=request.POST.get('address', ''),
                city=request.POST.get('city', ''),
                state=request.POST.get('state', ''),
                country=request.POST.get('country', ''),
                postal_code=request.POST.get('postal_code', ''),
                is_active=True,
            )
            owner_role = Role.all_tenants.filter(agency__isnull=True, is_template=True, name='Owner').first()
            owner = User.objects.create(
                username=owner_username,
                email=owner_email,
                password=make_password(owner_password),
                role='member',
                agency=agency,
                custom_role=owner_role,
            )
            trial_plan = Plan.objects.filter(is_default_trial=True, is_active=True).first()
            if trial_plan:
                Subscription.all_tenants.create(
                    agency=agency, plan=trial_plan, status='trialing',
                    trial_ends_at=timezone.now() + timezone.timedelta(days=trial_plan.trial_days),
                )

        messages.success(request, gettext("Agency '%(agency)s' created with owner account '%(owner)s'.") % {'agency': agency.name, 'owner': owner.username})
        return redirect('platform_admin:tenant-detail', agency_id=agency.pk)

    return render(request, 'platform_admin/tenant_create.html', {'form_data': {}})


@platform_staff_required('tenants.manage')
@require_POST
def tenant_suspend(request, agency_id):
    agency = get_object_or_404(Agency, pk=agency_id)
    agency.is_active = False
    agency.suspended_at = timezone.now()
    agency.suspended_by = request.user
    agency.suspended_reason = request.POST.get('reason', '').strip()
    agency.save(update_fields=['is_active', 'suspended_at', 'suspended_by', 'suspended_reason'])
    messages.success(request, gettext("'%(agency)s' has been suspended.") % {'agency': agency.name})
    return redirect('platform_admin:tenant-detail', agency_id=agency.pk)


@platform_staff_required('tenants.manage')
@require_POST
def tenant_activate(request, agency_id):
    agency = get_object_or_404(Agency, pk=agency_id)
    agency.is_active = True
    agency.suspended_at = None
    agency.suspended_by = None
    agency.suspended_reason = ''
    agency.save(update_fields=['is_active', 'suspended_at', 'suspended_by', 'suspended_reason'])
    messages.success(request, gettext("'%(agency)s' has been reactivated.") % {'agency': agency.name})
    return redirect('platform_admin:tenant-detail', agency_id=agency.pk)


@platform_staff_required('tenants.manage')
@require_POST
def impersonate_start(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target.is_superuser:
        messages.error(request, gettext("Cannot impersonate another Super Admin."))
        return redirect('platform_admin:dashboard')
    if not target.agency_id:
        messages.error(request, gettext("This user has no agency to impersonate into."))
        return redirect('platform_admin:dashboard')

    session = ImpersonationSession.objects.create(
        super_admin=request.user,
        target_user=target,
        target_agency=target.agency,
        reason=request.POST.get('reason', ''),
    )
    real_admin_id = request.user.pk
    login(request, target, backend='django.contrib.auth.backends.ModelBackend')
    request.session['impersonator_id'] = real_admin_id
    request.session['impersonation_session_id'] = session.pk
    _log(request, 'update', session)
    return redirect('root')


@require_POST
def impersonate_stop(request):
    admin_id = request.session.get('impersonator_id')
    if not admin_id:
        return redirect('root')

    admin_user = get_object_or_404(User, pk=admin_id, is_superuser=True)
    session_id = request.session.get('impersonation_session_id')
    if session_id:
        ImpersonationSession.objects.filter(pk=session_id, ended_at__isnull=True).update(ended_at=timezone.now())

    login(request, admin_user, backend='django.contrib.auth.backends.ModelBackend')
    request.session.pop('impersonator_id', None)
    request.session.pop('impersonation_session_id', None)
    messages.success(request, gettext("Returned to Super Admin."))
    return redirect('platform_admin:dashboard')


@platform_staff_required('tenants.manage')
def impersonation_sessions(request):
    sessions = ImpersonationSession.objects.select_related('super_admin', 'target_user', 'target_agency')[:200]
    return render(request, 'platform_admin/impersonation_sessions.html', {'sessions': sessions})


@platform_staff_required('audit.view')
def audit_log(request):
    entries = AuditLog.objects.select_related('user', 'agency').order_by('-timestamp')

    model_name = request.GET.get('model_name', '').strip()
    action = request.GET.get('action', '').strip()
    agency_id = request.GET.get('agency_id', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if model_name:
        entries = entries.filter(model_name=model_name)
    if action:
        entries = entries.filter(action=action)
    if agency_id:
        entries = entries.filter(agency_id=agency_id)
    if date_from:
        entries = entries.filter(timestamp__date__gte=date_from)
    if date_to:
        entries = entries.filter(timestamp__date__lte=date_to)

    paginator = Paginator(entries, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    model_names = AuditLog.objects.order_by('model_name').values_list('model_name', flat=True).distinct()
    agencies = Agency.objects.order_by('name').only('id', 'name')

    querystring = request.GET.copy()
    querystring.pop('page', None)

    return render(request, 'platform_admin/audit_log.html', {
        'page_obj': page_obj,
        'model_names': model_names,
        'agencies': agencies,
        'action_choices': AuditLog.ACTION_TYPES,
        'filters': {
            'model_name': model_name, 'action': action, 'agency_id': agency_id,
            'date_from': date_from, 'date_to': date_to,
        },
        'querystring': querystring.urlencode(),
    })


@platform_staff_required('billing.view')
def plans_list(request):
    plans = Plan.objects.all().order_by('sort_order')
    return render(request, 'platform_admin/plans_list.html', {'plans': plans})


@platform_staff_required('billing.manage')
def plan_form(request, plan_id=None):
    plan = get_object_or_404(Plan, pk=plan_id) if plan_id else None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip().lower().replace(' ', '-')
        errors = []
        if not name:
            errors.append("Name is required.")
        if not slug:
            errors.append("Slug is required.")
        elif Plan.objects.filter(slug=slug).exclude(pk=plan.pk if plan else None).exists():
            errors.append(f"Slug '{slug}' is already in use.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'platform_admin/plan_form.html', {'plan': plan, 'form_data': request.POST})

        def _int_or_none(val):
            val = (val or '').strip()
            return int(val) if val else None

        is_default_trial = request.POST.get('is_default_trial') == 'on'

        with transaction.atomic():
            if is_default_trial:
                Plan.objects.exclude(pk=plan.pk if plan else None).update(is_default_trial=False)
            fields = dict(
                name=name, slug=slug,
                description=request.POST.get('description', '').strip(),
                price_amount=request.POST.get('price_amount') or 0,
                currency=request.POST.get('currency', 'PKR').strip() or 'PKR',
                billing_interval=request.POST.get('billing_interval', 'monthly'),
                max_seats=_int_or_none(request.POST.get('max_seats')),
                max_bookings_per_month=_int_or_none(request.POST.get('max_bookings_per_month')),
                is_active=request.POST.get('is_active') == 'on',
                is_default_trial=is_default_trial,
                trial_days=int(request.POST.get('trial_days') or 14),
                sort_order=int(request.POST.get('sort_order') or 0),
                features="\n".join(line.strip() for line in request.POST.get('features', '').splitlines() if line.strip()),
                badge=request.POST.get('badge', '').strip()[:40],
                is_featured=request.POST.get('is_featured') == 'on',
            )
            if plan:
                for k, v in fields.items():
                    setattr(plan, k, v)
                plan.save()
            else:
                plan = Plan.objects.create(**fields)

        messages.success(request, gettext("Plan '%(plan)s' saved.") % {'plan': plan.name})
        return redirect('platform_admin:plans')

    return render(request, 'platform_admin/plan_form.html', {'plan': plan, 'form_data': {}})


@platform_staff_required('billing.view')
def pending_payments(request):
    payments = PaymentRecord.all_tenants.filter(status='pending').select_related('agency', 'plan').order_by('submitted_at')
    return render(request, 'platform_admin/pending_payments.html', {'payments': payments})


@platform_staff_required('billing.manage')
@require_POST
def confirm_payment(request, payment_id):
    payment = get_object_or_404(PaymentRecord.all_tenants, pk=payment_id, status='pending')
    period_days = 365 if payment.plan.billing_interval == 'yearly' else 30

    with transaction.atomic():
        payment.status = 'confirmed'
        payment.confirmed_by = request.user
        payment.confirmed_at = timezone.now()
        payment.save()

        Subscription.all_tenants.update_or_create(
            agency=payment.agency,
            defaults={
                'plan': payment.plan,
                'status': 'active',
                'current_period_end': timezone.now() + timezone.timedelta(days=period_days),
            },
        )
    messages.success(request, gettext("Payment confirmed — '%(agency)s' is now active on %(plan)s.") % {'agency': payment.agency.name, 'plan': payment.plan.name})
    return redirect('platform_admin:pending-payments')


@platform_staff_required('billing.manage')
@require_POST
def reject_payment(request, payment_id):
    payment = get_object_or_404(PaymentRecord.all_tenants, pk=payment_id, status='pending')
    payment.status = 'rejected'
    payment.confirmed_by = request.user
    payment.confirmed_at = timezone.now()
    payment.rejection_reason = request.POST.get('reason', '').strip()
    payment.save()
    messages.success(request, gettext("Payment claim rejected."))
    return redirect('platform_admin:pending-payments')


# ── Platform staff RBAC ──────────────────────────────────────────────

@superadmin_required
def staff_list(request):
    staff = StaffAccess.objects.select_related('user', 'granted_by').order_by('user__username')
    return render(request, 'platform_admin/staff_list.html', {'staff': staff})


@superadmin_required
def staff_form(request, staff_id=None):
    access = get_object_or_404(StaffAccess, pk=staff_id) if staff_id else None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        role_label = request.POST.get('role_label', '').strip()
        selected_caps = [c for c in request.POST.getlist('capabilities') if c in dict(CAPABILITIES)]

        errors = []
        target_user = None
        if access:
            target_user = access.user
        else:
            target_user = User.objects.filter(username=username).first()
            if not username:
                errors.append("Username is required.")
            elif not target_user:
                errors.append(f"No user found with username '{username}'.")
            elif target_user.is_superuser:
                errors.append("This user is already a full Super Admin — no need for scoped access.")
            elif StaffAccess.objects.filter(user=target_user).exists():
                errors.append("This user already has staff access — edit their existing entry instead.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'platform_admin/staff_form.html', {
                'access': access, 'capabilities': CAPABILITIES, 'form_data': request.POST,
            })

        if not access:
            access = StaffAccess(user=target_user, granted_by=request.user)
            target_user.is_staff = True
            target_user.save(update_fields=['is_staff'])
        access.role_label = role_label
        access.capabilities = selected_caps
        access.save()
        _log(request, 'update', access)

        messages.success(request, gettext("Staff access saved for '%(user)s'.") % {'user': access.user.username})
        return redirect('platform_admin:staff')

    return render(request, 'platform_admin/staff_form.html', {
        'access': access, 'capabilities': CAPABILITIES, 'form_data': {},
    })


@superadmin_required
@require_POST
def staff_revoke(request, staff_id):
    access = get_object_or_404(StaffAccess, pk=staff_id)
    user = access.user
    _log(request, 'delete', access)
    access.delete()
    user.is_staff = False
    user.save(update_fields=['is_staff'])
    messages.success(request, gettext("Staff access revoked for '%(user)s'.") % {'user': user.username})
    return redirect('platform_admin:staff')


# ── Tenant broadcast messaging ───────────────────────────────────────

@platform_staff_required('tenants.manage')
def announcements_list(request):
    items = Announcement.objects.prefetch_related('target_agencies').all()
    return render(request, 'platform_admin/announcements_list.html', {'announcements': items})


@platform_staff_required('tenants.manage')
def announcement_form(request, announcement_id=None):
    announcement = get_object_or_404(Announcement, pk=announcement_id) if announcement_id else None
    agencies = Agency.objects.order_by('name').only('id', 'name')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        errors = []
        if not title:
            errors.append("Title is required.")
        if not body:
            errors.append("Body is required.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'platform_admin/announcement_form.html', {
                'announcement': announcement, 'agencies': agencies, 'form_data': request.POST,
            })

        ends_at = request.POST.get('ends_at') or None
        target_ids = request.POST.getlist('target_agencies')

        if announcement:
            announcement.title = title
            announcement.body = body
            announcement.severity = request.POST.get('severity', 'info')
            announcement.ends_at = ends_at
            announcement.is_active = request.POST.get('is_active') == 'on'
            announcement.save()
        else:
            announcement = Announcement.objects.create(
                title=title, body=body,
                severity=request.POST.get('severity', 'info'),
                ends_at=ends_at,
                is_active=request.POST.get('is_active', 'on') == 'on',
                created_by=request.user,
            )
        announcement.target_agencies.set(target_ids)

        messages.success(request, gettext("Announcement '%(title)s' saved.") % {'title': announcement.title})
        return redirect('platform_admin:announcements')

    return render(request, 'platform_admin/announcement_form.html', {
        'announcement': announcement, 'agencies': agencies, 'form_data': {},
    })


@platform_staff_required('tenants.manage')
@require_POST
def announcement_deactivate(request, announcement_id):
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    announcement.is_active = False
    announcement.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, gettext("Announcement deactivated."))
    return redirect('platform_admin:announcements')


# ── System configuration ─────────────────────────────────────────────

@platform_staff_required('system_config.manage')
def system_config_list(request):
    # BACKUP_STATUS_KEY is written by `manage.py verify_backup`, not meant
    # for hand-editing — it has its own display on the System Health page.
    configs = SystemConfiguration.objects.exclude(key=BACKUP_STATUS_KEY).order_by('key')
    return render(request, 'platform_admin/system_config_list.html', {'configs': configs})


@platform_staff_required('system_config.manage')
def system_config_form(request, config_id=None):
    config = get_object_or_404(SystemConfiguration, pk=config_id) if config_id else None

    if request.method == 'POST':
        key = request.POST.get('key', '').strip()
        errors = []
        if not key:
            errors.append("Key is required.")
        elif SystemConfiguration.objects.filter(key=key).exclude(pk=config.pk if config else None).exists():
            errors.append(f"Key '{key}' is already in use.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'platform_admin/system_config_form.html', {'config': config, 'form_data': request.POST})

        fields = dict(
            key=key,
            value=request.POST.get('value', ''),
            description=request.POST.get('description', '').strip(),
            is_active=request.POST.get('is_active') == 'on',
        )
        if config:
            for k, v in fields.items():
                setattr(config, k, v)
            config.save()
        else:
            config = SystemConfiguration.objects.create(**fields)

        messages.success(request, gettext("Setting '%(key)s' saved.") % {'key': config.key})
        return redirect('platform_admin:system-config')

    return render(request, 'platform_admin/system_config_form.html', {'config': config, 'form_data': {}})


@platform_staff_required('system_config.manage')
@require_POST
def system_config_delete(request, config_id):
    config = get_object_or_404(SystemConfiguration, pk=config_id)
    key = config.key
    config.delete()
    messages.success(request, gettext("Setting '%(key)s' deleted.") % {'key': key})
    return redirect('platform_admin:system-config')


# ── Email templates (global defaults only) ──────────────────────────

@platform_staff_required('system_config.manage')
def email_templates_list(request):
    templates = EmailTemplate.all_tenants.filter(agency__isnull=True).order_by('template_type', 'name')
    return render(request, 'platform_admin/email_templates_list.html', {'templates': templates})


@platform_staff_required('system_config.manage')
def email_template_form(request, template_id=None):
    template = get_object_or_404(EmailTemplate.all_tenants, pk=template_id, agency__isnull=True) if template_id else None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        template_type = request.POST.get('template_type', 'custom')
        subject = request.POST.get('subject', '').strip()
        errors = []
        if not name:
            errors.append("Name is required.")
        if not subject:
            errors.append("Subject is required.")
        if EmailTemplate.all_tenants.filter(agency__isnull=True, template_type=template_type).exclude(pk=template.pk if template else None).exists():
            errors.append(f"A global template for type '{template_type}' already exists.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'platform_admin/email_template_form.html', {
                'template': template, 'type_choices': EmailTemplate.TEMPLATE_TYPES, 'form_data': request.POST,
            })

        fields = dict(
            name=name, template_type=template_type, subject=subject,
            html_content=request.POST.get('html_content', ''),
            text_content=request.POST.get('text_content', ''),
            is_active=request.POST.get('is_active') == 'on',
            is_default=request.POST.get('is_default') == 'on',
            agency=None,
        )
        if template:
            for k, v in fields.items():
                setattr(template, k, v)
            template.save()
        else:
            template = EmailTemplate.all_tenants.create(**fields)

        messages.success(request, gettext("Template '%(name)s' saved.") % {'name': template.name})
        return redirect('platform_admin:email-templates')

    return render(request, 'platform_admin/email_template_form.html', {
        'template': template, 'type_choices': EmailTemplate.TEMPLATE_TYPES, 'form_data': {},
    })


# ── API keys ─────────────────────────────────────────────────────────

def _mask_secret(value):
    if not value:
        return ''
    return f"••••{value[-4:]}" if len(value) > 4 else "••••"


@platform_staff_required('system_config.manage')
def api_keys_list(request):
    keys = APIKey.all_tenants.select_related('agency').order_by('key_type', 'name')
    masked = [{'obj': k, 'masked_key': _mask_secret(k.api_key)} for k in keys]
    return render(request, 'platform_admin/api_keys_list.html', {'keys': masked})


@platform_staff_required('system_config.manage')
def api_key_form(request, key_id=None):
    key = get_object_or_404(APIKey.all_tenants, pk=key_id) if key_id else None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        api_key_value = request.POST.get('api_key', '').strip()
        errors = []
        if not name:
            errors.append("Name is required.")
        if not api_key_value and not key:
            errors.append("API key value is required.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'platform_admin/api_key_form.html', {
                'key': key, 'type_choices': APIKey.KEY_TYPES, 'agencies': Agency.objects.order_by('name'), 'form_data': request.POST,
            })

        agency_id = request.POST.get('agency_id') or None
        fields = dict(
            name=name,
            key_type=request.POST.get('key_type', 'other'),
            endpoint_url=request.POST.get('endpoint_url', '').strip(),
            description=request.POST.get('description', '').strip(),
            agency_id=agency_id,
            is_active=request.POST.get('is_active') == 'on',
        )
        if api_key_value:
            fields['api_key'] = api_key_value
        api_secret_value = request.POST.get('api_secret', '').strip()
        if api_secret_value:
            fields['api_secret'] = api_secret_value

        if key:
            for k, v in fields.items():
                setattr(key, k, v)
            key.save()
        else:
            key = APIKey.all_tenants.create(**fields)

        messages.success(request, gettext("API key '%(name)s' saved.") % {'name': key.name})
        return redirect('platform_admin:api-keys')

    return render(request, 'platform_admin/api_key_form.html', {
        'key': key, 'type_choices': APIKey.KEY_TYPES, 'agencies': Agency.objects.order_by('name'), 'form_data': {},
    })


# ── Notification settings (read-only support diagnostic) ────────────

@platform_staff_required('tenants.view')
def notification_settings_report(request):
    settings_rows = NotificationSettings.all_tenants.select_related('agency').order_by('agency__name')
    return render(request, 'platform_admin/notification_settings.html', {'rows': settings_rows})


# ── System health ─────────────────────────────────────────────────────

@platform_staff_required('system_config.manage')
def system_health(request):
    checks = {'database': check_database(), 'redis': check_redis()}
    healthy = all(v == 'ok' for v in checks.values())

    backup_status = None
    backup_config = SystemConfiguration.objects.filter(key=BACKUP_STATUS_KEY).first()
    if backup_config:
        try:
            backup_status = json.loads(backup_config.value)
        except (ValueError, TypeError):
            backup_status = None

    return render(request, 'platform_admin/system_health.html', {
        'checks': checks, 'healthy': healthy, 'backup_status': backup_status,
    })
