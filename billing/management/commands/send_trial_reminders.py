"""
Warns a trialing agency's owner before their trial runs out, instead of
letting the access gate (billing/middleware.py) be the first they hear
of it. Schedule daily via cron / Windows Task Scheduler:

    python manage.py send_trial_reminders

Sends once per subscription (tracked via trial_warning_sent_at) when 3
days or fewer remain in the trial.
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone, translation
from django.utils.translation import gettext

from billing.models import Subscription


class Command(BaseCommand):
    help = "Email agency owners whose trial ends within 3 days and haven't been warned yet."

    def handle(self, *args, **options):
        cutoff = timezone.now() + timezone.timedelta(days=3)
        due = Subscription.all_tenants.filter(
            status='trialing',
            trial_ends_at__lte=cutoff,
            trial_ends_at__gte=timezone.now(),
            trial_warning_sent_at__isnull=True,
        ).select_related('agency', 'plan')

        sent = 0
        for sub in due:
            owner = sub.agency.users.filter(role='member', is_active=True).first()
            if not owner or not owner.email:
                continue
            try:
                with translation.override(owner.preferred_language or settings.LANGUAGE_CODE):
                    subject = gettext("Your trial ends in %(days)s day(s)") % {'days': sub.days_left_in_trial}
                    body = gettext(
                        "Hi %(name)s,\n\n"
                        "Your trial of %(plan)s for %(agency)s ends on %(end_date)s. Subscribe from the "
                        "Billing page in your dashboard to keep access without interruption.\n"
                    ) % {
                        'name': owner.first_name or owner.username,
                        'plan': sub.plan.name,
                        'agency': sub.agency.name,
                        'end_date': sub.trial_ends_at.strftime('%Y-%m-%d'),
                    }
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[owner.email],
                    fail_silently=False,
                )
                sub.trial_warning_sent_at = timezone.now()
                sub.save(update_fields=['trial_warning_sent_at'])
                sent += 1
            except Exception as e:
                self.stderr.write(f"Failed to email {sub.agency.name}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} trial-ending reminder(s)."))
