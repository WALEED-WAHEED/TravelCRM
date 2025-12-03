from rest_framework.routers import DefaultRouter
from .views import MutamerViewSet

router = DefaultRouter()
router.register("mutamers", MutamerViewSet, basename="mutamers")

urlpatterns = router.urls
