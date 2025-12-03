from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta
from .models import Voucher, VoucherService
from .serializers import (
    VoucherSerializer, VoucherCreateSerializer, VoucherUpdateSerializer,
    VoucherServiceSerializer, VoucherStatsSerializer
)
from utils.permissions import IsDeveloper, IsMember, IsAgent


class IsDeveloperOrAgency(permissions.BasePermission):
    """Developer has full access, Members full for their agency, Agents only their own"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.role == "developer":
            return True
        if request.user.role == "member":
            # Members can access all vouchers in their agency
            return obj.agent.agency == request.user.agency
        if request.user.role == "agent":
            return obj.agent == request.user
        return False

    def has_permission(self, request, view):
        return request.user.is_authenticated


class VoucherViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vouchers"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'agent']
    search_fields = ['voucher_number', 'mutamer__name', 'agent__first_name', 'agent__last_name']
    ordering_fields = ['created_at', 'total_amount', 'approved_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create']:
            return VoucherCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return VoucherUpdateSerializer
        return VoucherSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Voucher.objects.select_related('mutamer', 'agent', 'approved_by').prefetch_related('services')
        
        if user.role == "developer":
            return queryset
        elif user.role == "member":
            return queryset.filter(agent__agency=user.agency)
        elif user.role == "agent":
            return queryset.filter(agent=user)
        else:
            return Voucher.objects.none()

    def perform_create(self, serializer):
        """Create voucher with proper agent context"""
        if self.request.user.role not in ['developer', 'member', 'agent']:
            raise permissions.PermissionDenied("Only authenticated users can create vouchers.")
        
        serializer.save(agent=self.request.user)

    def perform_update(self, serializer):
        """Update voucher with permission checks"""
        if self.request.user.role not in ['developer', 'member', 'agent']:
            raise permissions.PermissionDenied("Only authenticated users can update vouchers.")
        
        serializer.save()

    def perform_destroy(self, instance):
        """Cancel voucher instead of deleting"""
        if self.request.user.role not in ['developer', 'member', 'agent']:
            raise permissions.PermissionDenied("Only authenticated users can cancel vouchers.")
        
        instance.status = 'cancelled'
        instance.save()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a voucher (Member/Developer only)"""
        if request.user.role not in ['developer', 'member']:
            return Response(
                {'error': 'Only developers and members can approve vouchers.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        voucher = self.get_object()
        
        if voucher.status == "approved":
            return Response(
                {"detail": "Voucher is already approved."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        voucher.status = "approved"
        voucher.approved_by = request.user
        voucher.approved_at = timezone.now()
        voucher.save()
        
        serializer = self.get_serializer(voucher)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a voucher (Member/Developer only)"""
        if request.user.role not in ['developer', 'member']:
            return Response(
                {'error': 'Only developers and members can reject vouchers.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        voucher = self.get_object()
        
        notes = request.data.get("notes", "")
        voucher.status = "rejected"
        if notes:
            voucher.notes = notes
        voucher.save()
        
        serializer = self.get_serializer(voucher)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a voucher"""
        voucher = self.get_object()
        voucher.status = "cancelled"
        voucher.save()
        
        serializer = self.get_serializer(voucher)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def get_services(self, request, pk=None):
        """Get all services for a voucher"""
        voucher = self.get_object()
        services = voucher.services.all()
        serializer = VoucherServiceSerializer(services, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get voucher statistics"""
        queryset = self.get_queryset()
        
        # Calculate statistics
        total_vouchers = queryset.count()
        pending_vouchers = queryset.filter(status='pending').count()
        approved_vouchers = queryset.filter(status='approved').count()
        rejected_vouchers = queryset.filter(status='rejected').count()
        
        # Calculate amounts
        amount_data = queryset.aggregate(
            total_amount=Sum('total_amount'),
            paid_amount=Sum('paid_amount')
        )
        total_amount = amount_data['total_amount'] or 0
        paid_amount = amount_data['paid_amount'] or 0
        pending_amount = total_amount - paid_amount
        
        # Recent vouchers (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_vouchers = queryset.filter(created_at__gte=thirty_days_ago).count()
        
        stats_data = {
            'total_vouchers': total_vouchers,
            'pending_vouchers': pending_vouchers,
            'approved_vouchers': approved_vouchers,
            'rejected_vouchers': rejected_vouchers,
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'pending_amount': pending_amount,
            'recent_vouchers': recent_vouchers
        }
        
        serializer = VoucherStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get pending vouchers"""
        queryset = self.get_queryset().filter(status='pending').order_by('-created_at')
        serializer = VoucherSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def approved(self, request):
        """Get approved vouchers"""
        queryset = self.get_queryset().filter(status='approved').order_by('-approved_at')
        serializer = VoucherSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_status(self, request):
        """Get vouchers grouped by status"""
        queryset = self.get_queryset()
        
        status_groups = {}
        for voucher in queryset:
            if voucher.status not in status_groups:
                status_groups[voucher.status] = {
                    'status': voucher.status,
                    'count': 0,
                    'vouchers': []
                }
            
            status_groups[voucher.status]['count'] += 1
            status_groups[voucher.status]['vouchers'].append({
                'id': voucher.id,
                'voucher_number': voucher.voucher_number,
                'mutamer_name': voucher.mutamer.name,
                'total_amount': float(voucher.total_amount),
                'created_at': voucher.created_at
            })
        
        return Response(list(status_groups.values()))


# Public view (no auth) to view voucher via public token
from rest_framework.views import APIView


class PublicVoucherView(APIView):
    """Public endpoint to view voucher (no authentication required)"""
    permission_classes = []

    def get(self, request, token):
        voucher = get_object_or_404(Voucher, public_token=token)
        serializer = VoucherSerializer(voucher)
        return Response(serializer.data)
