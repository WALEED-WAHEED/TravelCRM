from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Hotel, HotelRoom, HotelImage
from .serializers import (
    HotelListSerializer, HotelDetailSerializer, HotelCreateSerializer,
    HotelUpdateSerializer, HotelRoomSerializer, HotelImageSerializer,
    HotelAvailabilitySerializer, HotelSearchSerializer
)
from utils.permissions import IsDeveloper, IsMember, IsAgent


class HotelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing hotels and their rooms.
    
    - List: Returns hotels based on user role (developer sees all, member/agent see agency hotels)
    - Create: Members can create hotels for their agency
    - Retrieve: Get hotel details with rooms and images
    - Update: Members can update hotels in their agency
    - Destroy: Members can delete hotels in their agency
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['city', 'country', 'rating', 'is_active']
    search_fields = ['name', 'code', 'city', 'country', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name', 'rating', 'city']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return HotelListSerializer
        elif self.action in ['create']:
            return HotelCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return HotelUpdateSerializer
        else:
            return HotelDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Hotel.objects.select_related('agency', 'created_by').prefetch_related('rooms', 'images')
        
        if user.role == 'developer':
            return queryset
        elif user.role in ['member', 'agent']:
            return queryset.filter(agency=user.agency)
        else:
            return Hotel.objects.none()

    def perform_create(self, serializer):
        """Create hotel with proper agency and user context"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can create hotels.")
        
        serializer.save(
            agency=self.request.user.agency,
            created_by=self.request.user
        )

    def perform_update(self, serializer):
        """Update hotel with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can update hotels.")
        
        serializer.save()

    def perform_destroy(self, instance):
        """Delete hotel with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can delete hotels.")
        
        instance.delete()

    @action(detail=True, methods=['post'])
    def upload_images(self, request, pk=None):
        """Upload multiple images for a hotel"""
        if request.user.role not in ['developer', 'member']:
            return Response(
                {'error': 'Only developers and members can upload images.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        hotel = self.get_object()
        images = request.FILES.getlist('images')
        captions = request.data.getlist('captions', [])
        
        if not images:
            return Response(
                {'error': 'No images provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_images = []
        for i, image in enumerate(images):
            caption = captions[i] if i < len(captions) else ''
            hotel_image = HotelImage.objects.create(
                hotel=hotel,
                image=image,
                caption=caption
            )
            created_images.append(hotel_image)
        
        serializer = HotelImageSerializer(created_images, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def check_availability(self, request, pk=None):
        """Check hotel availability for given dates"""
        hotel = self.get_object()
        
        check_in = request.query_params.get('check_in')
        check_out = request.query_params.get('check_out')
        room_type = request.query_params.get('room_type')
        
        if not check_in or not check_out:
            return Response(
                {'error': 'check_in and check_out dates are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if check_in_date >= check_out_date:
            return Response(
                {'error': 'Check-in date must be before check-out date.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter rooms by type if specified
        rooms_query = hotel.rooms.filter(available_rooms__gt=0)
        if room_type:
            rooms_query = rooms_query.filter(room_type=room_type)
        
        available_rooms = []
        total_available = 0
        
        for room in rooms_query:
            available_rooms.append({
                'room_id': room.id,
                'room_type': room.room_type,
                'price_per_night': float(room.price_per_night),
                'capacity': room.capacity,
                'available_rooms': room.available_rooms,
                'amenities': room.amenities
            })
            total_available += room.available_rooms
        
        serializer = HotelAvailabilitySerializer({
            'hotel_id': hotel.id,
            'check_in': check_in_date,
            'check_out': check_out_date,
            'room_type': room_type,
            'available_rooms': available_rooms,
            'total_available': total_available
        })
        
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def get_rooms(self, request, pk=None):
        """Get all rooms for a hotel"""
        hotel = self.get_object()
        rooms = hotel.rooms.all()
        
        # Filter by room type if specified
        room_type = request.query_params.get('room_type')
        if room_type:
            rooms = rooms.filter(room_type=room_type)
        
        serializer = HotelRoomSerializer(rooms, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def get_images(self, request, pk=None):
        """Get all images for a hotel"""
        hotel = self.get_object()
        images = hotel.images.all()
        
        # Filter by primary image if specified
        primary_only = request.query_params.get('primary_only')
        if primary_only and primary_only.lower() == 'true':
            images = images.filter(is_primary=True)
        
        serializer = HotelImageSerializer(images, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search hotels with advanced filters"""
        queryset = self.get_queryset().filter(is_active=True)
        
        # Apply filters
        city = request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        
        country = request.query_params.get('country')
        if country:
            queryset = queryset.filter(country__icontains=country)
        
        min_rating = request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(rating__gte=min_rating)
        
        max_price = request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(rooms__price_per_night__lte=max_price).distinct()
        
        room_type = request.query_params.get('room_type')
        if room_type:
            queryset = queryset.filter(rooms__room_type=room_type).distinct()
        
        # Search by name, code, or description
        search_term = request.query_params.get('search')
        if search_term:
            queryset = queryset.filter(
                Q(name__icontains=search_term) | 
                Q(code__icontains=search_term) |
                Q(description__icontains=search_term) |
                Q(city__icontains=search_term) |
                Q(country__icontains=search_term)
            )
        
        # Prepare search results
        search_results = []
        for hotel in queryset:
            # Get price range
            rooms = hotel.rooms.all()
            if rooms:
                min_price = min(room.price_per_night for room in rooms)
                max_price = max(room.price_per_night for room in rooms)
                price_range = {'min': float(min_price), 'max': float(max_price)}
            else:
                price_range = {'min': 0, 'max': 0}
            
            # Get total available rooms
            total_available = sum(room.available_rooms for room in rooms)
            
            # Get primary image
            primary_img = hotel.images.filter(is_primary=True).first()
            primary_image_url = primary_img.image.url if primary_img else None
            
            search_results.append({
                'hotel_id': hotel.id,
                'hotel_name': hotel.name,
                'hotel_code': hotel.code,
                'city': hotel.city,
                'country': hotel.country,
                'rating': hotel.rating,
                'price_range': price_range,
                'available_rooms': total_available,
                'primary_image': primary_image_url
            })
        
        return Response(search_results)

    @action(detail=False, methods=['get'])
    def by_location(self, request):
        """Get hotels grouped by location"""
        queryset = self.get_queryset().filter(is_active=True)
        
        # Group by city, country
        locations = {}
        for hotel in queryset:
            location_key = f"{hotel.city}, {hotel.country}"
            if location_key not in locations:
                locations[location_key] = {
                    'location': location_key,
                    'city': hotel.city,
                    'country': hotel.country,
                    'hotels': []
                }
            
            # Get primary image
            primary_img = hotel.images.filter(is_primary=True).first()
            primary_image_url = primary_img.image.url if primary_img else None
            
            locations[location_key]['hotels'].append({
                'id': hotel.id,
                'name': hotel.name,
                'code': hotel.code,
                'rating': hotel.rating,
                'primary_image': primary_image_url
            })
        
        return Response(list(locations.values()))


class HotelRoomViewSet(viewsets.ModelViewSet):
    """ViewSet for managing hotel rooms"""
    serializer_class = HotelRoomSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        hotel_id = self.kwargs.get('hotel_pk')
        
        if user.role == 'developer':
            return HotelRoom.objects.filter(hotel_id=hotel_id)
        elif user.role in ['member', 'agent']:
            return HotelRoom.objects.filter(
                hotel_id=hotel_id,
                hotel__agency=user.agency
            )
        else:
            return HotelRoom.objects.none()
    
    def perform_create(self, serializer):
        """Create room with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can create rooms.")
        
        hotel_id = self.kwargs.get('hotel_pk')
        hotel = Hotel.objects.get(id=hotel_id)
        
        # Check if user has permission to create rooms for this hotel
        if self.request.user.role == 'member' and hotel.agency != self.request.user.agency:
            raise permissions.PermissionDenied("You can only create rooms for your agency's hotels.")
        
        serializer.save(hotel=hotel)
    
    def perform_update(self, serializer):
        """Update room with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can update rooms.")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Delete room with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can delete rooms.")
        
        instance.delete()


class HotelImageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing hotel images"""
    serializer_class = HotelImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        hotel_id = self.kwargs.get('hotel_pk')
        
        if user.role == 'developer':
            return HotelImage.objects.filter(hotel_id=hotel_id)
        elif user.role in ['member', 'agent']:
            return HotelImage.objects.filter(
                hotel_id=hotel_id,
                hotel__agency=user.agency
            )
        else:
            return HotelImage.objects.none()

    def perform_create(self, serializer):
        """Create image with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can upload images.")
        
        hotel_id = self.kwargs.get('hotel_pk')
        hotel = Hotel.objects.get(id=hotel_id)
        
        # Check if user has permission to upload images for this hotel
        if self.request.user.role == 'member' and hotel.agency != self.request.user.agency:
            raise permissions.PermissionDenied("You can only upload images for your agency's hotels.")
        
        serializer.save(hotel=hotel)
    
    def perform_update(self, serializer):
        """Update image with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can update images.")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Delete image with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can delete images.")
        
        instance.delete()
