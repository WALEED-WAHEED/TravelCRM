from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.api import TenantScopedAPIMixin
from utils.permissions import IsMember, IsMemberOrAgent

from .models import Voucher
from .serializers import VoucherSerializer


class VoucherViewSet(TenantScopedAPIMixin, viewsets.ModelViewSet):
    """
    Agency vouchers.
    - list/retrieve: member or agent (same agency)
    - approve/reject: members only
    """

    serializer_class = VoucherSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsMemberOrAgent()]
        if self.action in ("approve", "reject"):
            return [IsMember()]
        return [IsMemberOrAgent()]

    def get_queryset(self):
        user = self.request.user
        aid = getattr(user, "agency_id", None)
        if not aid:
            return Voucher.objects.none()
        # vouchers belong to agency through agent
        return Voucher.objects.filter(agent__agency_id=aid).select_related("agent").prefetch_related("services")

    def perform_create(self, serializer):
        serializer.save(agency_id=self.request.user.agency_id)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        v = self.get_object()
        if v.status != "pending":
            return Response({"detail": "Only pending vouchers can be approved."}, status=status.HTTP_400_BAD_REQUEST)
        v.status = "approved"
        v.rejection_reason = ""
        v.approved_by = request.user
        v.approved_at = timezone.now()
        v.save(update_fields=["status", "rejection_reason", "approved_by", "approved_at", "updated_at"])
        return Response({"detail": "Approved."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        v = self.get_object()
        if v.status != "pending":
            return Response({"detail": "Only pending vouchers can be rejected."}, status=status.HTTP_400_BAD_REQUEST)
        reason = str(request.data.get("reason") or "").strip()
        if not reason:
            return Response({"detail": "Please give a reason so the agent knows what to fix."},
                            status=status.HTTP_400_BAD_REQUEST)
        v.status = "rejected"
        v.rejection_reason = reason[:2000]
        v.approved_by = request.user
        v.approved_at = timezone.now()
        v.save(update_fields=["status", "rejection_reason", "approved_by", "approved_at", "updated_at"])
        return Response({"detail": "Rejected."}, status=status.HTTP_200_OK)

