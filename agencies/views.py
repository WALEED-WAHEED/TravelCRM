import logging

from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from utils.api import TenantScopedAPIMixin

from .models import Agency
from .serializers import AgencyCreateSerializer, AgencySerializer, AgencyStatisticsSerializer

logger = logging.getLogger(__name__)


class IsSuperAdminOrReadOnly(permissions.BasePermission):
    """
    Creating, renaming, or deleting a tenant is a platform decision, not
    a tenant one — Super Admin only (see platform_admin for the actual
    onboarding flow; this API is kept for programmatic/admin use).
    Any authenticated member/agent may still read their own agency's
    record (scoped by get_queryset below).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser


class AgencyViewSet(TenantScopedAPIMixin, viewsets.ModelViewSet):
    """
    Agencies API:
      - Super Admin -> full CRUD across every tenant
      - Members/Agents -> read-only, only their own agency
    """
    serializer_class = AgencySerializer
    permission_classes = [IsSuperAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "country", "city"]
    search_fields = ["name", "code", "email", "phone", "city", "country"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Agency.objects.all()
        if user.role in ['member', 'agent']:
            return Agency.objects.filter(id=user.agency_id) if user.agency else Agency.objects.none()
        return Agency.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return AgencyCreateSerializer
        return AgencySerializer

    def destroy(self, request, *args, **kwargs):
        """Handle agency deletion with proper error handling"""
        try:
            agency = self.get_object()

            # Check for related objects that might prevent deletion
            related_counts = {}
            if agency.users.exists():
                related_counts['users'] = agency.users.count()
            if hasattr(agency, 'bookings') and agency.bookings.exists():
                related_counts['bookings'] = agency.bookings.count()
            if hasattr(agency, 'hotels') and agency.hotels.exists():
                related_counts['hotels'] = agency.hotels.count()
            if hasattr(agency, 'flights') and agency.flights.exists():
                related_counts['flights'] = agency.flights.count()
            if hasattr(agency, 'transports') and agency.transports.exists():
                related_counts['transports'] = agency.transports.count()
            if hasattr(agency, 'contacts') and agency.contacts.exists():
                related_counts['contacts'] = agency.contacts.count()
            if hasattr(agency, 'ledger_entries') and agency.ledger_entries.exists():
                related_counts['ledger_entries'] = agency.ledger_entries.count()

            if related_counts:
                return Response(
                    {
                        "detail": "Cannot delete agency with associated data. Please delete related records first.",
                        "related_counts": related_counts
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Try hard delete first
            try:
                self.perform_destroy(agency)
                return Response(
                    {"detail": "Agency deleted successfully"},
                    status=status.HTTP_204_NO_CONTENT
                )
            except Exception as delete_error:
                # If hard delete fails, try soft delete (mark as inactive)
                logger.warning("Hard delete failed for agency %s: %s", agency.pk, delete_error)
                agency.is_active = False
                agency.save()
                return Response(
                    {"detail": "Agency deactivated successfully (soft delete)"},
                    status=status.HTTP_200_OK
                )

        except Exception as e:
            logger.exception("Agency deletion error")
            return Response(
                {"detail": f"Error deleting agency: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get statistics for an agency"""
        agency = self.get_object()

        # Calculate statistics. Booking has no `payment_status` field (only
        # `status`: draft/confirmed/cancelled/completed) and there is no
        # Package model yet, so revenue is summed over confirmed+completed
        # bookings and an "active packages" stat is not reported.
        total_bookings = agency.bookings.count()
        total_revenue = agency.bookings.filter(
            status__in=['confirmed', 'completed']
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        stats = {
            'total_bookings': total_bookings,
            'total_revenue': total_revenue,
            'member_count': agency.member_count,
            'agent_count': agency.agent_count,
        }

        serializer = AgencyStatisticsSerializer(stats)
        return Response(serializer.data)
