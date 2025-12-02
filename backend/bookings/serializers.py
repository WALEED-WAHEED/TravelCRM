from rest_framework import serializers
from django.utils import timezone
from .models import (
    Booking, BookingHotel, BookingFlight, BookingTransport, 
    BookingMutamer, BookingContact, BookingTeamContact, BookingPayment
)
from mutamers.serializers import MutamerListSerializer
from agencies.serializers import AgencySerializer
from accounts.serializers import UserSerializer


# BookingServiceSerializer removed - using separate models for hotels, flights, transports


class BookingPaymentSerializer(serializers.ModelSerializer):
    """Serializer for booking payments"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = BookingPayment
        fields = [
            'id', 'amount', 'payment_method', 'payment_date',
            'reference_number', 'notes', 'created_by_name'
        ]
        read_only_fields = ['payment_date', 'created_by']


class BookingListSerializer(serializers.ModelSerializer):
    """Serializer for booking list views with basic information"""
    mutamer_name = serializers.CharField(source='mutamer.name', read_only=True)
    agent_name = serializers.CharField(source='agent.get_full_name', read_only=True)
    balance_amount = serializers.ReadOnlyField()
    payment_count = serializers.SerializerMethodField()
    service_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'mutamer_name',
            'agent_name', 'booking_date', 'travel_date', 'return_date',
            'status', 'payment_status', 'total_amount', 'paid_amount',
            'balance_amount', 'currency', 'payment_count', 'service_count',
            'created_at', 'updated_at'
        ]
    
    def get_payment_count(self, obj):
        return obj.payments.count()
    
    def get_service_count(self, obj):
        return obj.services.count()


class BookingDetailSerializer(serializers.ModelSerializer):
    """Serializer for booking detail views with full information"""
    mutamer = MutamerListSerializer(read_only=True)
    agent = UserSerializer(read_only=True)
    agency = AgencySerializer(read_only=True)
    # services removed - using separate models for hotels, flights, transports
    payments = BookingPaymentSerializer(many=True, read_only=True)
    balance_amount = serializers.ReadOnlyField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'mutamer', 'agent', 'agency',
            'booking_date', 'travel_date', 'return_date', 'status', 'payment_status',
            'total_amount', 'paid_amount', 'balance_amount', 'currency',
            'special_requests', 'notes', 'services', 'payments',
            'created_at', 'updated_at'
        ]


class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bookings"""
    # Related data from frontend
    hotels = serializers.ListField(child=serializers.DictField(), required=False)
    outbound_flight_id = serializers.IntegerField(required=False, allow_null=True)
    return_flight_id = serializers.IntegerField(required=False, allow_null=True)
    transports = serializers.ListField(child=serializers.DictField(), required=False)
    mutamers = serializers.ListField(child=serializers.IntegerField(), required=False)
    contacts = serializers.ListField(child=serializers.IntegerField(), required=False)
    makkah_team = serializers.ListField(child=serializers.DictField(), required=False)
    medina_team = serializers.ListField(child=serializers.DictField(), required=False)
    special_instructions = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Booking
        fields = [
            'voucher_number', 'manual_number', 'package_name',
            'client_company', 'client_country', 'client_whatsapp',
            'pax_adults', 'pax_children', 'pax_infants', 'total_beds',
            'status', 'total_price', 'notes',
            'hotels', 'outbound_flight_id', 'return_flight_id', 'transports',
            'mutamers', 'contacts', 'makkah_team', 'medina_team', 'special_instructions'
        ]
    
    def validate(self, data):
        """Validate booking data"""
        # Ensure total_price is provided and valid
        total_price = data.get('total_price', 0)
        if total_price is None:
            raise serializers.ValidationError({"total_price": "Total price is required."})
        if total_price < 0:
            raise serializers.ValidationError({"total_price": "Total price cannot be negative."})
        
        # Ensure voucher_number is provided
        voucher_number = data.get('voucher_number')
        if not voucher_number:
            raise serializers.ValidationError({"voucher_number": "Voucher number is required."})
        
        # Check for duplicate voucher number (exclude current booking if updating)
        if voucher_number:
            query = Booking.objects.filter(voucher_number=voucher_number)
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise serializers.ValidationError({"voucher_number": f"A booking with voucher number {voucher_number} already exists."})
        
        return data
    
    def create(self, validated_data):
        """Create booking with agency and agent context and related objects"""
        # Extract related data
        hotels_data = validated_data.pop('hotels', [])
        outbound_flight_id = validated_data.pop('outbound_flight_id', None)
        return_flight_id = validated_data.pop('return_flight_id', None)
        transports_data = validated_data.pop('transports', [])
        mutamers_data = validated_data.pop('mutamers', [])
        contacts_data = validated_data.pop('contacts', [])
        makkah_team_data = validated_data.pop('makkah_team', [])
        medina_team_data = validated_data.pop('medina_team', [])
        special_instructions = validated_data.pop('special_instructions', '')
        
        # Map total_price to total_amount for database compatibility
        # The database still has total_amount column from the old schema
        total_price_value = validated_data.pop('total_price', 0) or 0
        # Set total_amount which is required by the database
        validated_data['total_amount'] = total_price_value
        # Also set total_price (both fields exist in the model now)
        validated_data['total_price'] = total_price_value
        
        # Add special instructions to notes if provided
        if special_instructions:
            validated_data['notes'] = f"{validated_data.get('notes', '')}\nSpecial Instructions: {special_instructions}".strip()
        
        # Create booking
        validated_data['agency'] = self.context['request'].user.agency
        validated_data['agent'] = self.context['request'].user
        booking = Booking.objects.create(**validated_data)
        
        # Create related hotels
        for hotel_data in hotels_data:
            from hotels.models import Hotel
            try:
                hotel = Hotel.objects.get(id=hotel_data.get('id'))
                BookingHotel.objects.create(
                    booking=booking,
                    hotel=hotel,
                    city=hotel_data.get('city', ''),
                    hotel_name=hotel_data.get('hotel_name', ''),
                    view=hotel_data.get('view', 'Standard'),
                    meal_plan=hotel_data.get('meal_plan', 'RO'),
                    confirmation_number=hotel_data.get('confirmation_number', ''),
                    room_type=hotel_data.get('room_type', 'sharing'),
                    check_in=hotel_data.get('check_in'),
                    check_out=hotel_data.get('check_out'),
                    nights=hotel_data.get('nights', 1)
                )
            except Hotel.DoesNotExist:
                pass  # Skip invalid hotel IDs
        
        # Create related flights
        from flights.models import Flight
        if outbound_flight_id:
            try:
                outbound_flight = Flight.objects.get(id=outbound_flight_id)
                BookingFlight.objects.create(
                    booking=booking,
                    flight=outbound_flight,
                    flight_type='outbound'
                )
            except Flight.DoesNotExist:
                pass
        if return_flight_id:
            try:
                return_flight = Flight.objects.get(id=return_flight_id)
                BookingFlight.objects.create(
                    booking=booking,
                    flight=return_flight,
                    flight_type='return'
                )
            except Flight.DoesNotExist:
                pass
        
        # Create related transports
        for transport_data in transports_data:
            from transports.models import Transport
            try:
                transport = Transport.objects.get(id=transport_data.get('id'))
                BookingTransport.objects.create(
                    booking=booking,
                    transport=transport,
                    travel_date=transport_data.get('travel_date'),
                    transporter=transport_data.get('transporter', ''),
                    vehicle_type=transport_data.get('vehicle_type', ''),
                    description=transport_data.get('description', '')
                )
            except Transport.DoesNotExist:
                pass
        
        # Create related mutamers
        from mutamers.models import Mutamer
        for mutamer_id in mutamers_data:
            try:
                mutamer = Mutamer.objects.get(id=mutamer_id)
                BookingMutamer.objects.create(booking=booking, mutamer=mutamer)
            except Mutamer.DoesNotExist:
                pass
        
        # Create related contacts
        from contacts.models import Contact
        for contact_id in contacts_data:
            try:
                contact = Contact.objects.get(id=contact_id)
                BookingContact.objects.create(booking=booking, contact=contact)
            except Contact.DoesNotExist:
                pass
        
        # Create team contacts
        for team_contact in makkah_team_data:
            BookingTeamContact.objects.create(
                booking=booking,
                team='makkah',
                role=team_contact.get('role', ''),
                name=team_contact.get('name', ''),
                phone=team_contact.get('phone', '')
            )
        for team_contact in medina_team_data:
            BookingTeamContact.objects.create(
                booking=booking,
                team='medina',
                role=team_contact.get('role', ''),
                name=team_contact.get('name', ''),
                phone=team_contact.get('phone', '')
            )
        
        return booking


class BookingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating bookings"""
    # services removed - using separate models
    
    class Meta:
        model = Booking
        fields = [
            'mutamer', 'travel_date', 'return_date',
            'status', 'payment_status', 'total_amount', 'paid_amount',
            'currency', 'special_requests', 'notes', 'services'
        ]
    
    def validate(self, data):
        """Validate booking data"""
        if 'travel_date' in data and data['travel_date'] < timezone.now().date():
            raise serializers.ValidationError("Travel date cannot be in the past.")
        
        if 'return_date' in data and data['return_date']:
            travel_date = data.get('travel_date', self.instance.travel_date)
            if data['return_date'] <= travel_date:
                raise serializers.ValidationError("Return date must be after travel date.")
        
        if 'total_amount' in data and data['total_amount'] <= 0:
            raise serializers.ValidationError("Total amount must be positive.")
        
        if 'paid_amount' in data and data['paid_amount'] < 0:
            raise serializers.ValidationError("Paid amount cannot be negative.")
        
        total_amount = data.get('total_amount', self.instance.total_amount)
        paid_amount = data.get('paid_amount', self.instance.paid_amount)
        
        if paid_amount > total_amount:
            raise serializers.ValidationError("Paid amount cannot exceed total amount.")
        
        return data
    
    def update(self, instance, validated_data):
        """Update booking with services"""
        services_data = validated_data.pop('services', None)
        
        # Update booking fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update services if provided
        if services_data is not None:
            # Delete existing services
            instance.services.all().delete()
            # Create new services
            for service_data in services_data:
                BookingService.objects.create(booking=instance, **service_data)
        
        return instance


class BookingPaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating booking payments"""
    
    class Meta:
        model = BookingPayment
        fields = ['amount', 'payment_method', 'reference_number', 'notes']
    
    def validate_amount(self, value):
        """Validate payment amount"""
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be positive.")
        return value
    
    def create(self, validated_data):
        """Create payment with booking context"""
        booking_id = self.context['booking_id']
        booking = Booking.objects.get(id=booking_id)
        
        # Check if payment exceeds balance
        new_balance = booking.balance_amount - validated_data['amount']
        if new_balance < 0:
            raise serializers.ValidationError("Payment amount exceeds booking balance.")
        
        validated_data['booking_id'] = booking_id
        validated_data['created_by'] = self.context['request'].user
        payment = BookingPayment.objects.create(**validated_data)
        
        # Update booking paid amount
        booking.paid_amount += validated_data['amount']
        if booking.paid_amount >= booking.total_amount:
            booking.payment_status = 'paid'
        elif booking.paid_amount > 0:
            booking.payment_status = 'partial'
        booking.save()
        
        return payment


# BookingServiceCreateSerializer removed - using separate models


class BookingStatsSerializer(serializers.Serializer):
    """Serializer for booking statistics"""
    total_bookings = serializers.IntegerField()
    confirmed_bookings = serializers.IntegerField()
    cancelled_bookings = serializers.IntegerField()
    completed_bookings = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    recent_bookings = serializers.IntegerField()


class BookingSummarySerializer(serializers.Serializer):
    """Serializer for booking summary"""
    booking_id = serializers.IntegerField()
    booking_number = serializers.CharField()
    mutamer_name = serializers.CharField()
    travel_date = serializers.DateField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    status = serializers.CharField()
    payment_status = serializers.CharField()
    balance_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
