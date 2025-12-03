from rest_framework.routers import DefaultRouter
from .views import AgencyViewSet

router = DefaultRouter()
router.register(r"", AgencyViewSet, basename="agency")

urlpatterns = router.urls
