"""
Render + send + log a notification. Never raises — a notification
failure must never break the booking/payment action that triggered it;
every outcome (sent, failed, skipped) is written to
NotificationDeliveryLog instead, so it's visible rather than silent.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template import Context, Template
from django.utils import translation
from django.utils.html import strip_tags
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from system_config.models import EmailTemplate, NotificationSettings

from .models import NotificationDeliveryLog

logger = logging.getLogger(__name__)

DISABLED_DETAIL = _("Disabled in this agency's notification settings.")
NO_RECIPIENT_DETAIL = _("No contact or traveler on this booking has an email address on file.")
SMS_NOT_CONFIGURED_DETAIL = _("SMS is enabled in settings, but no SMS provider is configured yet.")

EVENT_CONFIG = {
    'booking_confirmation': {
        'email_field': 'email_booking_confirmation',
        'sms_field': 'sms_booking_confirmation',
        'default_subject': 'Booking Confirmed — {{ booking.voucher_number }}',
        'default_body': (
            "<p>Dear {{ recipient_name }},</p>"
            "<p>Your booking <strong>{{ booking.voucher_number }}</strong> with "
            "{{ agency.name }} has been confirmed.</p>"
            "<p>Travelers: {{ mutamer_names }}<br>"
            "Total: {{ booking.total_amount }}</p>"
            "<p>Thank you for booking with us.</p>"
        ),
    },
    'payment_receipt': {
        'email_field': 'email_payment_received',
        'sms_field': 'sms_payment_received',
        'default_subject': 'Payment Received — {{ booking.voucher_number }}',
        'default_body': (
            "<p>Dear {{ recipient_name }},</p>"
            "<p>We've received a payment of <strong>{{ payment.amount }}</strong> "
            "({{ payment.get_payment_method_display }}) for booking "
            "{{ booking.voucher_number }}.</p>"
            "<p>Thank you.</p>"
        ),
    },
    'voucher_generated': {
        'email_field': 'email_voucher_generated',
        'sms_field': 'sms_voucher_generated',
        'default_subject': 'Your Voucher is Ready — {{ booking.voucher_number }}',
        'default_body': (
            "<p>Dear {{ recipient_name }},</p>"
            "<p>Your voucher for booking <strong>{{ booking.voucher_number }}</strong> "
            "is ready. Your agent can share the printable copy with you.</p>"
        ),
    },
    'booking_cancelled': {
        'email_field': 'email_booking_cancelled',
        'sms_field': None,
        'default_subject': 'Booking Cancelled — {{ booking.voucher_number }}',
        'default_body': (
            "<p>Dear {{ recipient_name }},</p>"
            "<p>Booking <strong>{{ booking.voucher_number }}</strong> with "
            "{{ agency.name }} has been cancelled.</p>"
        ),
    },
}


def _resolve_recipient(booking):
    """Best-available email for this booking: its contacts first, then
    its travelers. Booking itself has no email field — only a company
    name and WhatsApp number — so there's no single authoritative source.
    Language comes only from Contact — a traveler row has no language
    field, so a traveler-only recipient falls back to the site default."""
    contact_link = booking.booking_contacts.select_related('contact').filter(contact__email__gt='').first()
    if contact_link:
        return contact_link.contact.email, contact_link.contact.name, contact_link.contact.preferred_language
    mutamer_link = booking.booking_mutamers.filter(email__gt='').first()
    if mutamer_link:
        return mutamer_link.email, mutamer_link.name, None
    return None, None, None


def _get_template(agency, event_type):
    template = EmailTemplate.objects.filter(agency=agency, template_type=event_type, is_default=True).first()
    if not template:
        template = EmailTemplate.objects.filter(agency__isnull=True, template_type=event_type, is_default=True).first()
    return template


def _render(text, context_dict):
    return Template(text).render(Context(context_dict))


def send_notification(event_type, booking, payment=None, extra_context=None):
    """Synchronous send — safe to call directly, or from a Celery task
    (see notifications/tasks.py) for the actual background-job path."""
    config = EVENT_CONFIG.get(event_type)
    if not config:
        logger.error("Unknown notification event_type: %s", event_type)
        return

    agency = booking.agency
    settings_obj = NotificationSettings.all_tenants.filter(agency=agency).first()
    email_enabled = getattr(settings_obj, config['email_field'], True) if settings_obj else True

    if not email_enabled:
        NotificationDeliveryLog.all_tenants.create(
            agency=agency, booking=booking, event_type=event_type, channel='email',
            status='skipped', detail=str(DISABLED_DETAIL),
        )
        return

    recipient_email, recipient_name, recipient_language = _resolve_recipient(booking)
    mutamer_names = ", ".join(
        bm.name for bm in booking.booking_mutamers.all()[:10]
    ) or "—"
    lang = recipient_language or settings.LANGUAGE_CODE

    if not recipient_email:
        NotificationDeliveryLog.all_tenants.create(
            agency=agency, booking=booking, event_type=event_type, channel='email',
            status='skipped', detail=str(NO_RECIPIENT_DETAIL),
        )
    else:
        template = _get_template(agency, event_type)
        # A per-agency customized template is the agency's own wording —
        # never machine-translated. Only our own copy (the platform
        # default row, or the EVENT_CONFIG fallback if it's missing
        # entirely) gets translated to the recipient's language.
        is_platform_default = template is None or template.agency_id is None
        subject_src = template.subject if template else config['default_subject']
        body_src = template.html_content if template else config['default_body']
        try:
            with translation.override(lang):
                context = {
                    'booking': booking,
                    'agency': agency,
                    'payment': payment,
                    'recipient_name': recipient_name or booking.client_company or gettext('Traveler'),
                    'mutamer_names': mutamer_names,
                }
                if extra_context:
                    context.update(extra_context)
                if is_platform_default:
                    subject_src = gettext(subject_src)
                    body_src = gettext(body_src)
                subject = _render(subject_src, context)
                html_body = _render(body_src, context)
            send_mail(
                subject=subject,
                message=strip_tags(html_body),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_body,
                fail_silently=False,
            )
            NotificationDeliveryLog.all_tenants.create(
                agency=agency, booking=booking, event_type=event_type, channel='email',
                recipient=recipient_email, subject=subject, status='sent',
            )
        except Exception as e:
            logger.exception("Failed to send %s notification for booking %s", event_type, booking.pk)
            NotificationDeliveryLog.all_tenants.create(
                agency=agency, booking=booking, event_type=event_type, channel='email',
                recipient=recipient_email, status='failed', detail=str(e)[:2000],
            )

    # SMS: the data model (NotificationSettings.sms_*) and provider
    # scaffolding (system_config.APIKey key_type='sms_provider') exist,
    # but no actual SMS provider is integrated anywhere in this codebase
    # — log honestly rather than pretending to send.
    sms_field = config.get('sms_field')
    if sms_field and settings_obj and getattr(settings_obj, sms_field, False):
        NotificationDeliveryLog.all_tenants.create(
            agency=agency, booking=booking, event_type=event_type, channel='sms',
            status='skipped', detail=str(SMS_NOT_CONFIGURED_DETAIL),
        )
