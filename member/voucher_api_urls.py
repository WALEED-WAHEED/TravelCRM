from rest_framework.routers import DefaultRouter

from .voucher_api_views import VoucherViewSet

router = DefaultRouter()
router.register(r"", VoucherViewSet, basename="voucher")

urlpatterns = router.urls

