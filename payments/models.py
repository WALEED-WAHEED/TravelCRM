from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from agencies.models import Agency
from utils.tenancy import TenantManager, UnscopedManager

User = settings.AUTH_USER_MODEL


class PaymentPlan(models.Model):
    """A deposit/balance (or any N-part) payment schedule for one booking,
    instead of one lump sum recorded whenever someone remembers to."""
    booking = models.OneToOneField('member.Booking', on_delete=models.CASCADE, related_name='payment_plan')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='payment_plans')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payment_plans_created')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    class Meta:
        base_manager_name = 'all_tenants'

    def __str__(self):
        return f"Payment plan for {self.booking.voucher_number}"

    @property
    def total_scheduled(self):
        return sum((i.amount for i in self.installments.all()), start=0)

    @property
    def total_paid(self):
        return sum((i.amount for i in self.installments.filter(status='paid')), start=0)


class Installment(models.Model):
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('paid', _('Paid')),
        ('overdue', _('Overdue')),
        ('waived', _('Waived')),
    ]

    payment_plan = models.ForeignKey(PaymentPlan, on_delete=models.CASCADE, related_name='installments')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='installments')
    sequence = models.PositiveIntegerField(default=1)
    label = models.CharField(max_length=100, help_text="e.g. Deposit, Balance, Installment 2")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    class Meta:
        ordering = ['sequence', 'due_date']
        base_manager_name = 'all_tenants'

    def __str__(self):
        return f"{self.label} — {self.amount} due {self.due_date}"

    @property
    def is_overdue(self):
        return self.status == 'pending' and self.due_date < timezone.localdate()


class SupplierPayment(models.Model):
    """Money the agency has paid out to a supplier (hotel/flight/transport
    provider) — the outbound side of the ledger, mirroring BookingPayment
    on the inbound side."""
    METHOD_CHOICES = [
        ('cash', _('Cash')),
        ('bank_transfer', _('Bank transfer')),
        ('card', _('Card')),
        ('other', _('Other')),
    ]

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='supplier_payments')
    supplier = models.ForeignKey('member.Contact', on_delete=models.CASCADE, related_name='payments_received')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='PKR')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='bank_transfer')
    reference = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='supplier_payments_made')
    paid_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    class Meta:
        ordering = ['-paid_at']
        base_manager_name = 'all_tenants'

    def __str__(self):
        return f"{self.amount} {self.currency} to {self.supplier.name}"
