from rest_framework.routers import DefaultRouter
from .views import FlightViewSet

router = DefaultRouter()
router.register("flights", FlightViewSet, basename="flights")

urlpatterns = router.urls
