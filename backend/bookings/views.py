from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Booking, BookingHotel, BookingFlight, BookingTransport, 
    BookingMutamer, BookingContact, BookingTeamContact, BookingPayment
)
from .serializers import (
    BookingListSerializer, BookingDetailSerializer, BookingCreateSerializer,
    BookingUpdateSerializer, BookingPaymentSerializer,
    BookingPaymentCreateSerializer, BookingStatsSerializer, BookingSummarySerializer
)
from utils.permissions import IsDeveloper, IsMember, IsAgent


class IsDeveloperOrAgency(permissions.BasePermission):
    """Developer has full access, Members full for their agency, Agents only their own"""

    def has_object_permission(self, request, view, obj):
        if request.user.role == "developer":
            return True
        if request.user.role == "member":
            return obj.agency == request.user.agency
        if request.user.role == "agent":
            return obj.agent == request.user
        return False

    def has_permission(self, request, view):
        return request.user.is_authenticated


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bookings.
    
    - List: Returns bookings based on user role (developer sees all, member sees agency bookings, agent sees own bookings)
    - Create: Agents and members can create bookings
    - Retrieve: Get booking details with services and payments
    - Update: Update booking information
    - Destroy: Cancel bookings (soft delete)
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'agent', 'mutamer']
    search_fields = ['booking_number', 'mutamer__name', 'agent__first_name', 'agent__last_name']
    ordering_fields = ['created_at', 'travel_date', 'total_amount', 'booking_date']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        elif self.action in ['create']:
            return BookingCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BookingUpdateSerializer
        else:
            return BookingDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Booking.objects.select_related('mutamer', 'agent', 'agency', 'package').prefetch_related('services', 'payments')
        
        if user.role == 'developer':
            return queryset
        elif user.role == 'member':
            return queryset.filter(agency=user.agency)
        elif user.role == 'agent':
            return queryset.filter(agent=user)
        else:
            return Booking.objects.none()
    
    def perform_create(self, serializer):
        """Create booking with proper agency and agent context"""
        if self.request.user.role not in ['developer', 'member', 'agent']:
            raise permissions.PermissionDenied("Only authenticated users can create bookings.")
        
        serializer.save(
            agency=self.request.user.agency,
            agent=self.request.user
        )

    def perform_update(self, serializer):
        """Update booking with permission checks"""
        if self.request.user.role not in ['developer', 'member', 'agent']:
            raise permissions.PermissionDenied("Only authenticated users can update bookings.")
        
        serializer.save()

    def perform_destroy(self, instance):
        """Cancel booking instead of deleting"""
        if self.request.user.role not in ['developer', 'member', 'agent']:
            raise permissions.PermissionDenied("Only authenticated users can cancel bookings.")
        
        instance.status = 'cancelled'
        instance.save()
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a booking"""
        if request.user.role not in ['developer', 'member']:
            return Response(
                {'error': 'Only developers and members can confirm bookings.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        booking = self.get_object()
        booking.status = 'confirmed'
        booking.save()
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        booking.status = 'cancelled'
        booking.save()
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark booking as completed"""
        if request.user.role not in ['developer', 'member']:
            return Response(
                {'error': 'Only developers and members can complete bookings.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        booking = self.get_object()
        booking.status = 'completed'
        booking.save()
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        """Add a payment to booking"""
        booking = self.get_object()
        serializer = BookingPaymentCreateSerializer(
            data=request.data, 
            context={'request': request, 'booking_id': booking.id}
        )
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_service(self, request, pk=None):
        """Add a service to booking"""
        booking = self.get_object()
        serializer = BookingServiceCreateSerializer(
            data=request.data,
            context={'booking_id': booking.id}
        )
        serializer.is_valid(raise_exception=True)
        service = serializer.save()
        
        # Recalculate total amount
        total_services = booking.services.aggregate(total=Sum('total'))['total'] or 0
        booking.total_amount = total_services
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def get_services(self, request, pk=None):
        """Get all services for a booking"""
        booking = self.get_object()
        services = booking.services.all()
        serializer = BookingServiceSerializer(services, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def get_payments(self, request, pk=None):
        """Get all payments for a booking"""
        booking = self.get_object()
        payments = booking.payments.all()
        serializer = BookingPaymentSerializer(payments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get booking statistics"""
        queryset = self.get_queryset()
        
        # Calculate statistics
        total_bookings = queryset.count()
        confirmed_bookings = queryset.filter(status='confirmed').count()
        cancelled_bookings = queryset.filter(status='cancelled').count()
        completed_bookings = queryset.filter(status='completed').count()
        pending_payments = queryset.filter(payment_status='pending').count()
        
        # Calculate total revenue
        revenue_data = queryset.filter(status__in=['confirmed', 'completed']).aggregate(
            total_revenue=Sum('total_amount')
        )
        total_revenue = revenue_data['total_revenue'] or 0
        
        # Recent bookings (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_bookings = queryset.filter(created_at__gte=thirty_days_ago).count()
        
        # Get currency from first booking or default
        first_booking = queryset.first()
        currency = first_booking.currency if first_booking else 'USD'
        
        stats_data = {
            'total_bookings': total_bookings,
            'confirmed_bookings': confirmed_bookings,
            'cancelled_bookings': cancelled_bookings,
            'completed_bookings': completed_bookings,
            'pending_payments': pending_payments,
            'total_revenue': total_revenue,
            'currency': currency,
            'recent_bookings': recent_bookings
        }
        
        serializer = BookingStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming bookings"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(
            travel_date__gte=today,
            status__in=['draft', 'confirmed']
        ).order_by('travel_date')
        
        serializer = BookingListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get bookings for today"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(travel_date=today)
        
        serializer = BookingListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_payments(self, request):
        """Get bookings with pending payments"""
        queryset = self.get_queryset().filter(
            payment_status__in=['pending', 'partial']
        ).order_by('-created_at')
        
        serializer = BookingListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Get bookings grouped by status"""
        queryset = self.get_queryset()
        
        # Group by status
        status_groups = {}
        for booking in queryset:
            if booking.status not in status_groups:
                status_groups[booking.status] = {
                    'status': booking.status,
                    'count': 0,
                    'bookings': []
                }
            
            status_groups[booking.status]['count'] += 1
            status_groups[booking.status]['bookings'].append({
                'id': booking.id,
                'booking_number': booking.booking_number,
                'mutamer_name': booking.mutamer.name,
                'travel_date': booking.travel_date,
                'total_amount': float(booking.total_amount),
                'currency': booking.currency
            })
        
        return Response(list(status_groups.values()))
