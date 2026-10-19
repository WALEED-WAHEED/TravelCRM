import logging

from celery import shared_task

from utils.tenancy import tenant_context

logger = logging.getLogger(__name__)


@shared_task(name='notifications.send_notification_task', ignore_result=True)
def send_notification_task(event_type, booking_id, payment_id=None):
    """
    Runs in the Celery worker process — no HTTP request, so no
    TenantMiddleware has set tenant context. Establish it explicitly
    before touching the database (same lesson Phase 03 learned the hard
    way with AuditLog: writes without this context either get silently
    mis-scoped or, where RLS is enforced, rejected outright).
    """
    from member.models import Booking, BookingPayment

    from .engine import send_notification

    # The context must be set *before* the first query: when the app runs as the scoped travelcrm_app role,
    # RLS hides the booking from a session with no tenant set, and the task would silently do nothing.
    # tenant_context also restores the previous state, so nothing leaks into the next task on this worker.
    with tenant_context(bypass=True):
        booking = Booking.all_tenants.filter(pk=booking_id).select_related('agency').first()
        if not booking:
            logger.warning("send_notification_task: booking %s no longer exists", booking_id)
            return
        with tenant_context(agency_id=booking.agency_id, bypass=True):
            payment = BookingPayment.objects.filter(pk=payment_id).first() if payment_id else None
            send_notification(event_type, booking, payment=payment)


def dispatch(event_type, booking, payment=None):
    """
    The one call site everything else should use. Tries to hand off to
    the Celery queue; if no broker is reachable (e.g. local dev without
    Redis running), falls back to sending inline rather than losing the
    notification — logged either way, since dev environments not always
    having a worker running as a fact of life, not a reason to no-op.
    """
    payment_id = payment.pk if payment else None
    try:
        send_notification_task.delay(event_type, booking.pk, payment_id)
    except Exception:
        logger.warning(
            "Celery broker unreachable — sending %s notification for booking %s inline instead of queuing.",
            event_type, booking.pk,
        )
        from .engine import send_notification
        send_notification(event_type, booking, payment=payment)
