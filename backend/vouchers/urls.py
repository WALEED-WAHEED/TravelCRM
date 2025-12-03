from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import VoucherViewSet, PublicVoucherView

router = DefaultRouter()
router.register("vouchers", VoucherViewSet, basename="vouchers")

urlpatterns = router.urls + [
    path("public/voucher/<str:token>/", PublicVoucherView.as_view(), name="public_voucher"),
]
