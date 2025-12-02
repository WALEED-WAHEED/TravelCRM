from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Flight
from .serializers import (
    FlightListSerializer, FlightDetailSerializer, FlightCreateSerializer,
    FlightUpdateSerializer, FlightSearchSerializer, FlightAvailabilitySerializer,
    FlightBookingSerializer
)
from utils.permissions import IsDeveloper, IsMember, IsAgent


class FlightViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing flights.
    
    - List: Returns flights based on user role (developer sees all, member/agent see agency flights)
    - Create: Members can create flights for their agency
    - Retrieve: Get flight details with availability information
    - Update: Members can update flights in their agency
    - Destroy: Members can delete flights in their agency
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['airline', 'flight_class', 'status', 'departure_city', 'arrival_city']
    search_fields = ['airline', 'flight_number', 'departure_city', 'arrival_city', 'departure_airport', 'arrival_airport']
    ordering_fields = ['created_at', 'updated_at', 'flight_number']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return FlightListSerializer
        elif self.action in ['create']:
            return FlightCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FlightUpdateSerializer
        else:
            return FlightDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Flight.objects.select_related('agency', 'created_by')
        
        if user.role == 'developer':
            return queryset
        elif user.role in ['member', 'agent']:
            return queryset.filter(agency=user.agency)
        else:
            return Flight.objects.none()

    def perform_create(self, serializer):
        """Create flight with proper agency and user context"""
        print("=== FlightViewSet perform_create ===")
        print("Serializer data:", serializer.validated_data if hasattr(serializer, 'validated_data') else "No validated_data yet")
        print("Serializer errors:", serializer.errors if hasattr(serializer, 'errors') else "No errors yet")
        
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can create flights.")
        
        serializer.save(
            agency=self.request.user.agency,
            created_by=self.request.user
        )

    def perform_update(self, serializer):
        """Update flight with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can update flights.")
        
        serializer.save()

    def perform_destroy(self, instance):
        """Delete flight with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can delete flights.")
        
        instance.delete()

    @action(detail=True, methods=['post'])
    def update_seats(self, request, pk=None):
        """Update available seats for a flight"""
        if request.user.role not in ['developer', 'member']:
            return Response(
                {'error': 'Only developers and members can update seats.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        flight = self.get_object()
        new_available_seats = request.data.get('available_seats')
        
        if new_available_seats is None:
            return Response(
                {'error': 'available_seats field is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_available_seats = int(new_available_seats)
        except ValueError:
            return Response(
                {'error': 'available_seats must be a valid integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_available_seats < 0:
            return Response(
                {'error': 'Available seats cannot be negative.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_available_seats > flight.total_seats:
            return Response(
                {'error': 'Available seats cannot exceed total seats.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        flight.available_seats = new_available_seats
        flight.save()
        
        serializer = self.get_serializer(flight)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update flight status"""
        if request.user.role not in ['developer', 'member']:
            return Response(
                {'error': 'Only developers and members can update flight status.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        flight = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'status field is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_statuses = [choice[0] for choice in Flight.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Valid options: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        flight.status = new_status
        flight.save()
        
        serializer = self.get_serializer(flight)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def check_availability(self, request, pk=None):
        """Check flight availability and get booking information"""
        flight = self.get_object()
        
        passengers = int(request.query_params.get('passengers', 1))
        
        if passengers <= 0:
            return Response(
                {'error': 'Passenger count must be positive.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if passengers > flight.available_seats:
            return Response(
                {'error': f'Not enough seats available. Only {flight.available_seats} seats available.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate total price
        total_price = flight.price * passengers
        
        # Format duration
        hours = flight.duration_minutes // 60
        minutes = flight.duration_minutes % 60
        duration_formatted = f"{hours}h {minutes}m"
        
        serializer = FlightAvailabilitySerializer({
            'flight_id': flight.id,
            'flight_number': flight.flight_number,
            'departure_city': flight.departure_city,
            'arrival_city': flight.arrival_city,
            'flight_class': flight.flight_class,
            'price': flight.price,
            'currency': flight.currency,
            'available_seats': flight.available_seats,
            'total_seats': flight.total_seats,
            'status': flight.status,
            'duration_formatted': duration_formatted
        })
        
        return Response({
            'flight': serializer.data,
            'passengers': passengers,
            'total_price': float(total_price),
            'currency': flight.currency,
            'available': flight.available_seats >= passengers
        })

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search flights with advanced filters"""
        queryset = self.get_queryset().filter(status='scheduled')
        
        # Apply filters
        departure_city = request.query_params.get('departure_city')
        if departure_city:
            queryset = queryset.filter(departure_city__icontains=departure_city)
        
        arrival_city = request.query_params.get('arrival_city')
        if arrival_city:
            queryset = queryset.filter(arrival_city__icontains=arrival_city)
        
        
        flight_class = request.query_params.get('flight_class')
        if flight_class:
            queryset = queryset.filter(flight_class=flight_class)
        
        max_price = request.query_params.get('max_price')
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                return Response(
                    {'error': 'Invalid max_price format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        min_seats = request.query_params.get('min_seats')
        if min_seats:
            try:
                queryset = queryset.filter(available_seats__gte=int(min_seats))
            except ValueError:
                return Response(
                    {'error': 'Invalid min_seats format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Search by airline, flight number, or cities
        search_term = request.query_params.get('search')
        if search_term:
            queryset = queryset.filter(
                Q(airline__icontains=search_term) | 
                Q(flight_number__icontains=search_term) |
                Q(departure_city__icontains=search_term) |
                Q(arrival_city__icontains=search_term) |
                Q(departure_airport__icontains=search_term) |
                Q(arrival_airport__icontains=search_term)
            )
        
        # Prepare search results
        search_results = []
        for flight in queryset:
            # Format duration
            hours = flight.duration_minutes // 60
            minutes = flight.duration_minutes % 60
            duration_formatted = f"{hours}h {minutes}m"
            
            route_summary = f"{flight.departure_city} ({flight.departure_airport}) → {flight.arrival_city} ({flight.arrival_airport})"
            
            search_results.append({
                'flight_id': flight.id,
                'airline': flight.airline,
                'flight_number': flight.flight_number,
                'departure_airport': flight.departure_airport,
                'arrival_airport': flight.arrival_airport,
                'departure_city': flight.departure_city,
                'arrival_city': flight.arrival_city,
                'flight_class': flight.flight_class,
                'price': flight.price,
                'currency': flight.currency,
                'available_seats': flight.available_seats,
                'duration_formatted': duration_formatted,
                'route_summary': route_summary
            })
        
        return Response(search_results)

    @action(detail=False, methods=['get'])
    def by_route(self, request):
        """Get flights grouped by route"""
        queryset = self.get_queryset().filter(status='scheduled')
        
        # Group by route
        routes = {}
        for flight in queryset:
            route_key = f"{flight.departure_city} → {flight.arrival_city}"
            if route_key not in routes:
                routes[route_key] = {
                    'route': route_key,
                    'departure_city': flight.departure_city,
                    'arrival_city': flight.arrival_city,
                    'flights': []
                }
            
            # Format duration
            hours = flight.duration_minutes // 60
            minutes = flight.duration_minutes % 60
            duration_formatted = f"{hours}h {minutes}m"
            
            routes[route_key]['flights'].append({
                'id': flight.id,
                'airline': flight.airline,
                'flight_number': flight.flight_number,
                'flight_class': flight.flight_class,
                'price': float(flight.price),
                'currency': flight.currency,
                'available_seats': flight.available_seats,
                'duration_formatted': duration_formatted
            })
        
        return Response(list(routes.values()))

    @action(detail=False, methods=['get'])
    def by_airline(self, request):
        """Get flights grouped by airline"""
        queryset = self.get_queryset().filter(status='scheduled')
        
        # Group by airline
        airlines = {}
        for flight in queryset:
            if flight.airline not in airlines:
                airlines[flight.airline] = {
                    'airline': flight.airline,
                    'flights': []
                }
            
            # Format duration
            hours = flight.duration_minutes // 60
            minutes = flight.duration_minutes % 60
            duration_formatted = f"{hours}h {minutes}m"
            
            airlines[flight.airline]['flights'].append({
                'id': flight.id,
                'flight_number': flight.flight_number,
                'departure_city': flight.departure_city,
                'arrival_city': flight.arrival_city,
                'flight_class': flight.flight_class,
                'price': float(flight.price),
                'currency': flight.currency,
                'available_seats': flight.available_seats,
                'duration_formatted': duration_formatted
            })
        
        return Response(list(airlines.values()))

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming flights (departing in the next 24 hours)"""
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        
        queryset = self.get_queryset().filter(status='scheduled')
        
        serializer = FlightListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get flights departing today"""
        today = datetime.now().date()
        
        queryset = self.get_queryset().filter(status='scheduled')
        
        serializer = FlightListSerializer(queryset, many=True)
        return Response(serializer.data)
