"""
URL configuration for travelcrm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
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
from .health import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check endpoint (no auth required)
    path('health/', health_check, name='health-check'),

    # JWT Auth
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/user/", current_user, name="current-user"),  # Current user profile
    
    # Apps
    path("api/v1/accounts/", include("accounts.urls")),  # User management and accounts
    path("api/v1/settings/", include("system_config.urls")),  # System settings
    path("api/v1/system-config/", include("system_config.urls")),  # System configuration
    path("api/v1/agencies/", include("agencies.urls")),
    path("api/v1/hotels/", include("hotels.urls")),
    path("api/v1/flights/", include("flights.urls")),
    path("api/v1/transports/", include("transports.urls")),
    path("api/v1/mutamers/", include("mutamers.urls")),
    path("api/v1/bookings/", include("bookings.urls")),
    path("api/v1/vouchers/", include("vouchers.urls")),
    path("api/v1/ledger/", include("ledger.urls")),
    path("api/v1/attendance/", include("attendance.urls")),
    path("api/v1/contacts/", include("contacts.urls")),
    path("api/v1/dashboard/", include("dashboard.urls")),
    
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
