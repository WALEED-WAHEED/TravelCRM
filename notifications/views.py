from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy
from django.views.decorators.http import require_POST

from rbac.decorators import permission_required
from rbac.engine import has_capability
from system_config.models import NotificationSettings

from .models import NotificationDeliveryLog

# (event label, email field, sms field, one-line help, icon) — one row per message on the settings page.
EVENTS = [
    (gettext_lazy('Payment received'), 'email_payment_received', 'sms_payment_received',
     gettext_lazy('A receipt for each payment recorded in the ledger.'), 'payment'),
    (gettext_lazy('Voucher generated'), 'email_voucher_generated', 'sms_voucher_generated',
     gettext_lazy('The voucher, once a booking is confirmed.'), 'voucher'),
]
PREFERENCE_FIELDS = [f for _l, e, s, _h, _i in EVENTS for f in (e, s) if f]


def _email_mode():
    """'console' in development (emails are printed, not delivered), else 'smtp'."""
    return 'console' if 'console' in settings.EMAIL_BACKEND or 'locmem' in settings.EMAIL_BACKEND else 'smtp'


def settings_url():
    """Where the notification settings live now: a section of Settings → Company profile."""
    return reverse('profile') + '#notifications'


def preferences_context(request):
    """Everything the notifications section of the company profile page needs."""
    agency = request.user.agency
    settings_obj, _ = NotificationSettings.all_tenants.get_or_create(agency=agency)
    rows = [
        {'label': label, 'email_field': e, 'email_on': getattr(settings_obj, e),
         'sms_field': s, 'sms_on': getattr(settings_obj, s) if s else False, 'hint': hint, 'icon': icon}
        for label, e, s, hint, icon in EVENTS
    ]
    since = timezone.now() - timezone.timedelta(days=30)
    recent = dict(NotificationDeliveryLog.objects.filter(agency=agency, created_at__gte=since)
                  .values_list('status').annotate(n=Count('id')))
    return {
        'rows': rows,
        'can_manage': has_capability(request.user, 'agency_settings', 'manage'),
        'email_mode': _email_mode(),
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'recent': {k: recent.get(k, 0) for k in ('sent', 'failed', 'skipped')},
    }


@permission_required('agency_settings', 'view')
def preferences(request):
    """Saves the switches; viewing them happens on the company profile page (old links land there)."""
    agency = request.user.agency
    if not agency:
        messages.error(request, gettext("This is a tenant screen."))
        return redirect('root')

    if request.method == 'POST':
        if not has_capability(request.user, 'agency_settings', 'manage'):
            messages.error(request, gettext("You don't have permission to change these settings."))
            return redirect(settings_url())
        settings_obj, _ = NotificationSettings.all_tenants.get_or_create(agency=agency)
        for field in PREFERENCE_FIELDS:
            setattr(settings_obj, field, request.POST.get(field) == 'on')
        settings_obj.save()
        messages.success(request, gettext("Notification preferences updated."))
    return redirect(settings_url())


@permission_required('agency_settings', 'manage')
@require_POST
def send_test_email(request):
    """Send a test message to the signed-in user, so an owner can check the email setup works."""
    to = (request.user.email or '').strip()
    if not to:
        messages.error(request, gettext("Add an email address to your account first (Profile), then try again."))
        return redirect(settings_url())
    try:
        send_mail(
            subject=gettext("Test email from %(agency)s") % {'agency': request.user.agency.name},
            message=gettext("This is a test. If you can read this, booking notifications can reach your customers."),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            fail_silently=False,
        )
    except Exception as e:  # SMTP misconfiguration, network, auth…
        messages.error(request, gettext("Test email failed: %(err)s") % {'err': str(e)[:300]})
        return redirect(settings_url())
    if _email_mode() == 'console':
        messages.warning(request, gettext("Test email created, but this server is in development mode: it was printed in the server console instead of being delivered. Set EMAIL_BACKEND to SMTP in .env to send real emails."))
    else:
        messages.success(request, gettext("Test email sent to %(to)s — check your inbox.") % {'to': to})
    return redirect(settings_url())


@permission_required('agency_settings', 'view')
def recent(request):
    """The bell menu: the latest messages the system sent for this agency (loaded when the bell is opened)."""
    agency = request.user.agency
    items = []
    if agency:
        items = list(NotificationDeliveryLog.objects.filter(agency=agency).select_related('booking').order_by('-created_at', '-id')[:8])
    return render(request, 'notifications/_recent.html', {'items': items})


@permission_required('agency_settings', 'view')
def delivery_log(request):
    agency = request.user.agency
    if not agency:
        messages.error(request, gettext("This is a tenant screen."))
        return redirect('root')
    from member import attendance as att

    tz = att.office_tz(att.get_settings(agency))
    f = {k: (request.GET.get(k) or '').strip() for k in ('status', 'event', 'channel')}
    qs = NotificationDeliveryLog.objects.filter(agency=agency).select_related('booking')
    if f['event'] in dict(NotificationDeliveryLog.EVENT_CHOICES):
        qs = qs.filter(event_type=f['event'])
    if f['channel'] in dict(NotificationDeliveryLog.CHANNEL_CHOICES):
        qs = qs.filter(channel=f['channel'])
    counts = dict(qs.values_list('status').annotate(n=Count('id')))  # cards ignore the status filter
    if f['status'] in dict(NotificationDeliveryLog.STATUS_CHOICES):
        qs = qs.filter(status=f['status'])
    page = Paginator(qs.order_by('-created_at', '-id'), 50).get_page(request.GET.get('page'))
    rows = [{
        'e': e,
        # Pre-formatted: the |date filter would convert back to the server's UTC.
        'when_date': timezone.localtime(e.created_at, tz).strftime('%d %b %Y'),
        'when_time': timezone.localtime(e.created_at, tz).strftime('%I:%M %p').lstrip('0'),
    } for e in page.object_list]
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'notifications/delivery_log.html', {
        'page_title': 'Sent messages',
        'rows': rows,
        'page': page,
        'f': f,
        'filtered': any(f.values()),
        'counts': {k: counts.get(k, 0) for k in ('sent', 'failed', 'skipped')},
        'event_choices': NotificationDeliveryLog.EVENT_CHOICES,
        'channel_choices': NotificationDeliveryLog.CHANNEL_CHOICES,
        'status_choices': NotificationDeliveryLog.STATUS_CHOICES,
        'query': query.urlencode(),
        'email_mode': _email_mode(),
    })
