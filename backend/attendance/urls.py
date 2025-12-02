from rest_framework.routers import DefaultRouter
from .views import AttendanceLogViewSet

router = DefaultRouter()
router.register("attendance", AttendanceLogViewSet, basename="attendance")

urlpatterns = router.urls
