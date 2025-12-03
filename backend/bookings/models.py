from django.db import models
from django.conf import settings
from agencies.models import Agency

User = settings.AUTH_USER_MODEL


class VoucherSequence(models.Model):
    """Track voucher number sequences per agency"""
    agency = models.OneToOneField(Agency, on_delete=models.CASCADE, related_name='voucher_sequence')
    current_sequence = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_next_voucher_number(self):
        """Generate next voucher number for this agency"""
        # Extract company name prefix
        company_name = self.agency.name.replace(' ', '').replace('.', '').replace(',', '')
        prefix = company_name[:4].upper() if company_name else 'V'
        
        # Format: PREFIX-000001
        return f"{prefix}-{(self.current_sequence + 1):06d}"
    
    def increment_and_get_next(self):
        """Increment sequence and generate next voucher number"""
        self.current_sequence += 1
        self.save()
        
        # Extract company name prefix
        company_name = self.agency.name.replace(' ', '').replace('.', '').replace(',', '')
        prefix = company_name[:4].upper() if company_name else 'V'
        
        # Format: PREFIX-000001
        return f"{prefix}-{self.current_sequence:06d}"

    def __str__(self):
        return f"Voucher sequence for {self.agency.name}: {self.current_sequence}"

    class Meta:
        ordering = ['agency__name']


class Booking(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    # Basic booking info
    voucher_number = models.CharField(max_length=50, unique=True)
    manual_number = models.CharField(max_length=50, blank=True)
    package_name = models.CharField(max_length=200, blank=True)
    
    # Client info
    client_company = models.CharField(max_length=200, blank=True)
    client_country = models.CharField(max_length=100, blank=True)
    client_whatsapp = models.CharField(max_length=20, blank=True)
    
    # PAX info
    pax_adults = models.PositiveIntegerField(default=0)
    pax_children = models.PositiveIntegerField(default=0)
    pax_infants = models.PositiveIntegerField(default=0)
    total_beds = models.PositiveIntegerField(default=0)
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    # Keep both total_amount (for database compatibility) and total_price (for new schema)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    # Relationships
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='bookings')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking {self.voucher_number} - {self.client_company}"

    class Meta:
        ordering = ['-created_at']


class BookingHotel(models.Model):
    """Hotels selected for a booking"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='hotels')
    hotel = models.ForeignKey('hotels.Hotel', on_delete=models.CASCADE)
    
    # Booking-specific details
    city = models.CharField(max_length=100)
    hotel_name = models.CharField(max_length=200)
    view = models.CharField(max_length=100, default='Standard')
    meal_plan = models.CharField(max_length=10, default='RO')
    confirmation_number = models.CharField(max_length=100, blank=True)
    room_type = models.CharField(max_length=50, default='sharing')
    check_in = models.DateField()
    check_out = models.DateField()
    nights = models.PositiveIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.hotel_name}"

    class Meta:
        ordering = ['check_in']


class BookingFlight(models.Model):
    """Flights selected for a booking"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='flights')
    flight = models.ForeignKey('flights.Flight', on_delete=models.CASCADE)
    flight_type = models.CharField(max_length=20, choices=[
        ('outbound', 'Outbound'),
        ('return', 'Return'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.flight.airline} {self.flight.flight_number}"

    class Meta:
        ordering = ['flight_type']


class BookingTransport(models.Model):
    """Transports selected for a booking"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='transports')
    transport = models.ForeignKey('transports.Transport', on_delete=models.CASCADE)
    
    # Booking-specific details
    travel_date = models.DateField()
    transporter = models.CharField(max_length=200)
    vehicle_type = models.CharField(max_length=100)
    description = models.CharField(max_length=300)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.transporter}"

    class Meta:
        ordering = ['travel_date']


class BookingMutamer(models.Model):
    """Mutamers selected for a booking"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booking_mutamers')
    mutamer = models.ForeignKey('mutamers.Mutamer', on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.mutamer.name}"

    class Meta:
        ordering = ['mutamer__name']


class BookingContact(models.Model):
    """Contacts selected for a booking"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booking_contacts')
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.contact.name}"

    class Meta:
        ordering = ['contact__name']


class BookingTeamContact(models.Model):
    """Team contacts for a booking"""
    TEAM_CHOICES = [
        ('makkah', 'Makkah Team'),
        ('medina', 'Medina Team'),
    ]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='team_contacts')
    team = models.CharField(max_length=20, choices=TEAM_CHOICES)
    role = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.team.title()} {self.name}"

    class Meta:
        ordering = ['team', 'role']


class BookingPayment(models.Model):
    """Payment records for bookings"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Relationships
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booking_payments')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.amount} for {self.booking.voucher_number}"

    class Meta:
        ordering = ['-created_at']