"""
Reminds a booking's contact before an installment comes due, and flags
overdue ones — the same "warn before the hard wall" pattern as
billing/management/commands/send_trial_reminders.py. Schedule daily:

    python manage.py send_installment_reminders
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone, translation
from django.utils.translation import gettext

from notifications.engine import _resolve_recipient
from payments.models import Installment


class Command(BaseCommand):
    help = "Email booking contacts about installments due within 3 days or already overdue."

    def handle(self, *args, **options):
        today = timezone.localdate()
        cutoff = today + timezone.timedelta(days=3)
        due = Installment.all_tenants.filter(
            status='pending', due_date__lte=cutoff, reminder_sent_at__isnull=True,
        ).select_related('payment_plan__booking', 'agency')

        sent = 0
        for installment in due:
            booking = installment.payment_plan.booking
            recipient_email, recipient_name, recipient_language = _resolve_recipient(booking)
            if not recipient_email:
                continue

            overdue = installment.due_date < today
            try:
                with translation.override(recipient_language or settings.LANGUAGE_CODE):
                    subject = (
                        gettext("Payment overdue — %(voucher)s") % {'voucher': booking.voucher_number} if overdue
                        else gettext("Payment due soon — %(voucher)s") % {'voucher': booking.voucher_number}
                    )
                    body = gettext(
                        "Dear %(recipient)s,\n\n"
                        "The '%(label)s' installment of %(amount)s for booking %(voucher)s was due on %(due_date)s%(overdue_note)s.\n\n"
                        "Please arrange payment at your earliest convenience.\n"
                    ) % {
                        'recipient': recipient_name or booking.client_company or gettext('Traveler'),
                        'label': installment.label,
                        'amount': installment.amount,
                        'voucher': booking.voucher_number,
                        'due_date': installment.due_date,
                        'overdue_note': gettext(' and is now overdue') if overdue else '',
                    }
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
                installment.reminder_sent_at = timezone.now()
                if overdue:
                    installment.status = 'overdue'
                installment.save(update_fields=['reminder_sent_at', 'status', 'updated_at'])
                sent += 1
            except Exception as e:
                self.stderr.write(f"Failed to email booking {booking.voucher_number}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} installment reminder(s)."))
