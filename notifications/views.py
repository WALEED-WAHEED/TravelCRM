from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy
from django.views.decorators.http import require_POST

from rbac.decorators import permission_required
from rbac.engine import has_capability
from system_config.models import NotificationSettings

from .models import NotificationDeliveryLog

# (event label, email field, sms field or None) — one row per event on the settings page.
EVENTS = [
    (gettext_lazy('Booking confirmed'), 'email_booking_confirmation', 'sms_booking_confirmation'),
    (gettext_lazy('Payment received'), 'email_payment_received', 'sms_payment_received'),
    (gettext_lazy('Voucher generated'), 'email_voucher_generated', 'sms_voucher_generated'),
    (gettext_lazy('Booking cancelled'), 'email_booking_cancelled', None),
]
PREFERENCE_FIELDS = [f for _l, e, s in EVENTS for f in (e, s) if f]


def _email_mode():
    """'console' in development (emails are printed, not delivered), else 'smtp'."""
    return 'console' if 'console' in settings.EMAIL_BACKEND or 'locmem' in settings.EMAIL_BACKEND else 'smtp'


@permission_required('agency_settings', 'view')
def preferences(request):
    agency = request.user.agency
    if not agency:
        messages.error(request, gettext("This is a tenant screen."))
        return redirect('root')

    settings_obj, _ = NotificationSettings.all_tenants.get_or_create(agency=agency)
    can_manage = has_capability(request.user, 'agency_settings', 'manage')

    if request.method == 'POST':
        if not can_manage:
            messages.error(request, gettext("You don't have permission to change these settings."))
            return redirect('notifications-preferences')
        for field in PREFERENCE_FIELDS:
            setattr(settings_obj, field, request.POST.get(field) == 'on')
        settings_obj.save()
        messages.success(request, gettext("Notification preferences updated."))
        return redirect('notifications-preferences')

    rows = [
        {'label': label, 'email_field': e, 'email_on': getattr(settings_obj, e),
         'sms_field': s, 'sms_on': getattr(settings_obj, s) if s else False}
        for label, e, s in EVENTS
    ]
    since = timezone.now() - timezone.timedelta(days=30)
    recent = dict(NotificationDeliveryLog.objects.filter(agency=agency, created_at__gte=since)
                  .values_list('status').annotate(n=Count('id')))
    return render(request, 'notifications/preferences.html', {
        'page_title': 'Notifications',
        'rows': rows,
        'can_manage': can_manage,
        'email_mode': _email_mode(),
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'recent': {k: recent.get(k, 0) for k in ('sent', 'failed', 'skipped')},
    })


@permission_required('agency_settings', 'manage')
@require_POST
def send_test_email(request):
    """Send a test message to the signed-in user, so an owner can check the email setup works."""
    to = (request.user.email or '').strip()
    if not to:
        messages.error(request, gettext("Add an email address to your account first (Profile), then try again."))
        return redirect('notifications-preferences')
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
        return redirect('notifications-preferences')
    if _email_mode() == 'console':
        messages.warning(request, gettext("Test email created, but this server is in development mode: it was printed in the server console instead of being delivered. Set EMAIL_BACKEND to SMTP in .env to send real emails."))
    else:
        messages.success(request, gettext("Test email sent to %(to)s — check your inbox.") % {'to': to})
    return redirect('notifications-preferences')


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
