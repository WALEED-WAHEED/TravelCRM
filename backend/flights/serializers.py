from rest_framework import serializers
from .models import Flight, FlightSegment
from agencies.serializers import AgencySerializer
from accounts.serializers import UserSerializer


class FlightSegmentSerializer(serializers.ModelSerializer):
    """Serializer for flight segments"""
    
    class Meta:
        model = FlightSegment
        fields = [
            'id', 'segment_number', 'departure_city', 'arrival_city',
            'departure_airport', 'arrival_airport', 'departure_country', 'arrival_country',
            'flight_number', 'airline', 'notes'
        ]


class FlightListSerializer(serializers.ModelSerializer):
    """Serializer for flight list views with basic information"""
    agency_name = serializers.CharField(source='agency.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    occupancy_rate = serializers.SerializerMethodField()
    segments = FlightSegmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Flight
        fields = [
            'id', 'flight_type', 'airline', 'flight_number', 'pnr_number', 'departure_airport', 'arrival_airport',
            'departure_city', 'arrival_city', 'departure_country', 'arrival_country',
            'flight_class', 'sale_price', 'purchase_price', 'currency',
            'available_seats', 'total_seats', 'status', 'notes', 'agency_name', 'created_by_name',
            'occupancy_rate', 'segments', 'created_at', 'updated_at'
        ]
    
    
    def get_occupancy_rate(self, obj):
        if obj.total_seats > 0:
            occupied = obj.total_seats - obj.available_seats
            return round((occupied / obj.total_seats) * 100, 2)
        return 0


class FlightDetailSerializer(serializers.ModelSerializer):
    """Serializer for flight detail views with full information"""
    agency = AgencySerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    occupancy_rate = serializers.SerializerMethodField()
    route_summary = serializers.SerializerMethodField()
    segments = FlightSegmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Flight
        fields = [
            'id', 'flight_type', 'airline', 'flight_number', 'pnr_number', 'departure_airport', 'arrival_airport',
            'departure_city', 'arrival_city', 'departure_country', 'arrival_country',
            'flight_class', 'sale_price', 'purchase_price', 'currency',
            'available_seats', 'total_seats', 'status', 'baggage_allowance',
            'meal_included', 'notes', 'agency', 'created_by',
            'occupancy_rate', 'route_summary', 'segments', 'created_at', 'updated_at'
        ]
    
    
    def get_occupancy_rate(self, obj):
        if obj.total_seats > 0:
            occupied = obj.total_seats - obj.available_seats
            return round((occupied / obj.total_seats) * 100, 2)
        return 0
    
    def get_route_summary(self, obj):
        if obj.flight_type == 'multi_city' and obj.segments.exists():
            # For multi-city flights, show the route through all segments
            segments = obj.segments.all().order_by('segment_number')
            route_parts = []
            for segment in segments:
                route_parts.append(f"{segment.departure_city} → {segment.arrival_city}")
            return " → ".join(route_parts)
        else:
            # For one-way and return flights, show the main route
            return f"{obj.departure_city} ({obj.departure_airport}) → {obj.arrival_city} ({obj.arrival_airport})"


class FlightCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating flights"""
    segments = FlightSegmentSerializer(many=True, required=False)
    
    class Meta:
        model = Flight
        fields = [
            'flight_type', 'airline', 'flight_number', 'pnr_number', 'departure_city', 'arrival_city',
            'sale_price', 'purchase_price', 'notes', 'segments'
        ]
    
    def __init__(self, *args, **kwargs):
        print("=== FlightCreateSerializer __init__ ===")
        print("args:", args)
        print("kwargs:", kwargs)
        super().__init__(*args, **kwargs)
        print("Serializer initialized successfully")
    
    def validate_flight_number(self, value):
        """Ensure flight number is unique within the agency"""
        print(f"=== validate_flight_number called with: {value}")
        if value:  # Only validate if flight_number is provided
            user = self.context['request'].user
            if Flight.objects.filter(flight_number=value, agency=user.agency).exists():
                raise serializers.ValidationError("Flight number must be unique within your agency.")
        return value
    
    def validate(self, data):
        """Validate flight data"""
        print("=== FlightCreateSerializer Validation ===")
        print("Received data:", data)
        print("Data types:")
        for key, value in data.items():
            print(f"  {key}: {type(value)} = {value}")
        
        try:
            if 'sale_price' in data and data['sale_price'] <= 0:
                raise serializers.ValidationError("Sale price must be positive.")
            
            if 'purchase_price' in data and data['purchase_price'] <= 0:
                raise serializers.ValidationError("Purchase price must be positive.")
            
            print("Validation passed successfully")
            return data
        except Exception as e:
            print(f"Validation error: {e}")
            raise
    
    def create(self, validated_data):
        """Create flight with agency and user context"""
        print("=== FlightCreateSerializer Create ===")
        print("Validated data:", validated_data)
        
        # Extract segments data if present
        segments_data = validated_data.pop('segments', [])
        
        validated_data['agency'] = self.context['request'].user.agency
        validated_data['created_by'] = self.context['request'].user
        print("About to create flight with data:", validated_data)
        
        # Create the flight
        flight = super().create(validated_data)
        
        # Create segments for multi-city flights
        if flight.flight_type == 'multi_city' and segments_data:
            for segment_data in segments_data:
                FlightSegment.objects.create(flight=flight, **segment_data)
        
        print("Flight created successfully:", flight)
        return flight


class FlightUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating flights"""
    segments = FlightSegmentSerializer(many=True, required=False)
    
    class Meta:
        model = Flight
        fields = [
            'flight_type', 'airline', 'flight_number', 'pnr_number', 'departure_city', 'arrival_city',
            'sale_price', 'purchase_price', 'notes', 'segments'
        ]
    
    def validate_flight_number(self, value):
        """Ensure flight number is unique within the agency"""
        if value:  # Only validate if flight_number is provided
            user = self.context['request'].user
            instance = self.instance
            if Flight.objects.filter(flight_number=value, agency=user.agency).exclude(id=instance.id).exists():
                raise serializers.ValidationError("Flight number must be unique within your agency.")
        return value
    
    def validate(self, data):
        """Validate flight data"""
        # Check departure/arrival times if both provided
        
        if 'sale_price' in data and data['sale_price'] <= 0:
            raise serializers.ValidationError("Sale price must be positive.")
        
        if 'purchase_price' in data and data['purchase_price'] <= 0:
            raise serializers.ValidationError("Purchase price must be positive.")
        
        return data
    
    def update(self, instance, validated_data):
        """Update flight with segments handling"""
        # Extract segments data if present
        segments_data = validated_data.pop('segments', [])
        
        # Update the flight instance
        flight = super().update(instance, validated_data)
        
        # Handle segments for multi-city flights
        if flight.flight_type == 'multi_city' and segments_data:
            # Delete existing segments
            flight.segments.all().delete()
            
            # Create new segments
            for segment_data in segments_data:
                FlightSegment.objects.create(flight=flight, **segment_data)
        elif flight.flight_type != 'multi_city':
            # If changing from multi-city to another type, delete segments
            flight.segments.all().delete()
        
        return flight


class FlightSearchSerializer(serializers.Serializer):
    """Serializer for flight search results"""
    flight_id = serializers.IntegerField()
    airline = serializers.CharField()
    flight_number = serializers.CharField()
    departure_airport = serializers.CharField()
    arrival_airport = serializers.CharField()
    departure_city = serializers.CharField()
    arrival_city = serializers.CharField()
    flight_class = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    available_seats = serializers.IntegerField()
    route_summary = serializers.CharField()


class FlightAvailabilitySerializer(serializers.Serializer):
    """Serializer for flight availability checking"""
    flight_id = serializers.IntegerField()
    flight_number = serializers.CharField()
    departure_city = serializers.CharField()
    arrival_city = serializers.CharField()
    flight_class = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    available_seats = serializers.IntegerField()
    total_seats = serializers.IntegerField()
    status = serializers.CharField()


class FlightBookingSerializer(serializers.Serializer):
    """Serializer for flight booking information"""
    flight_id = serializers.IntegerField()
    flight_number = serializers.CharField()
    airline = serializers.CharField()
    departure_city = serializers.CharField()
    arrival_city = serializers.CharField()
    flight_class = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    available_seats = serializers.IntegerField()
    baggage_allowance = serializers.CharField()
    meal_included = serializers.BooleanField()
