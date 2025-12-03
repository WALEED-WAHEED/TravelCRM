from django.contrib import admin
from .models import (
    SystemConfiguration, AgencyBranding, EmailTemplate,
    NotificationSettings, APIKey, AuditLog
)


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'is_active', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['key', 'description']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('key', 'value', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AgencyBranding)
class AgencyBrandingAdmin(admin.ModelAdmin):
    list_display = ['agency', 'company_name', 'primary_color', 'is_active', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['agency__name', 'company_name', 'tagline']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Agency', {
            'fields': ('agency',)
        }),
        ('Branding', {
            'fields': ('logo', 'favicon', 'primary_color', 'secondary_color')
        }),
        ('Company Information', {
            'fields': ('company_name', 'tagline', 'address', 'phone', 'email', 'website')
        }),
        ('Social Media', {
            'fields': ('social_facebook', 'social_twitter', 'social_instagram', 'social_linkedin')
        }),
        ('Email Templates', {
            'fields': ('booking_confirmation_template', 'payment_receipt_template', 'voucher_template'),
            'classes': ('collapse',)
        }),
        ('Custom Fields', {
            'fields': ('custom_fields',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'agency', 'is_active', 'is_default', 'updated_at']
    list_filter = ['template_type', 'is_active', 'is_default', 'created_at', 'updated_at']
    search_fields = ['name', 'subject', 'agency__name']
    list_editable = ['is_active', 'is_default']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'template_type', 'agency')
        }),
        ('Content', {
            'fields': ('subject', 'html_content', 'text_content')
        }),
        ('Variables', {
            'fields': ('variables',),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_active', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['agency', 'email_booking_confirmation', 'sms_booking_confirmation', 'updated_at']
    list_filter = ['email_booking_confirmation', 'sms_booking_confirmation', 'created_at', 'updated_at']
    search_fields = ['agency__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Agency', {
            'fields': ('agency',)
        }),
        ('Email Notifications', {
            'fields': (
                'email_booking_confirmation', 'email_payment_received',
                'email_voucher_generated', 'email_booking_cancelled',
                'email_daily_summary', 'email_weekly_report'
            )
        }),
        ('SMS Notifications', {
            'fields': (
                'sms_booking_confirmation', 'sms_payment_received',
                'sms_voucher_generated'
            )
        }),
        ('Admin Notifications', {
            'fields': (
                'admin_new_booking', 'admin_payment_received',
                'admin_cancellation'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'key_type', 'agency', 'is_active', 'updated_at']
    list_filter = ['key_type', 'is_active', 'created_at', 'updated_at']
    search_fields = ['name', 'description', 'agency__name']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('API Key Information', {
            'fields': ('name', 'key_type', 'agency', 'description')
        }),
        ('Credentials', {
            'fields': ('api_key', 'api_secret', 'endpoint_url')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('agency')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'object_repr', 'timestamp']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__username', 'object_repr', 'model_name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Action Details', {
            'fields': ('user', 'action', 'model_name', 'object_id', 'object_repr')
        }),
        ('Changes', {
            'fields': ('changes',),
            'classes': ('collapse',)
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False