from rest_framework.routers import DefaultRouter
from .views import TransportViewSet

router = DefaultRouter()
router.register("transports", TransportViewSet, basename="transports")

urlpatterns = router.urls
