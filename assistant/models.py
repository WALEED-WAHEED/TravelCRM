from django.conf import settings
from django.db import models

from agencies.models import Agency
from travelcrm.languages import SUPPORTED_LANGUAGES
from utils.tenancy import TenantManager, UnscopedManager

User = settings.AUTH_USER_MODEL

# Sourced from the product-wide language list (travelcrm/languages.py) so
# this never drifts out of sync with Settings -> Language.
LANGUAGE_CHOICES = SUPPORTED_LANGUAGES


class ChatSession(models.Model):
    """One conversation thread. `preferred_language` is null while the
    assistant auto-detects and mirrors whatever language the user writes
    in; setting it pins responses to that language regardless of input,
    until cleared or changed."""
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='chat_sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=200, blank=True)
    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    class Meta:
        ordering = ['-updated_at']
        base_manager_name = 'all_tenants'

    def __str__(self):
        return self.title or f"Chat #{self.pk}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('tool', 'Tool result'),
    ]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='chat_messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField(blank=True)
    tool_name = models.CharField(max_length=100, blank=True)
    tool_payload = models.JSONField(
        null=True, blank=True,
        help_text="Structured tool call arguments or tool result, kept so the conversation can be replayed to the model on the next turn.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    class Meta:
        ordering = ['created_at']
        base_manager_name = 'all_tenants'


class PendingAction(models.Model):
    """A write the assistant wants to make, held for explicit user
    confirmation before anything is actually written — the model can
    propose, never execute, a write tool."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('executed', 'Executed'),
        ('failed', 'Failed'),
    ]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='pending_actions')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='chat_pending_actions')
    tool_name = models.CharField(max_length=100)
    arguments = models.JSONField()
    summary = models.TextField(help_text="Human-readable description of exactly what will happen, shown on the confirm card.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result = models.JSONField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_pending_actions')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    class Meta:
        ordering = ['-created_at']
        base_manager_name = 'all_tenants'
