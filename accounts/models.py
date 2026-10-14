from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from travelcrm.languages import SUPPORTED_LANGUAGES


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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    class Meta:
        ordering = ['-created_at']
