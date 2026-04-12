from django.db import models
from django.conf import settings
from agencies.models import Agency

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
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Branding for {self.agency.name}"
    
    class Meta:
        ordering = ['agency__name']


class EmailTemplate(models.Model):
    """Email templates for different purposes"""
    TEMPLATE_TYPES = [
        ('booking_confirmation', 'Booking Confirmation'),
        ('payment_receipt', 'Payment Receipt'),
        ('voucher_generated', 'Voucher Generated'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('welcome_email', 'Welcome Email'),
        ('password_reset', 'Password Reset'),
        ('custom', 'Custom'),
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
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"
    
    class Meta:
        ordering = ['template_type', 'name']
        unique_together = ['template_type', 'agency']


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
    
    def __str__(self):
        return f"Notifications for {self.agency.name}"
    
    class Meta:
        ordering = ['agency__name']


class APIKey(models.Model):
    """API keys for external integrations"""
    KEY_TYPES = [
        ('attendance_device', 'Attendance Device'),
        ('payment_gateway', 'Payment Gateway'),
        ('sms_provider', 'SMS Provider'),
        ('email_provider', 'Email Provider'),
        ('map_service', 'Map Service'),
        ('other', 'Other'),
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
    
    def __str__(self):
        return f"{self.name} ({self.key_type})"
    
    class Meta:
        ordering = ['key_type', 'name']


class AuditLog(models.Model):
    """Audit log for system configuration changes"""
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('activate', 'Activate'),
        ('deactivate', 'Deactivate'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=200)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user} {self.action} {self.model_name} {self.object_id}"
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'timestamp']),
        ]