from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from travelcrm.languages import SUPPORTED_LANGUAGES

from .avatars import avatar_upload_to


class User(AbstractUser):
    """
    Custom user model with role-based access
    """
    ROLE_CHOICES = [
        ('admin', _('Admin')),
        ('member', _('Member')),
        ('agent', _('Agent')),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='agent'
    )
    agency = models.ForeignKey(
        'agencies.Agency',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users'
    )
    custom_role = models.ForeignKey(
        'rbac.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_users',
        help_text="Fine-grained role (Team & Roles). Falls back to the coarse `role` field's default template if unset.",
    )
    phone = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(
        max_length=10, choices=SUPPORTED_LANGUAGES, blank=True, null=True,
        help_text="Account-wide UI language, set from Settings -> Language. Blank means auto-detect from the browser, falling back to English.",
    )
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True, help_text="Profile picture, set by the user from Settings -> My profile.")
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Set when removed from the team: the person is hidden and cannot sign in, but their bookings, payments and vouchers are kept.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    class Meta:
        ordering = ['-created_at']
