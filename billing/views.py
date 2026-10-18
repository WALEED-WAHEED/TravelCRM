from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext

from accounts.models import User
from agencies.models import Agency
from rbac.decorators import permission_required
from rbac.models import Role
from utils.ratelimit import is_rate_limited
from utils.tenancy import apply_db_session_context, set_current_tenant, set_platform_admin_bypass

from .models import PaymentRecord, Plan, Subscription
from .usage import get_booking_usage_this_month, get_seat_usage, get_subscription


def signup(request):
    """Public, unauthenticated self-serve signup — the whole point of
    this phase: a new agency exists without you doing anything."""
    if request.user.is_authenticated:
        return redirect('root')

    plans = Plan.objects.filter(is_active=True).order_by('sort_order')
    trial_plan = Plan.objects.filter(is_default_trial=True, is_active=True).first()

    if request.method == 'POST':
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        if is_rate_limited(f"signup:{client_ip}", limit=5, window_seconds=600):
            messages.error(request, gettext("Too many signup attempts. Please wait a few minutes and try again."))
            return render(request, 'billing/signup.html', {'plans': plans, 'form_data': request.POST})

        agency_name = request.POST.get('agency_name', '').strip()
        owner_username = request.POST.get('owner_username', '').strip()
        owner_email = request.POST.get('owner_email', '').strip()
        owner_password = request.POST.get('owner_password', '').strip()

        errors = []
        if not agency_name:
            errors.append("Agency name is required.")
        if not owner_username:
            errors.append("Choose a username.")
        elif User.objects.filter(username=owner_username).exists():
            errors.append(f"Username '{owner_username}' is already taken.")
        if not owner_password or len(owner_password) < 8:
            errors.append("Password must be at least 8 characters.")
        if not trial_plan:
            errors.append("Signup isn't available right now — no trial plan is configured. Please contact us.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'billing/signup.html', {'plans': plans, 'form_data': request.POST})

        code = _generate_agency_code(agency_name)
        owner_role = Role.all_tenants.filter(agency__isnull=True, is_template=True, name='Owner').first()

        # This request has no tenant yet — it's creating one. RLS on
        # billing_subscription would otherwise reject the INSERT, the
        # same way it rejected AuditLog writes from context-less code in
        # Phase 03: the row's agency_id can't match a tenant context
        # that doesn't exist yet. Bypass explicitly, the same trust
        # boundary Super Admin's tenant_create gets automatically from
        # its superuser session.
        set_platform_admin_bypass(True)
        apply_db_session_context(bypass=True, tenant_id=None)
        try:
            with transaction.atomic():
                agency = Agency.objects.create(name=agency_name, code=code, email=owner_email, is_active=True)
                owner = User.objects.create(
                    username=owner_username, email=owner_email, password=make_password(owner_password),
                    role='member', agency=agency, custom_role=owner_role,
                )
                Subscription.all_tenants.create(
                    agency=agency, plan=trial_plan, status='trialing',
                    trial_ends_at=timezone.now() + timezone.timedelta(days=trial_plan.trial_days),
                )
        finally:
            set_platform_admin_bypass(False)
            set_current_tenant(None)

        login(request, owner, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, gettext("Welcome! Your %(days)s-day trial has started.") % {'days': trial_plan.trial_days})
        return redirect('root')

    return render(request, 'billing/signup.html', {'plans': plans, 'form_data': {}})


def _generate_agency_code(name):
    import re
    import uuid
    base = re.sub(r'[^A-Z0-9]', '', name.upper())[:8] or 'AGENCY'
    for _ in range(10):
        candidate = f"{base}{uuid.uuid4().hex[:4].upper()}"[:20]
        if not Agency.objects.filter(code=candidate).exists():
            return candidate
    return uuid.uuid4().hex[:12].upper()


@permission_required('agency_settings', 'view')
def billing_home(request):
    agency = request.user.agency
    if not agency:
        messages.error(request, gettext("This is a tenant screen."))
        return redirect('root')

    sub = get_subscription(agency)
    plans = list(Plan.objects.filter(is_active=True).order_by('sort_order', 'price_amount'))
    current_price = sub.plan.price_amount if sub else None
    for plan in plans:
        if sub and plan.pk == sub.plan_id:
            plan.cta = 'current'
        elif current_price is not None and plan.price_amount > current_price:
            plan.cta = 'upgrade'
        elif current_price is not None and plan.price_amount < current_price:
            plan.cta = 'downgrade'
        else:
            plan.cta = 'choose'
    payment_history = PaymentRecord.objects.filter(agency=agency).order_by('-submitted_at')[:50]
    can_manage = _can_manage_billing(request.user)
    seats, bookings = get_seat_usage(agency), get_booking_usage_this_month(agency)

    def pct(used, limit):
        return min(100, round(used * 100 / limit)) if limit else 0

    return render(request, 'billing/home.html', {
        'subscription': sub,
        'plans': plans,
        'payment_history': payment_history,
        'seat_usage': seats,
        'booking_usage': bookings,
        'seat_pct': pct(seats, sub.plan.max_seats if sub else None),
        'booking_pct': pct(bookings, sub.plan.max_bookings_per_month if sub else None),
        'can_manage': can_manage,
    })


def _can_manage_billing(user):
    from rbac.engine import has_capability
    return has_capability(user, 'agency_settings', 'manage')


@permission_required('agency_settings', 'manage')
def submit_payment(request, plan_id):
    agency = request.user.agency
    if not agency:
        messages.error(request, gettext("This is a tenant screen."))
        return redirect('root')

    plan = get_object_or_404(Plan, pk=plan_id, is_active=True)

    if request.method == 'POST':
        PaymentRecord.objects.create(
            agency=agency, plan=plan, amount=plan.price_amount, currency=plan.currency,
            method=request.POST.get('method', 'bank_transfer'),
            reference=request.POST.get('reference', '').strip(),
            submitted_by=request.user,
        )
        messages.success(request, gettext("Thanks — we've recorded your payment and will confirm it shortly."))
        return redirect('member-billing')

    return render(request, 'billing/submit_payment.html', {'plan': plan})
