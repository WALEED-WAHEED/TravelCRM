from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CustomTokenObtainPairView, 
    request_password_reset, reset_password, MemberProfileView, upload_logo, generate_voucher_number
)

router = DefaultRouter()
router.register("", UserViewSet, basename="users")

urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("password-reset/", request_password_reset, name="request_password_reset"),
    path("password-reset-confirm/", reset_password, name="reset_password"),
    path("profile/", MemberProfileView.as_view(), name="member_profile"),
    path("profile/upload-logo/", upload_logo, name="upload_logo"),
    path("voucher-number/", generate_voucher_number, name="generate_voucher_number"),
    path("", include(router.urls)),
]
