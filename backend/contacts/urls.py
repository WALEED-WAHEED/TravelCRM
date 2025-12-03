from rest_framework.routers import DefaultRouter
from .views import ContactInstructionViewSet

router = DefaultRouter()
router.register("contacts", ContactInstructionViewSet, basename="contacts")

urlpatterns = router.urls
