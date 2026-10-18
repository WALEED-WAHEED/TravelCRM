from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from agencies.models import Agency
from utils.tenancy import TenantManager, TenantOrGlobalManager, UnscopedManager

User = settings.AUTH_USER_MODEL


class SAASProductConfig(models.Model):
    """Singleton model for global SaaS product branding and settings"""

    product_name = models.CharField(
        max_length=100,
        default="Travel Management System",
        help_text="Global product name displayed in headers, titles, and sidebars"
    )
    slogan = models.CharField(
        max_length=150,
        default="Travel Management System",
        help_text="Short tagline or slogan displayed below the brand name (e.g. 'Enterprise B2B Travel Platform')"
    )
    logo = models.ImageField(upload_to='saas_branding/', null=True, blank=True, help_text="Upload custom SaaS logo here")
    favicon = models.ImageField(upload_to='saas_branding/', null=True, blank=True, help_text="Upload custom browser tab favicon")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    # Parent company information
    company_name = models.CharField(max_length=200, blank=True, help_text="Parent company name (e.g., NOORI KAKI CO.)")
    country = models.CharField(max_length=100, blank=True, help_text="Parent company country")
    email = models.EmailField(blank=True, help_text="Parent company email")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SAAS Product Configuration'
        verbose_name_plural = 'SAAS Product Configuration'

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion - just reset fields
        self.product_name = 'Nahd Travels CRM'
        self.logo = None
        self.address = ''
        self.phone = ''
        self.company_name = ''
        self.country = ''
        self.email = ''
        self.save()

    @classmethod
    def load(cls):
        """Get or create the singleton instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"SAAS Product Configuration: {self.product_name}"


class SystemConfiguration(models.Model):
    """System-wide configuration settings"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}: {self.value}"

    class Meta:
        ordering = ['key']


class AgencyBranding(models.Model):
    """Agency-specific branding and configuration"""
    agency = models.OneToOneField(Agency, on_delete=models.CASCADE, related_name='branding')
    logo = models.ImageField(upload_to='agency_branding/', null=True, blank=True)
    favicon = models.ImageField(upload_to='agency_branding/', null=True, blank=True)
    primary_color = models.CharField(max_length=7, default='#2bb7ff')  # Hex color
    secondary_color = models.CharField(max_length=7, default='#4ea8ff')  # Hex color
    company_name = models.CharField(max_length=200, blank=True)
    tagline = models.CharField(max_length=300, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    # Right-side block on printed vouchers (Shirka / parent company line)
    shirka_company_name = models.CharField(max_length=200, blank=True)
    shirka_company_country = models.CharField(max_length=100, blank=True)
    shirka_company_whatsapp = models.CharField(max_length=50, blank=True)
    shirka_company_address = models.TextField(blank=True)
    shirka_company_phone = models.CharField(max_length=50, blank=True)
    shirka_company_email = models.EmailField(blank=True)
    shirka_company_website = models.URLField(blank=True)
    social_facebook = models.URLField(blank=True)
    social_twitter = models.URLField(blank=True)
    social_instagram = models.URLField(blank=True)
    social_linkedin = models.URLField(blank=True)
    social_media_links = models.JSONField(default=dict, blank=True)
    custom_css = models.TextField(blank=True)

    # Email templates
    booking_confirmation_template = models.TextField(blank=True)
    payment_receipt_template = models.TextField(blank=True)
    voucher_template = models.TextField(blank=True)

    # Custom fields
    custom_fields = models.JSONField(default=dict, blank=True)

    @property
    def logo_is_wordmark(self):
        """True when the logo is wide enough to be a name-and-icon wordmark (so the top bar shows it alone);
        a square / icon-style logo is shown with the company name beside it."""
        if not self.logo:
            return False
        from django.core.files.images import get_image_dimensions
        try:
            w, h = get_image_dimensions(self.logo)
        except Exception:
            return False
        return bool(w and h and w / h >= 2.0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"Branding for {self.agency.name}"

    class Meta:
        ordering = ['agency__name']
        base_manager_name = 'all_tenants'


class EmailTemplate(models.Model):
    """Email templates for different purposes"""
    TEMPLATE_TYPES = [
        ('booking_confirmation', _('Booking Confirmation')),
        ('payment_receipt', _('Payment Receipt')),
        ('voucher_generated', _('Voucher Generated')),
        ('booking_cancelled', _('Booking Cancelled')),
        ('welcome_email', _('Welcome Email')),
        ('password_reset', _('Password Reset')),
        ('custom', _('Custom')),
    ]

    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=200)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    variables = models.JSONField(default=list, blank=True)  # Available template variables

    # Agency-specific or global
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, null=True, blank=True, related_name='email_templates')

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantOrGlobalManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"{self.name} ({self.template_type})"

    class Meta:
        ordering = ['template_type', 'name']
        unique_together = ['template_type', 'agency']
        base_manager_name = 'all_tenants'


class NotificationSettings(models.Model):
    """Notification settings for agencies"""
    agency = models.OneToOneField(Agency, on_delete=models.CASCADE, related_name='notification_settings')

    # Email notifications
    email_booking_confirmation = models.BooleanField(default=True)
    email_payment_received = models.BooleanField(default=True)
    email_voucher_generated = models.BooleanField(default=True)
    email_booking_cancelled = models.BooleanField(default=True)
    email_daily_summary = models.BooleanField(default=False)
    email_weekly_report = models.BooleanField(default=True)

    # SMS notifications
    sms_booking_confirmation = models.BooleanField(default=False)
    sms_payment_received = models.BooleanField(default=False)
    sms_voucher_generated = models.BooleanField(default=False)

    # Admin notifications
    admin_new_booking = models.BooleanField(default=True)
    admin_payment_received = models.BooleanField(default=True)
    admin_cancellation = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"Notifications for {self.agency.name}"

    class Meta:
        ordering = ['agency__name']
        base_manager_name = 'all_tenants'


class APIKey(models.Model):
    """API keys for external integrations"""
    KEY_TYPES = [
        ('attendance_device', _('Attendance Device')),
        ('payment_gateway', _('Payment Gateway')),
        ('sms_provider', _('SMS Provider')),
        ('email_provider', _('Email Provider')),
        ('map_service', _('Map Service')),
        ('other', _('Other')),
    ]

    name = models.CharField(max_length=100)
    key_type = models.CharField(max_length=50, choices=KEY_TYPES)
    api_key = models.CharField(max_length=500)
    api_secret = models.CharField(max_length=500, blank=True)
    endpoint_url = models.URLField(blank=True)
    description = models.TextField(blank=True)

    # Agency-specific or global
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, null=True, blank=True, related_name='api_keys')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantOrGlobalManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"{self.name} ({self.key_type})"

    class Meta:
        ordering = ['key_type', 'name']
        base_manager_name = 'all_tenants'


class AuditLog(models.Model):
    """Audit log for system configuration changes"""
    ACTION_TYPES = [
        ('create', _('Create')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('activate', _('Activate')),
        ('deactivate', _('Deactivate')),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    # NULL = platform-level entry (e.g. an Agency record itself, or global
    # config) — visible only to Super Admin, never to a tenant. Deliberately
    # NOT a TenantOrGlobalManager like EmailTemplate/APIKey: those use NULL
    # to mean "shared with everyone", here it means the opposite.
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=200)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"{self.user} {self.action} {self.model_name} {self.object_id}"

    class Meta:
        ordering = ['-timestamp']
        base_manager_name = 'all_tenants'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'timestamp']),
            models.Index(fields=['agency', 'timestamp']),
        ]
