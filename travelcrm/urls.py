from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from accounts.views import current_user
from member.views import root_redirect
from .health import health_check

urlpatterns = [
    # Root redirect (automatically handles unauthenticated -> /login/ and routes roles dynamically)
    path('', root_redirect, name='root'),

    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),

    # === TEMPLATE-SERVING VIEWS (Django + HTMX) ===
    path('', include('member.urls')),
    path('', include('agent.urls')),

    # === REST API (JWT — for external/API use) ===
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/user/", current_user, name="current-user"),
    path("api/v1/accounts/", include("accounts.urls")),
    path("api/v1/settings/", include("system_config.urls")),
    path("api/v1/system-config/", include("system_config.urls")),
    path("api/v1/agencies/", include("agencies.urls")),
    path("api/v1/hotels/", include("member.api_urls")),
    path("api/v1/flights/", include("member.flight_api_urls")),
    path("api/v1/transports/", include("member.transport_api_urls")),
    path("api/v1/mutamers/", include("member.mutamer_api_urls")),
    path("api/v1/vouchers/", include("member.voucher_api_urls")),
    path("api/v1/ledger/", include("member.ledger_api_urls")),

    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
