from rest_framework.routers import DefaultRouter

from .api_views import TransportViewSet

router = DefaultRouter()
router.register(r"", TransportViewSet, basename="transport")

urlpatterns = router.urls
