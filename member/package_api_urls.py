from rest_framework.routers import DefaultRouter

from .api_views import PackageViewSet

router = DefaultRouter()
router.register(r"", PackageViewSet, basename="package")

urlpatterns = router.urls
