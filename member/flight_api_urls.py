from rest_framework.routers import DefaultRouter

from .api_views import FlightViewSet

router = DefaultRouter()
router.register(r"", FlightViewSet, basename="flight")

urlpatterns = router.urls
