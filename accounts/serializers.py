from django.contrib.auth import get_user_model
from rest_framework import serializers

from agencies.models import Agency

User = get_user_model()


class AgencySimpleSerializer(serializers.ModelSerializer):
    """Simple agency serializer for nested representations"""
    class Meta:
        model = Agency
        fields = ["id", "name", "code"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    agency = AgencySimpleSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "full_name", "role", "phone", "is_active", "agency",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "username", "role", "created_at", "updated_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users (Developer only)"""
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    agency_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "username", "email", "password", "first_name", "last_name",
            "role", "phone", "agency_id", "is_active"
        ]

    def validate(self, attrs):
        # If role is member or agent, agency is required
        role = attrs.get('role')
        agency_id = attrs.get('agency_id')

        if role in ['member', 'agent'] and not agency_id:
            raise serializers.ValidationError({
                "agency_id": "Agency is required for member and agent roles"
            })

        return attrs

    def create(self, validated_data):
        agency_id = validated_data.pop('agency_id', None)
        password = validated_data.pop('password')

        # Get agency if provided
        if agency_id:
            try:
                agency = Agency.objects.get(id=agency_id)
                validated_data['agency'] = agency
            except Agency.DoesNotExist:
                raise serializers.ValidationError({"agency_id": "Invalid agency ID"}) from None

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "is_active"]


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, write_only=True, min_length=8, style={'input_type': 'password'})

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
