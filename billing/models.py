from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from agencies.models import Agency
from utils.tenancy import TenantManager, UnscopedManager

User = settings.AUTH_USER_MODEL


class Plan(models.Model):
    """
    Platform-wide plan catalog — defined by Super Admin, chosen by
    tenants. Not agency-scoped: every tenant sees the same list.
    `max_seats`/`max_bookings_per_month` of NULL means unlimited.
    """
    INTERVAL_CHOICES = [
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='PKR')
    billing_interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default='monthly')
    max_seats = models.PositiveIntegerField(null=True, blank=True, help_text="Blank = unlimited.")
    max_bookings_per_month = models.PositiveIntegerField(null=True, blank=True, help_text="Blank = unlimited.")
    is_active = models.BooleanField(default=True, help_text="Inactive plans are hidden from the signup/upgrade picker.")
    is_default_trial = models.BooleanField(
        default=False,
        help_text="The plan new self-serve signups start on during their trial. Only one plan should have this set.",
    )
    trial_days = models.PositiveIntegerField(default=14)
    features = models.TextField(blank=True, help_text="Extra bullet points shown on the plan card, one per line.")
    badge = models.CharField(max_length=40, blank=True, help_text="Small label on the plan card, e.g. Most popular.")
    is_featured = models.BooleanField(default=False, help_text="Highlight this plan on the billing page.")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'price_amount']

    def __str__(self):
        return self.name

    @property
    def features_list(self):
        return [line.strip() for line in (self.features or '').splitlines() if line.strip()]


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('trialing', _('Trialing')),
        ('active', _('Active')),
        ('past_due', _('Past due')),
        ('expired', _('Expired')),
        ('cancelled', _('Cancelled')),
    ]

    agency = models.OneToOneField(Agency, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing')
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True, help_text="Paid access runs until this date.")
    trial_warning_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    class Meta:
        base_manager_name = 'all_tenants'

    def __str__(self):
        return f"{self.agency.name} — {self.plan.name} ({self.status})"

    @property
    def is_usable(self):
        """Whether this agency currently has access to the app at all."""
        now = timezone.now()
        if self.status == 'active':
            return self.current_period_end is None or self.current_period_end >= now
        if self.status == 'trialing':
            return self.trial_ends_at is None or self.trial_ends_at >= now
        return False

    @property
    def days_left_in_trial(self):
        if self.status != 'trialing' or not self.trial_ends_at:
            return None
        delta = self.trial_ends_at - timezone.now()
        return max(0, delta.days)


class PaymentRecord(models.Model):
    """
    A self-reported "I've paid" claim, confirmed manually by Super Admin —
    the whole payment story for now, on purpose (see billing app docstring
    in views.py): no processor, no fees, no country restrictions.
    """
    METHOD_CHOICES = [
        ('bank_transfer', _('Bank transfer')),
        ('jazzcash', _('JazzCash')),
        ('easypaisa', _('EasyPaisa')),
        ('other', _('Other')),
    ]
    STATUS_CHOICES = [
        ('pending', _('Pending review')),
        ('confirmed', _('Confirmed')),
        ('rejected', _('Rejected')),
    ]

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='payment_records')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='payment_records')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='PKR')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='bank_transfer')
    reference = models.CharField(max_length=255, blank=True, help_text="Transaction ID or note from the payer.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payment_records_submitted')
    submitted_at = models.DateTimeField(auto_now_add=True)
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_records_confirmed')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    class Meta:
        base_manager_name = 'all_tenants'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.agency.name} — {self.amount} {self.currency} ({self.status})"
