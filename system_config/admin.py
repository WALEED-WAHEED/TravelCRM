from django.contrib import admin
from .models import SAASProductConfig, AgencyBranding, EmailTemplate, NotificationSettings, APIKey, AuditLog

@admin.register(SAASProductConfig)
class SAASProductConfigAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'slogan', 'company_name', 'phone']
    search_fields = ('product_name', 'email', 'company_name')
    fields = ['product_name', 'slogan', 'logo', 'favicon', 'address', 'phone', 'email', 'company_name']

@admin.register(AgencyBranding)
class AgencyBrandingAdmin(admin.ModelAdmin):
    list_display = ('agency', 'primary_color', 'secondary_color', 'is_active')
    search_fields = ('agency__name',)
    list_filter = ('is_active',)

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'subject', 'is_active', 'is_default', 'created_at')
    search_fields = ('name', 'subject')
    list_filter = ('template_type', 'is_active', 'is_default')

@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('agency', 'email_booking_confirmation', 'sms_booking_confirmation', 'admin_new_booking')
    search_fields = ('agency__name',)
    list_filter = ('email_booking_confirmation', 'sms_booking_confirmation')

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'agency', 'key_type', 'is_active', 'created_at')
    search_fields = ('name', 'agency__name')
    list_filter = ('is_active', 'key_type')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'model_name', 'object_repr', 'ip_address', 'timestamp')
    search_fields = ('action', 'user__username', 'model_name', 'ip_address')
    list_filter = ('action', 'timestamp')
    readonly_fields = ('timestamp',)
