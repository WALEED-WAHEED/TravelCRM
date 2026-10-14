from rest_framework import permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.api import TenantScopedAPIMixin
from utils.permissions import IsMember

from .models import LedgerEntry
from .serializers import LedgerEntrySerializer


class LedgerEntryViewSet(TenantScopedAPIMixin, viewsets.ModelViewSet):
    """Agency ledger entries — members can create/update/delete."""

    serializer_class = LedgerEntrySerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        # Ledger is a finance feature; members only for write operations.
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsMember()]
        return [IsMember()]

    def get_queryset(self):
        user = self.request.user
        aid = getattr(user, "agency_id", None)
        if not aid:
            return LedgerEntry.objects.none()
        return LedgerEntry.objects.filter(agency_id=aid).order_by("-transaction_date", "-created_at")

    def create(self, request, *args, **kwargs):
        if not request.user.agency_id:
            return Response(
                {"detail": "User is not associated with an agency."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            agency_id=self.request.user.agency_id,
            created_by=self.request.user,
        )

