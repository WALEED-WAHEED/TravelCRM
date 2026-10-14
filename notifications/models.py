from django.db import models
from django.utils.translation import gettext_lazy as _

from agencies.models import Agency
from member.models import Booking
from utils.tenancy import TenantManager, UnscopedManager


class NotificationDeliveryLog(models.Model):
    """
    One row per notification attempt — the "visible delivery status"
    the roadmap asked for. Written by notifications/engine.py regardless
    of outcome (sent, failed, or skipped because the tenant disabled
    that event/channel or no recipient could be found), so an agency
    can see *why* a customer didn't get an email instead of just
    wondering.
    """
    EVENT_CHOICES = [
        ('booking_confirmation', _('Booking confirmation')),
        ('payment_receipt', _('Payment receipt')),
        ('voucher_generated', _('Voucher generated')),
        ('booking_cancelled', _('Booking cancelled')),
    ]
    CHANNEL_CHOICES = [
        ('email', _('Email')),
        ('sms', _('SMS')),
    ]
    STATUS_CHOICES = [
        ('sent', _('Sent')),
        ('failed', _('Failed')),
        ('skipped', _('Skipped')),
    ]

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='notification_deliveries')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='notification_deliveries')
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    recipient = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    detail = models.TextField(blank=True, help_text="Error message, or the reason it was skipped.")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    class Meta:
        ordering = ['-created_at']
        base_manager_name = 'all_tenants'
        indexes = [
            models.Index(fields=['agency', 'created_at']),
            # (no separate index on `booking`: the ForeignKey already creates one)
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} -> {self.recipient or '(no recipient)'}: {self.status}"
