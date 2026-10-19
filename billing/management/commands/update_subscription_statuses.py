"""
Makes Subscription.status a truthful historical record instead of a
manually-selectable label that nothing ever transitions automatically.
Mirrors is_usable's own logic (billing/models.py) so this command doesn't
introduce a second, possibly-diverging source of truth for "is this
agency's access actually lapsed" — it just makes the stored `status`
catch up to what the access gate (billing/middleware.py) already decides
live on every request.

Schedule daily via cron / Windows Task Scheduler, same convention as
send_trial_reminders.py (no Celery Beat in this repo):

    python manage.py update_subscription_statuses

Transitions:
  trialing + trial_ends_at passed              -> expired
  active   + current_period_end passed         -> past_due
  past_due + current_period_end + 7d grace passed -> expired

Each transition is a plain .save(), so it's picked up automatically by
the generic audit trail (utils/audit.py — Subscription is registered)
without any extra logging code here.
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone, translation
from django.utils.translation import gettext

from billing.models import Subscription
from utils.tenancy import tenant_context

GRACE_DAYS = 7


class Command(BaseCommand):
    help = "Transition trial/active/past_due subscriptions that have actually lapsed, per is_usable's own rules."

    def handle(self, *args, **options):
        # Runs across every agency outside a request: under the scoped travelcrm_app role, RLS would
        # otherwise hide every row and the command would silently do nothing.
        with tenant_context(bypass=True):
            return self._run(*args, **options)

    def _run(self, *args, **options):
        now = timezone.now()
        expired_from_trial = 0
        past_due = 0
        expired_from_past_due = 0

        trialing = Subscription.all_tenants.filter(
            status='trialing', trial_ends_at__isnull=False, trial_ends_at__lt=now,
        ).select_related('agency', 'plan')
        for sub in trialing:
            sub.status = 'expired'
            sub.save(update_fields=['status', 'updated_at'])
            expired_from_trial += 1

        active_lapsed = Subscription.all_tenants.filter(
            status='active', current_period_end__isnull=False, current_period_end__lt=now,
        ).select_related('agency', 'plan')
        for sub in active_lapsed:
            sub.status = 'past_due'
            sub.save(update_fields=['status', 'updated_at'])
            past_due += 1
            self._notify_past_due(sub)

        grace_cutoff = now - timezone.timedelta(days=GRACE_DAYS)
        past_due_lapsed = Subscription.all_tenants.filter(
            status='past_due', current_period_end__isnull=False, current_period_end__lt=grace_cutoff,
        )
        for sub in past_due_lapsed:
            sub.status = 'expired'
            sub.save(update_fields=['status', 'updated_at'])
            expired_from_past_due += 1

        self.stdout.write(self.style.SUCCESS(
            f"trialing->expired: {expired_from_trial}, active->past_due: {past_due}, "
            f"past_due->expired (grace lapsed): {expired_from_past_due}"
        ))

    def _notify_past_due(self, sub):
        owner = sub.agency.users.filter(role='member', is_active=True).first()
        if not owner or not owner.email:
            return
        try:
            with translation.override(owner.preferred_language or settings.LANGUAGE_CODE):
                subject = gettext("Your payment is overdue")
                body = gettext(
                    "Your subscription to the %(plan)s plan is now past due. "
                    "Please submit a payment to avoid losing access once the grace period ends."
                ) % {'plan': sub.plan.name}
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [owner.email], fail_silently=True)
        except Exception:
            pass
