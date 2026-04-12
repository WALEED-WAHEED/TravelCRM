from rest_framework.routers import DefaultRouter

from .api_views import MutamerViewSet

router = DefaultRouter()
router.register(r"", MutamerViewSet, basename="mutamer")

urlpatterns = router.urls
