from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    SystemConfigurationViewSet, AgencyBrandingViewSet, EmailTemplateViewSet,
    NotificationSettingsViewSet, APIKeyViewSet, AuditLogViewSet,
    SystemConfigDashboardViewSet, system_settings, saas_product_config, saas_product_config_public, upload_saas_logo
)

router = DefaultRouter()
router.register("configurations", SystemConfigurationViewSet, basename="system-configurations")
router.register("agency-branding", AgencyBrandingViewSet, basename="agency-branding")
router.register("email-templates", EmailTemplateViewSet, basename="email-templates")
router.register("notification-settings", NotificationSettingsViewSet, basename="notification-settings")
router.register("api-keys", APIKeyViewSet, basename="api-keys")
router.register("audit-logs", AuditLogViewSet, basename="audit-logs")
router.register("dashboard", SystemConfigDashboardViewSet, basename="system-config-dashboard")

urlpatterns = [
    path('', system_settings, name='system-settings'),  # For /api/v1/settings/
    path('settings/', system_settings, name='system-settings-alt'),  # For /api/v1/system-config/settings/
    path('saas-product-config/', saas_product_config, name='saas-product-config'),
    path('saas-product-config/upload-logo/', upload_saas_logo, name='upload-saas-logo'),
    path('saas-product-config-public/', saas_product_config_public, name='saas-product-config-public'),
] + router.urls
