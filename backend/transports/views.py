from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from decimal import Decimal
from .models import Transport
from .serializers import (
    TransportListSerializer, TransportDetailSerializer, TransportCreateSerializer,
    TransportUpdateSerializer, TransportAvailabilitySerializer, TransportCostCalculationSerializer
)
from utils.permissions import IsDeveloper, IsMember, IsAgent


class TransportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transports.
    
    - List: Returns transports based on user role (developer sees all, member/agent see agency transports)
    - Create: Members can create transports for their agency
    - Retrieve: Get transport details with availability information
    - Update: Members can update transports in their agency
    - Destroy: Members can delete transports in their agency
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['transport_type', 'is_active']
    search_fields = ['name', 'transport_type']
    ordering_fields = ['created_at', 'updated_at', 'name', 'capacity', 'sale_price']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return TransportListSerializer
        elif self.action in ['create']:
            return TransportCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TransportUpdateSerializer
        else:
            return TransportDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Transport.objects.select_related('agency', 'created_by')
        
        if user.role == 'developer':
            return queryset
        elif user.role in ['member', 'agent']:
            return queryset.filter(agency=user.agency)
        else:
            return Transport.objects.none()

    def perform_create(self, serializer):
        """Create transport with proper agency and user context"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can create transports.")
        
        serializer.save(
            agency=self.request.user.agency,
            created_by=self.request.user
        )

    def perform_update(self, serializer):
        """Update transport with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can update transports.")
        
        serializer.save()

    def perform_destroy(self, instance):
        """Delete transport with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can delete transports.")
        
        instance.delete()

    @action(detail=True, methods=['get'])
    def check_availability(self, request, pk=None):
        """Check transport availability"""
        transport = self.get_object()
        
        passengers = int(request.query_params.get('passengers', 1))
        
        if passengers <= 0:
            return Response(
                {'error': 'Passenger count must be positive.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if passengers > transport.capacity:
            return Response(
                {'error': f'Not enough capacity. Vehicle capacity: {transport.capacity}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not transport.is_active:
            return Response(
                {'error': 'Transport is not active.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TransportAvailabilitySerializer({
            'transport_id': transport.id,
            'transport_name': transport.name,
            'transport_type': transport.transport_type,
            'capacity': transport.capacity,
            'purchase_price': transport.purchase_price,
            'sale_price': transport.sale_price,
            'amenities': transport.amenities
        })
        
        return Response({
            'transport': serializer.data,
            'passengers': passengers,
            'available': True
        })

    @action(detail=True, methods=['get'])
    def calculate_cost(self, request, pk=None):
        """Calculate transport cost for given distance and days"""
        transport = self.get_object()
        
        distance_km = request.query_params.get('distance_km')
        days = request.query_params.get('days')
        passengers = int(request.query_params.get('passengers', 1))
        
        if not distance_km or not days:
            return Response(
                {'error': 'distance_km and days are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            distance_km = Decimal(distance_km)
            days = int(days)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid distance_km or days format.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if distance_km <= 0 or days <= 0:
            return Response(
                {'error': 'Distance and days must be positive.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate costs based on sale price
        if transport.sale_price:
            total_cost = transport.sale_price * days  # Use sale price per day
        else:
            total_cost = Decimal('0')  # No pricing available
        
        breakdown = {
            'distance_km': float(distance_km),
            'days': days,
            'passengers': passengers,
            'purchase_price': float(transport.purchase_price) if transport.purchase_price else None,
            'sale_price': float(transport.sale_price) if transport.sale_price else None,
            'daily_cost': float(transport.sale_price) if transport.sale_price else 0,
            'subtotal': float(total_cost),
            'discounts': [],
            'taxes': [],
            'total': float(total_cost)
        }
        
        serializer = TransportCostCalculationSerializer({
            'transport_id': transport.id,
            'transport_name': transport.name,
            'transport_type': transport.transport_type,
            'distance_km': distance_km,
            'days': days,
            'passengers': passengers,
            'purchase_price': transport.purchase_price,
            'sale_price': transport.sale_price,
            'total_cost': total_cost,
            'breakdown': breakdown
        })
        
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available transports"""
        queryset = self.get_queryset().filter(is_active=True)
        
        # Filter by capacity if specified
        min_capacity = request.query_params.get('min_capacity')
        if min_capacity:
            try:
                queryset = queryset.filter(capacity__gte=int(min_capacity))
            except ValueError:
                return Response(
                    {'error': 'Invalid min_capacity format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Filter by transport type if specified
        transport_type = request.query_params.get('transport_type')
        if transport_type:
            queryset = queryset.filter(transport_type=transport_type)
        
        serializer = TransportListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get transports grouped by type"""
        queryset = self.get_queryset().filter(is_active=True)
        
        # Group by transport type
        types = {}
        for transport in queryset:
            if transport.transport_type not in types:
                types[transport.transport_type] = {
                    'transport_type': transport.transport_type,
                    'transports': []
                }
            
            types[transport.transport_type]['transports'].append({
                'id': transport.id,
                'name': transport.name,
                'capacity': transport.capacity,
                'purchase_price': float(transport.purchase_price) if transport.purchase_price else None,
                'sale_price': float(transport.sale_price) if transport.sale_price else None,
                'amenities': transport.amenities
            })
        
        return Response(list(types.values()))
