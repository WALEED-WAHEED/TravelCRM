from rest_framework import serializers
from .models import Hotel, HotelRoom, HotelImage
from agencies.serializers import AgencySerializer
from accounts.serializers import UserSerializer


class HotelImageSerializer(serializers.ModelSerializer):
    """Serializer for hotel images"""
    
    class Meta:
        model = HotelImage
        fields = ['id', 'image', 'caption', 'is_primary']


class HotelRoomSerializer(serializers.ModelSerializer):
    """Serializer for hotel rooms"""
    
    class Meta:
        model = HotelRoom
        fields = [
            'id', 'room_type', 'price_per_night', 'capacity', 
            'available_rooms', 'amenities'
        ]


class HotelRoomCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating hotel rooms"""
    
    class Meta:
        model = HotelRoom
        fields = [
            'room_type', 'price_per_night', 'capacity', 
            'available_rooms', 'amenities'
        ]
    
    def validate_price_per_night(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price per night must be positive.")
        return value
    
    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be positive.")
        return value
    
    def validate_available_rooms(self, value):
        if value < 0:
            raise serializers.ValidationError("Available rooms cannot be negative.")
        return value


class HotelListSerializer(serializers.ModelSerializer):
    """Serializer for hotel list views with basic information"""
    agency_name = serializers.CharField(source='agency.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    room_count = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Hotel
        fields = [
            'id', 'name', 'code', 'address', 'city', 'country',
            'phone', 'email', 'rating', 'description', 'amenities', 
            'sale_price', 'purchase_price', 'is_active', 
            'agency_name', 'created_by_name', 'room_count', 'primary_image', 
            'created_at', 'updated_at'
        ]
    
    def get_room_count(self, obj):
        return obj.rooms.count()
    
    def get_primary_image(self, obj):
        primary_img = obj.images.filter(is_primary=True).first()
        if primary_img:
            return primary_img.image.url
        return None


class HotelDetailSerializer(serializers.ModelSerializer):
    """Serializer for hotel detail views with full information"""
    agency = AgencySerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    rooms = HotelRoomSerializer(many=True, read_only=True)
    images = HotelImageSerializer(many=True, read_only=True)
    room_count = serializers.SerializerMethodField()
    total_available_rooms = serializers.SerializerMethodField()
    
    class Meta:
        model = Hotel
        fields = [
            'id', 'name', 'code', 'address', 'city', 'country',
            'phone', 'email', 'rating', 'description', 'amenities',
            'sale_price', 'purchase_price', 'is_active', 'agency', 'created_by', 'rooms',
            'images', 'room_count', 'total_available_rooms', 'created_at', 'updated_at'
        ]
    
    def get_room_count(self, obj):
        return obj.rooms.count()
    
    def get_total_available_rooms(self, obj):
        return sum(room.available_rooms for room in obj.rooms.all())


class HotelCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating hotels"""
    rooms = HotelRoomCreateSerializer(many=True, required=False)
    images = HotelImageSerializer(many=True, required=False)
    
    class Meta:
        model = Hotel
        fields = [
            'name', 'code', 'address', 'city', 'country',
            'phone', 'email', 'rating', 'description', 'amenities',
            'sale_price', 'purchase_price', 'is_active', 'rooms', 'images'
        ]
    
    def validate_code(self, value):
        """Ensure hotel code is unique within the agency"""
        user = self.context['request'].user
        if Hotel.objects.filter(code=value, agency=user.agency).exists():
            raise serializers.ValidationError("Hotel code must be unique within your agency.")
        return value
    
    def validate_rating(self, value):
        """Validate hotel rating"""
        if value is not None and not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
    
    def create(self, validated_data):
        """Create hotel with agency and user context"""
        rooms_data = validated_data.pop('rooms', [])
        images_data = validated_data.pop('images', [])
        
        validated_data['agency'] = self.context['request'].user.agency
        validated_data['created_by'] = self.context['request'].user
        hotel = Hotel.objects.create(**validated_data)
        
        # Create rooms
        for room_data in rooms_data:
            HotelRoom.objects.create(hotel=hotel, **room_data)
        
        # Create images
        for image_data in images_data:
            HotelImage.objects.create(hotel=hotel, **image_data)
        
        return hotel


class HotelUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating hotels"""
    rooms = HotelRoomCreateSerializer(many=True, required=False)
    images = HotelImageSerializer(many=True, required=False)
    
    class Meta:
        model = Hotel
        fields = [
            'name', 'code', 'address', 'city', 'country',
            'phone', 'email', 'rating', 'description', 'amenities',
            'sale_price', 'purchase_price', 'is_active', 'rooms', 'images'
        ]
    
    def validate_code(self, value):
        """Ensure hotel code is unique within the agency"""
        user = self.context['request'].user
        instance = self.instance
        if Hotel.objects.filter(code=value, agency=user.agency).exclude(id=instance.id).exists():
            raise serializers.ValidationError("Hotel code must be unique within your agency.")
        return value
    
    def validate_rating(self, value):
        """Validate hotel rating"""
        if value is not None and not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
    
    def update(self, instance, validated_data):
        """Update hotel with rooms and images"""
        rooms_data = validated_data.pop('rooms', None)
        images_data = validated_data.pop('images', None)
        
        # Update hotel fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update rooms if provided
        if rooms_data is not None:
            # Delete existing rooms
            instance.rooms.all().delete()
            # Create new rooms
            for room_data in rooms_data:
                HotelRoom.objects.create(hotel=instance, **room_data)
        
        # Update images if provided
        if images_data is not None:
            # Delete existing images
            instance.images.all().delete()
            # Create new images
            for image_data in images_data:
                HotelImage.objects.create(hotel=instance, **image_data)
        
        return instance


class HotelAvailabilitySerializer(serializers.Serializer):
    """Serializer for hotel availability checking"""
    hotel_id = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    room_type = serializers.CharField(required=False)
    available_rooms = serializers.ListField(child=serializers.DictField())
    total_available = serializers.IntegerField()


class HotelSearchSerializer(serializers.Serializer):
    """Serializer for hotel search results"""
    hotel_id = serializers.IntegerField()
    hotel_name = serializers.CharField()
    hotel_code = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    country = serializers.CharField()
    rating = serializers.IntegerField()
    price_range = serializers.DictField()
    available_rooms = serializers.IntegerField()
    primary_image = serializers.URLField(required=False)
