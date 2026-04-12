from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q
from utils.permissions import IsMember, IsAgent
from .models import Agency
from .serializers import AgencySerializer, AgencyCreateSerializer, AgencyStatisticsSerializer


class IsMemberOrReadOnly(permissions.BasePermission):
    """Members: full CRUD on own agency, Agents: read-only"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == 'member'


class AgencyViewSet(viewsets.ModelViewSet):
    """
    Agencies API:
      - Members → full CRUD on their own agency
      - Agents → read-only, only their own agency
    """
    serializer_class = AgencySerializer
    permission_classes = [IsMemberOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "country", "city"]
    search_fields = ["name", "code", "email", "phone", "city", "country"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
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
            if hasattr(agency, 'packages') and agency.packages.exists():
                related_counts['packages'] = agency.packages.count()
            if hasattr(agency, 'hotels') and agency.hotels.exists():
                related_counts['hotels'] = agency.hotels.count()
            if hasattr(agency, 'flights') and agency.flights.exists():
                related_counts['flights'] = agency.flights.count()
            if hasattr(agency, 'transports') and agency.transports.exists():
                related_counts['transports'] = agency.transports.count()
            if hasattr(agency, 'mutamers') and agency.mutamers.exists():
                related_counts['mutamers'] = agency.mutamers.count()
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
                print(f"Hard delete failed: {delete_error}")
                agency.is_active = False
                agency.save()
                return Response(
                    {"detail": "Agency deactivated successfully (soft delete)"},
                    status=status.HTTP_200_OK
                )
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Agency deletion error: {error_details}")  # Log for debugging
            return Response(
                {"detail": f"Error deleting agency: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get statistics for an agency"""
        agency = self.get_object()
        
        # Calculate statistics
        total_bookings = agency.bookings.count()
        total_revenue = agency.bookings.filter(
            payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        active_packages = agency.packages.filter(status='active').count()
        total_mutamers = agency.mutamers.count()
        
        stats = {
            'total_bookings': total_bookings,
            'total_revenue': total_revenue,
            'active_packages': active_packages,
            'total_mutamers': total_mutamers,
            'member_count': agency.member_count,
            'agent_count': agency.agent_count,
        }
        
        serializer = AgencyStatisticsSerializer(stats)
        return Response(serializer.data)
