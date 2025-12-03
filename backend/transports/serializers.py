from rest_framework import serializers
from .models import Transport
from agencies.serializers import AgencySerializer
from accounts.serializers import UserSerializer


class TransportListSerializer(serializers.ModelSerializer):
    """Serializer for transport list views with basic information"""
    agency_name = serializers.CharField(source='agency.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Transport
        fields = [
            'id', 'name', 'transport_type', 'capacity',
            'purchase_price', 'sale_price', 'amenities',
            'is_active', 'agency_name', 'created_by_name',
            'created_at', 'updated_at'
        ]


class TransportDetailSerializer(serializers.ModelSerializer):
    """Serializer for transport detail views with full information"""
    agency = AgencySerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Transport
        fields = [
            'id', 'name', 'transport_type', 'capacity',
            'purchase_price', 'sale_price', 'amenities', 'notes',
            'is_active', 'agency', 'created_by', 'created_at', 'updated_at'
        ]


class TransportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transports"""
    
    class Meta:
        model = Transport
        fields = [
            'name', 'transport_type', 'capacity',
            'purchase_price', 'sale_price', 'amenities', 'notes', 'is_active'
        ]
    
    def validate(self, data):
        """Validate transport data"""
        if data['capacity'] <= 0:
            raise serializers.ValidationError("Capacity must be positive.")
        
        if 'purchase_price' in data and data['purchase_price'] is not None and data['purchase_price'] <= 0:
            raise serializers.ValidationError("Purchase price must be positive.")
        
        if 'sale_price' in data and data['sale_price'] is not None and data['sale_price'] <= 0:
            raise serializers.ValidationError("Sale price must be positive.")
        
        return data
    
    def create(self, validated_data):
        """Create transport with agency and user context"""
        validated_data['agency'] = self.context['request'].user.agency
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TransportUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating transports"""
    
    class Meta:
        model = Transport
        fields = [
            'name', 'transport_type', 'capacity',
            'purchase_price', 'sale_price', 'amenities', 'notes', 'is_active'
        ]
    
    def validate(self, data):
        """Validate transport data"""
        if 'capacity' in data and data['capacity'] <= 0:
            raise serializers.ValidationError("Capacity must be positive.")
        
        if 'purchase_price' in data and data['purchase_price'] is not None and data['purchase_price'] <= 0:
            raise serializers.ValidationError("Purchase price must be positive.")
        
        if 'sale_price' in data and data['sale_price'] is not None and data['sale_price'] <= 0:
            raise serializers.ValidationError("Sale price must be positive.")
        
        return data


class TransportAvailabilitySerializer(serializers.Serializer):
    """Serializer for transport availability checking"""
    transport_id = serializers.IntegerField()
    transport_name = serializers.CharField()
    transport_type = serializers.CharField()
    capacity = serializers.IntegerField()
    purchase_price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    amenities = serializers.ListField()


class TransportCostCalculationSerializer(serializers.Serializer):
    """Serializer for transport cost calculation"""
    transport_id = serializers.IntegerField()
    transport_name = serializers.CharField()
    transport_type = serializers.CharField()
    distance_km = serializers.DecimalField(max_digits=10, decimal_places=2)
    days = serializers.IntegerField()
    passengers = serializers.IntegerField()
    purchase_price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    breakdown = serializers.JSONField()
