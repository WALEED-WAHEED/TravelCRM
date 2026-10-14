from django.conf import settings
from django.db import models
from django.utils import timezone

from agencies.models import Agency


class ImpersonationSession(models.Model):
    """
    Audit trail for Super Admin "log in as this user" support access.
    One row per impersonation session, open (ended_at=None) while active.
    """
    super_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='impersonations_started',
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='impersonations_received',
    )
    target_agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='impersonation_sessions')
    reason = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        status = "active" if self.ended_at is None else "ended"
        return f"{self.super_admin} as {self.target_user} ({status})"


class StaffAccess(models.Model):
    """
    Grants a non-superuser platform staff account (is_staff=True,
    is_superuser=False) a scoped set of platform_admin capabilities (see
    catalog.py). Real Django superusers don't need a row here — they
    bypass this entirely and always have full access, the same "root
    bypasses the permission system" shape rbac/engine.py already uses.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_access',
    )
    role_label = models.CharField(
        max_length=100, blank=True,
        help_text="Free-text label for your own bookkeeping, e.g. 'Support Agent' or 'Billing Ops'. Not enforced.",
    )
    capabilities = models.JSONField(default=list, blank=True, help_text="List of capability keys from catalog.py.")
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_access_granted',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} ({self.role_label or 'staff'})"


class Announcement(models.Model):
    """
    Super Admin -> tenant broadcast messaging (e.g. maintenance notices).
    Rendered as a dismissible banner in the tenant app shell (see
    context_processors.active_announcements); dismissal is tracked
    client-side (localStorage), not here — no per-user read-state model.
    """
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    title = models.CharField(max_length=200)
    body = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    target_agencies = models.ManyToManyField(
        Agency, blank=True, related_name='announcements',
        help_text="Leave empty to target every tenant.",
    )
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True, help_text="Blank = stays active until manually deactivated.")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_live(self):
        now = timezone.now()
        if not self.is_active or self.starts_at > now:
            return False
        return self.ends_at is None or self.ends_at >= now
