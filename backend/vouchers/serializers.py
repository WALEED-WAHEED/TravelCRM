from rest_framework import serializers
from .models import Voucher, VoucherService
from mutamers.serializers import MutamerListSerializer
from accounts.serializers import UserSerializer


class VoucherServiceSerializer(serializers.ModelSerializer):
    """Serializer for voucher services"""
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = VoucherService
        fields = ['id', 'service_type', 'service_name', 'description', 
                  'amount', 'quantity', 'total']
        read_only_fields = ['id', 'total']


class VoucherSerializer(serializers.ModelSerializer):
    """Serializer for vouchers"""
    services = VoucherServiceSerializer(many=True, read_only=True)
    balance_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    mutamer_name = serializers.CharField(source='mutamer.name', read_only=True)
    agent_name = serializers.CharField(source='agent.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)

    class Meta:
        model = Voucher
        fields = [
            'id', 'voucher_number', 'agent', 'agent_name', 'mutamer', 'mutamer_name',
            'status', 'total_amount', 'paid_amount', 'balance_amount', 'notes',
            'approved_by', 'approved_by_name', 'approved_at', 'public_token',
            'services', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'voucher_number', 'public_token', 'agent', 
            'approved_by', 'approved_at', 'created_at', 'updated_at'
        ]


class VoucherCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating vouchers"""
    services = VoucherServiceSerializer(many=True, required=False)
    
    class Meta:
        model = Voucher
        fields = [
            'mutamer', 'total_amount', 'paid_amount', 'notes', 'status', 'services'
        ]
        extra_kwargs = {
            'status': {'required': False}
        }
    
    def validate_total_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total amount must be positive.")
        return value
    
    def validate_paid_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Paid amount cannot be negative.")
        return value
    
    def validate(self, data):
        if data.get('paid_amount', 0) > data['total_amount']:
            raise serializers.ValidationError("Paid amount cannot exceed total amount.")
        return data
    
    def create(self, validated_data):
        services_data = validated_data.pop('services', [])
        validated_data['agent'] = self.context['request'].user
        voucher = Voucher.objects.create(**validated_data)
        
        for service_data in services_data:
            VoucherService.objects.create(voucher=voucher, **service_data)
        
        return voucher


class VoucherUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating vouchers"""
    services = VoucherServiceSerializer(many=True, required=False)
    
    class Meta:
        model = Voucher
        fields = [
            'mutamer', 'status', 'total_amount', 'paid_amount', 'notes', 'services'
        ]
    
    def validate_total_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total amount must be positive.")
        return value
    
    def validate_paid_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Paid amount cannot be negative.")
        return value
    
    def validate(self, data):
        if data.get('paid_amount', 0) > data.get('total_amount', self.instance.total_amount):
            raise serializers.ValidationError("Paid amount cannot exceed total amount.")
        return data
    
    def update(self, instance, validated_data):
        services_data = validated_data.pop('services', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if services_data is not None:
            instance.services.all().delete()
            for service_data in services_data:
                VoucherService.objects.create(voucher=instance, **service_data)
        
        return instance


class VoucherStatsSerializer(serializers.Serializer):
    """Serializer for voucher statistics"""
    total_vouchers = serializers.IntegerField()
    pending_vouchers = serializers.IntegerField()
    approved_vouchers = serializers.IntegerField()
    rejected_vouchers = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    recent_vouchers = serializers.IntegerField()
