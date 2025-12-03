from rest_framework.routers import DefaultRouter
from .views import LedgerEntryViewSet

router = DefaultRouter()
router.register("ledger", LedgerEntryViewSet, basename="ledger")

urlpatterns = router.urls
