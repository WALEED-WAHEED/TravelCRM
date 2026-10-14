from django.urls import path

from . import views

app_name = 'platform_admin'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('tenants/create/', views.tenant_create, name='tenant-create'),
    path('tenants/<int:agency_id>/', views.tenant_detail, name='tenant-detail'),
    path('tenants/<int:agency_id>/suspend/', views.tenant_suspend, name='tenant-suspend'),
    path('tenants/<int:agency_id>/activate/', views.tenant_activate, name='tenant-activate'),
    path('tenants/<int:agency_id>/assign-plan/', views.tenant_assign_plan, name='tenant-assign-plan'),
    path('tenants/<int:agency_id>/branding/', views.tenant_branding_update, name='tenant-branding-update'),
    path('impersonate/<int:user_id>/start/', views.impersonate_start, name='impersonate-start'),
    path('impersonate/stop/', views.impersonate_stop, name='impersonate-stop'),
    path('impersonations/', views.impersonation_sessions, name='impersonations'),
    path('audit-log/', views.audit_log, name='audit-log'),
    path('plans/', views.plans_list, name='plans'),
    path('plans/new/', views.plan_form, name='plan-create'),
    path('plans/<int:plan_id>/edit/', views.plan_form, name='plan-edit'),
    path('payments/pending/', views.pending_payments, name='pending-payments'),
    path('payments/<int:payment_id>/confirm/', views.confirm_payment, name='confirm-payment'),
    path('payments/<int:payment_id>/reject/', views.reject_payment, name='reject-payment'),

    path('staff/', views.staff_list, name='staff'),
    path('staff/new/', views.staff_form, name='staff-create'),
    path('staff/<int:staff_id>/edit/', views.staff_form, name='staff-edit'),
    path('staff/<int:staff_id>/revoke/', views.staff_revoke, name='staff-revoke'),

    path('announcements/', views.announcements_list, name='announcements'),
    path('announcements/new/', views.announcement_form, name='announcement-create'),
    path('announcements/<int:announcement_id>/edit/', views.announcement_form, name='announcement-edit'),
    path('announcements/<int:announcement_id>/deactivate/', views.announcement_deactivate, name='announcement-deactivate'),

    path('system-config/', views.system_config_list, name='system-config'),
    path('system-config/new/', views.system_config_form, name='system-config-create'),
    path('system-config/<int:config_id>/edit/', views.system_config_form, name='system-config-edit'),
    path('system-config/<int:config_id>/delete/', views.system_config_delete, name='system-config-delete'),

    path('email-templates/', views.email_templates_list, name='email-templates'),
    path('email-templates/new/', views.email_template_form, name='email-template-create'),
    path('email-templates/<int:template_id>/edit/', views.email_template_form, name='email-template-edit'),

    path('api-keys/', views.api_keys_list, name='api-keys'),
    path('api-keys/new/', views.api_key_form, name='api-key-create'),
    path('api-keys/<int:key_id>/edit/', views.api_key_form, name='api-key-edit'),

    path('notification-settings/', views.notification_settings_report, name='notification-settings'),
    path('system-health/', views.system_health, name='system-health'),
]
