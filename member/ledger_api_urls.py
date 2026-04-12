from rest_framework.routers import DefaultRouter

from .ledger_api_views import LedgerEntryViewSet

router = DefaultRouter()
router.register(r"", LedgerEntryViewSet, basename="ledger")

urlpatterns = router.urls

