from rest_framework import serializers

from .models import Agency


class AgencySerializer(serializers.ModelSerializer):
    """Full agency serializer with all fields"""
    member_count = serializers.IntegerField(read_only=True)
    agent_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Agency
        fields = [
            "id",
            "name",
            "code",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "is_active",
            "member_count",
            "agent_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "member_count", "agent_count"]

    def validate_code(self, value):
        """Validate agency code is unique"""
        instance = self.instance
        if instance and instance.code == value:
            return value

        if Agency.objects.filter(code=value).exists():
            raise serializers.ValidationError("Agency with this code already exists.")
        return value


class AgencyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating agencies"""
    class Meta:
        model = Agency
        fields = [
            "name",
            "code",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "is_active",
        ]


class AgencyStatisticsSerializer(serializers.Serializer):
    """Serializer for agency statistics"""
    total_bookings = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    member_count = serializers.IntegerField()
    agent_count = serializers.IntegerField()
