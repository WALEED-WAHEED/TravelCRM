from rest_framework import serializers
from .models import Mutamer, MutamerDocument
from agencies.serializers import AgencySerializer
from accounts.serializers import UserSerializer


class MutamerDocumentSerializer(serializers.ModelSerializer):
    """Serializer for mutamer documents"""
    
    class Meta:
        model = MutamerDocument
        fields = ['id', 'document_type', 'file', 'uploaded_at']


class MutamerListSerializer(serializers.ModelSerializer):
    """Serializer for mutamer list views with basic information"""
    agency_name = serializers.CharField(source='agency.name', read_only=True)
    agent_name = serializers.CharField(source='agent.get_full_name', read_only=True)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Mutamer
        fields = [
            'id', 'name', 'passport_number', 'visa_number', 'nationality', 'gender', 'person_type',
            'date_of_birth', 'phone', 'email', 'city', 'state', 'country',
            'is_active', 'family_id', 'is_family_head', 'family_head_name',
            'agency_name', 'agent_name', 'age', 'created_at', 'updated_at'
        ]
    
    def get_age(self, obj):
        from datetime import date
        if not obj.date_of_birth:
            return None
        today = date.today()
        return today.year - obj.date_of_birth.year - ((today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day))
    


class MutamerDetailSerializer(serializers.ModelSerializer):
    """Serializer for mutamer detail views with full information"""
    agency = AgencySerializer(read_only=True)
    agent = UserSerializer(read_only=True)
    documents = MutamerDocumentSerializer(many=True, read_only=True)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Mutamer
        fields = [
            'id', 'name', 'passport_number', 'visa_number', 'nationality', 'gender', 'person_type',
            'date_of_birth', 'phone', 'email', 'emergency_contact',
            'emergency_phone', 'address', 'city', 'state', 'country',
            'postal_code', 'photo', 'passport_copy', 'visa_copy', 'notes',
            'is_active', 'family_id', 'is_family_head', 'family_head_name',
            'agency', 'agent', 'documents', 'age', 'created_at', 'updated_at'
        ]
    
    def get_age(self, obj):
        from datetime import date
        if not obj.date_of_birth:
            return None
        today = date.today()
        return today.year - obj.date_of_birth.year - ((today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day))


class MutamerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating mutamers"""
    
    class Meta:
        model = Mutamer
        fields = [
            'name', 'passport_number', 'visa_number', 'nationality', 'gender', 'person_type',
            'date_of_birth', 'phone', 'email', 'emergency_contact',
            'emergency_phone', 'address', 'city', 'state', 'country',
            'postal_code', 'photo', 'passport_copy', 'visa_copy', 'notes', 'is_active',
            'family_id', 'is_family_head', 'family_head_name'
        ]
    
    def validate_passport_number(self, value):
        """Ensure passport number is unique"""
        if Mutamer.objects.filter(passport_number=value).exists():
            raise serializers.ValidationError("Passport number must be unique.")
        return value
    
    def validate(self, data):
        """Validate mutamer data"""
        from datetime import date
        
        # Age check only for adults if DOB provided
        if 'date_of_birth' in data and data['date_of_birth'] and data.get('person_type', 'adult') == 'adult':
            today = date.today()
            age = today.year - data['date_of_birth'].year - ((today.month, today.day) < (data['date_of_birth'].month, data['date_of_birth'].day))
            
            if age < 18:
                raise serializers.ValidationError("Mutamer must be at least 18 years old.")
        
        return data
    
    def create(self, validated_data):
        """Create mutamer with agency and agent context"""
        validated_data['agency'] = self.context['request'].user.agency
        validated_data['agent'] = self.context['request'].user
        return super().create(validated_data)


class MutamerUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating mutamers"""
    
    class Meta:
        model = Mutamer
        fields = [
            'name', 'passport_number', 'visa_number', 'nationality', 'gender', 'person_type',
            'date_of_birth', 'phone', 'email', 'emergency_contact',
            'emergency_phone', 'address', 'city', 'state', 'country',
            'postal_code', 'photo', 'passport_copy', 'visa_copy', 'notes', 'is_active',
            'family_id', 'is_family_head', 'family_head_name'
        ]
    
    def validate_passport_number(self, value):
        """Ensure passport number is unique"""
        instance = self.instance
        if Mutamer.objects.filter(passport_number=value).exclude(id=instance.id).exists():
            raise serializers.ValidationError("Passport number must be unique.")
        return value
    
    def validate(self, data):
        """Validate mutamer data"""
        if 'date_of_birth' in data and data['date_of_birth'] and data.get('person_type', 'adult') == 'adult':
            from datetime import date
            today = date.today()
            age = today.year - data['date_of_birth'].year - ((today.month, today.day) < (data['date_of_birth'].month, data['date_of_birth'].day))
            
            if age < 18:
                raise serializers.ValidationError("Mutamer must be at least 18 years old.")
        
        return data


class MutamerDocumentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating mutamer documents"""
    
    class Meta:
        model = MutamerDocument
        fields = ['document_type', 'file']
    
    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB.")
        
        # Check file type
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
        if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError("File type not allowed. Allowed types: PDF, JPG, PNG, DOC, DOCX")
        
        return value
    
    def create(self, validated_data):
        """Create document with mutamer context"""
        mutamer_id = self.context['mutamer_id']
        validated_data['mutamer_id'] = mutamer_id
        return super().create(validated_data)


class MutamerSearchSerializer(serializers.Serializer):
    """Serializer for mutamer search results"""
    mutamer_id = serializers.IntegerField()
    name = serializers.CharField()
    passport_number = serializers.CharField()
    nationality = serializers.CharField()
    gender = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField()
    city = serializers.CharField()
    state = serializers.CharField()
    country = serializers.CharField()
    age = serializers.IntegerField()
    is_active = serializers.BooleanField()
    agent_name = serializers.CharField()


class MutamerStatsSerializer(serializers.Serializer):
    """Serializer for mutamer statistics"""
    total_mutamers = serializers.IntegerField()
    active_mutamers = serializers.IntegerField()
    by_gender = serializers.DictField()
    by_nationality = serializers.DictField()
    by_age_group = serializers.DictField()
    recent_additions = serializers.IntegerField()
