from rest_framework import serializers
from .models import (
    SAASProductConfig, SystemConfiguration, AgencyBranding, EmailTemplate,
    NotificationSettings, APIKey, AuditLog
)
from agencies.serializers import AgencySerializer
from accounts.serializers import UserSerializer


class SAASProductConfigSerializer(serializers.ModelSerializer):
    """Serializer for SAAS Product Configuration"""
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = SAASProductConfig
        fields = [
            'id', 'product_name', 'logo', 'logo_url', 'address', 'phone',
            'company_name', 'country', 'email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'logo_url']
    
    def get_logo_url(self, obj):
        """Get logo URL if logo exists"""
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class SystemConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for system configuration"""
    
    class Meta:
        model = SystemConfiguration
        fields = [
            'id', 'key', 'value', 'description', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_key(self, value):
        """Ensure key is unique"""
        instance = self.instance
        if SystemConfiguration.objects.filter(key=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError("Configuration key must be unique.")
        return value


class AgencyBrandingSerializer(serializers.ModelSerializer):
    """Serializer for agency branding"""
    agency = AgencySerializer(read_only=True)
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = AgencyBranding
        fields = [
            'id', 'agency', 'logo', 'logo_url', 'favicon', 'primary_color', 'secondary_color',
            'company_name', 'tagline', 'address', 'phone', 'email', 'website',
            'social_facebook', 'social_twitter', 'social_instagram', 'social_linkedin',
            'booking_confirmation_template', 'payment_receipt_template', 'voucher_template',
            'custom_fields', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_primary_color(self, value):
        """Validate hex color format"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Primary color must be a valid hex color (e.g., #2bb7ff).")
        return value
    
    def validate_secondary_color(self, value):
        """Validate hex color format"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Secondary color must be a valid hex color (e.g., #4ea8ff).")
        return value
    
    def get_logo_url(self, obj):
        """Get logo URL if logo exists"""
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class AgencyBrandingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating agency branding"""
    
    class Meta:
        model = AgencyBranding
        fields = [
            'agency', 'logo', 'favicon', 'primary_color', 'secondary_color',
            'company_name', 'tagline', 'address', 'phone', 'email', 'website',
            'social_facebook', 'social_twitter', 'social_instagram', 'social_linkedin',
            'booking_confirmation_template', 'payment_receipt_template', 'voucher_template',
            'custom_fields', 'is_active'
        ]
    
    def validate_primary_color(self, value):
        """Validate hex color format"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Primary color must be a valid hex color (e.g., #2bb7ff).")
        return value
    
    def validate_secondary_color(self, value):
        """Validate hex color format"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Secondary color must be a valid hex color (e.g., #4ea8ff).")
        return value


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Serializer for email templates"""
    agency = AgencySerializer(read_only=True)
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'template_type', 'subject', 'html_content',
            'text_content', 'variables', 'agency', 'is_active', 'is_default',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        """Validate template data"""
        if data['template_type'] != 'custom' and not data.get('is_default'):
            # Check if default template already exists for this type and agency
            existing = EmailTemplate.objects.filter(
                template_type=data['template_type'],
                agency=data.get('agency'),
                is_default=True
            )
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            if existing.exists():
                raise serializers.ValidationError(
                    f"A default template already exists for {data['template_type']}."
                )
        return data


class EmailTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating email templates"""
    
    class Meta:
        model = EmailTemplate
        fields = [
            'name', 'template_type', 'subject', 'html_content',
            'text_content', 'variables', 'agency', 'is_active', 'is_default'
        ]
    
    def validate(self, data):
        """Validate template data"""
        if data['template_type'] != 'custom' and not data.get('is_default'):
            # Check if default template already exists for this type and agency
            existing = EmailTemplate.objects.filter(
                template_type=data['template_type'],
                agency=data.get('agency'),
                is_default=True
            )
            if existing.exists():
                raise serializers.ValidationError(
                    f"A default template already exists for {data['template_type']}."
                )
        return data


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """Serializer for notification settings"""
    agency = AgencySerializer(read_only=True)
    
    class Meta:
        model = NotificationSettings
        fields = [
            'id', 'agency', 'email_booking_confirmation', 'email_payment_received',
            'email_voucher_generated', 'email_booking_cancelled', 'email_daily_summary',
            'email_weekly_report', 'sms_booking_confirmation', 'sms_payment_received',
            'sms_voucher_generated', 'admin_new_booking', 'admin_payment_received',
            'admin_cancellation', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class NotificationSettingsCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notification settings"""
    
    class Meta:
        model = NotificationSettings
        fields = [
            'agency', 'email_booking_confirmation', 'email_payment_received',
            'email_voucher_generated', 'email_booking_cancelled', 'email_daily_summary',
            'email_weekly_report', 'sms_booking_confirmation', 'sms_payment_received',
            'sms_voucher_generated', 'admin_new_booking', 'admin_payment_received',
            'admin_cancellation'
        ]


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer for API keys"""
    agency = AgencySerializer(read_only=True)
    
    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'key_type', 'api_key', 'api_secret',
            'endpoint_url', 'description', 'agency', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True},
            'api_secret': {'write_only': True},
        }


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating API keys"""
    
    class Meta:
        model = APIKey
        fields = [
            'name', 'key_type', 'api_key', 'api_secret',
            'endpoint_url', 'description', 'agency', 'is_active'
        ]


class APIKeyListSerializer(serializers.ModelSerializer):
    """Serializer for API key list (without sensitive data)"""
    agency = AgencySerializer(read_only=True)
    api_key_masked = serializers.SerializerMethodField()
    
    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'key_type', 'api_key_masked',
            'endpoint_url', 'description', 'agency', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_api_key_masked(self, obj):
        """Return masked API key for security"""
        if obj.api_key:
            return f"{obj.api_key[:8]}...{obj.api_key[-4:]}"
        return None


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'action', 'model_name', 'object_id',
            'object_repr', 'changes', 'ip_address', 'user_agent',
            'timestamp'
        ]
        read_only_fields = ['timestamp']


class SystemConfigSummarySerializer(serializers.Serializer):
    """Serializer for system configuration summary"""
    total_configurations = serializers.IntegerField()
    total_agencies = serializers.IntegerField()
    agencies_with_branding = serializers.IntegerField()
    total_email_templates = serializers.IntegerField()
    total_api_keys = serializers.IntegerField()
    recent_changes = serializers.IntegerField()


class AgencyBrandingSummarySerializer(serializers.Serializer):
    """Serializer for agency branding summary"""
    agency_id = serializers.IntegerField()
    agency_name = serializers.CharField()
    has_logo = serializers.BooleanField()
    has_favicon = serializers.BooleanField()
    primary_color = serializers.CharField()
    secondary_color = serializers.CharField()
    company_name = serializers.CharField()
    is_active = serializers.BooleanField()
    last_updated = serializers.DateTimeField()
