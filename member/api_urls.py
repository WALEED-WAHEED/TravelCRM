from rest_framework.routers import DefaultRouter

from .api_views import HotelViewSet

router = DefaultRouter()
router.register(r"", HotelViewSet, basename="hotel")

urlpatterns = router.urls
