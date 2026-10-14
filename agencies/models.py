from django.conf import settings
from django.db import models


class Agency(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    default_currency = models.CharField(
        max_length=3, default='PKR',
        help_text="ISO 4217 code used as the default for new bookings, inventory, and ledger entries in this agency.",
    )
    attendance_admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_admin_for_agencies",
    )
    attendance_admin_password_hash = models.CharField(max_length=256, blank=True, default="")
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agencies_suspended",
    )
    suspended_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def member_count(self):
        return self.users.filter(role='member').count()

    @property
    def agent_count(self):
        return self.users.filter(role='agent').count()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Agencies'
        ordering = ['-created_at']
