import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from agencies.models import Agency

User = settings.AUTH_USER_MODEL

# ==========================================
# HOTELS
# ==========================================

class Hotel(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], blank=True, null=True)  # 1-5 stars
    description = models.TextField(blank=True, null=True)
    amenities = models.JSONField(default=list, blank=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='hotels')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='hotels_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.city}"

    def save(self, *args, **kwargs):
        if not (self.code and str(self.code).strip()):
            base = (slugify(self.name or "") or "hotel")[:24]
            for _ in range(24):
                cand = f"{base}-{uuid.uuid4().hex[:6].upper()}"
                cand = cand[:50]
                if not Hotel.objects.filter(code=cand).exclude(pk=self.pk).exists():
                    self.code = cand
                    break
            else:
                self.code = f"H-{uuid.uuid4().hex[:12].upper()}"[:50]
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']

class HotelRoom(models.Model):
    ROOM_TYPES = [
        ('single', 'Single'),
        ('double', 'Double'),
        ('triple', 'Triple'),
        ('quad', 'Quad'),
        ('suite', 'Suite'),
    ]
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.IntegerField()
    available_rooms = models.IntegerField()
    amenities = models.JSONField(default=list)
    
    def __str__(self):
        return f"{self.hotel.name} - {self.room_type}"

class HotelImage(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='hotels/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.hotel.name} - Image"

# ==========================================
# FLIGHTS
# ==========================================

class Flight(models.Model):
    FLIGHT_CLASS = [
        ('economy', 'Economy'),
        ('business', 'Business'),
        ('first', 'First Class'),
    ]
    FLIGHT_TYPE_CHOICES = [
        ('one_way', 'One Way'),
        ('return', 'Return'),
        ('multi_city', 'Multi-City'),
    ]
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('delayed', 'Delayed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    flight_type = models.CharField(max_length=20, choices=FLIGHT_TYPE_CHOICES, default='one_way')
    airline = models.CharField(max_length=100)
    flight_number = models.CharField(max_length=20, blank=True, null=True)
    pnr_number = models.CharField(max_length=20, blank=True, null=True)
    departure_airport = models.CharField(max_length=10, default='N/A')
    arrival_airport = models.CharField(max_length=10, default='N/A')
    departure_city = models.CharField(max_length=100)
    arrival_city = models.CharField(max_length=100)
    departure_country = models.CharField(max_length=100, default='N/A')
    arrival_country = models.CharField(max_length=100, default='N/A')
    flight_class = models.CharField(max_length=20, choices=FLIGHT_CLASS, default='economy')
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='PKR')
    available_seats = models.IntegerField(default=0)
    total_seats = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    baggage_allowance = models.CharField(max_length=100, default='N/A')
    meal_included = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='flights')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='flights_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.airline} {self.flight_number} - {self.departure_city} to {self.arrival_city}"
    
    class Meta:
        ordering = ['-created_at']

class FlightSegment(models.Model):
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='segments')
    segment_number = models.PositiveIntegerField()
    departure_city = models.CharField(max_length=100)
    arrival_city = models.CharField(max_length=100)
    departure_airport = models.CharField(max_length=10, default='N/A')
    arrival_airport = models.CharField(max_length=10, default='N/A')
    departure_country = models.CharField(max_length=100, default='N/A')
    arrival_country = models.CharField(max_length=100, default='N/A')
    flight_number = models.CharField(max_length=20, blank=True, null=True)
    airline = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['segment_number']
        unique_together = ['flight', 'segment_number']
    
    def __str__(self):
        return f"Segment {self.segment_number}: {self.departure_city} → {self.arrival_city}"

# ==========================================
# TRANSPORTS
# ==========================================

class Transport(models.Model):
    TRANSPORT_TYPES = [
        ('bus', 'Bus'),
        ('car', 'Car'),
        ('van', 'Van'),
        ('coach', 'Coach'),
        ('train', 'Train'),
        ('other', 'Other'),
    ]
    name = models.CharField(max_length=200)
    transport_type = models.CharField(max_length=20, choices=TRANSPORT_TYPES)
    capacity = models.IntegerField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amenities = models.JSONField(default=list)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='transports')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transports_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.transport_type}) - {self.agency}"
    
    class Meta:
        ordering = ['-created_at']

# ==========================================
# ATTENDANCE
# ==========================================

class AttendanceLog(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('leave', 'Leave'),
    ]
    # Attendance can be tracked for agency staff even if they don't have a user account.
    # If a user exists, link it; otherwise store a typed name in person_name.
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_logs')
    person_name = models.CharField(max_length=200)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='attendance_logs')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    work_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        label = self.person_name or (self.user.username if self.user_id else "Unknown")
        return f"{label} - {self.date} ({self.status})"
    
    class Meta:
        unique_together = ['agency', 'person_name', 'date']
        ordering = ['-date', '-created_at']

# ==========================================
# CONTACTS
# ==========================================

class Contact(models.Model):
    CONTACT_TYPES = [
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        ('partner', 'Partner'),
        ('vendor', 'Vendor'),
        ('other', 'Other'),
    ]
    name = models.CharField(max_length=200)
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPES)
    company = models.CharField(max_length=200, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='contacts')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='contacts_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.contact_type})"
    
    class Meta:
        ordering = ['-created_at']

class ContactInstruction(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="contact_instructions")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contact_instructions_created")
    city = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.city} - {self.role} ({self.contact_name})"

# ==========================================
# MUTAMERS
# ==========================================

class Mutamer(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    PERSON_TYPE_CHOICES = [
        ('adult', 'Adult'),
        ('child', 'Child'),
        ('infant', 'Infant'),
    ]
    name = models.CharField(max_length=200)
    passport_number = models.CharField(max_length=50, unique=True)
    visa_number = models.CharField(max_length=50, blank=True, null=True)
    nationality = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    person_type = models.CharField(max_length=10, choices=PERSON_TYPE_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    emergency_contact = models.CharField(max_length=200, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='mutamers/photos/', null=True, blank=True)
    passport_copy = models.FileField(upload_to='mutamers/documents/', null=True, blank=True)
    visa_copy = models.FileField(upload_to='mutamers/documents/', null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    family_id = models.CharField(max_length=100, blank=True, null=True, help_text="Unique identifier for family group")
    is_family_head = models.BooleanField(default=False, help_text="Whether this mutamer is the head of the family")
    family_head_name = models.CharField(max_length=200, blank=True, null=True, help_text="Name of the family head")
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mutamers')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='mutamers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.passport_number})"
    
    class Meta:
        ordering = ['-created_at']

class MutamerDocument(models.Model):
    mutamer = models.ForeignKey(Mutamer, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50)
    file = models.FileField(upload_to='mutamers/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.mutamer.name} - {self.document_type}"

# ==========================================
# BOOKINGS
# ==========================================

class VoucherSequence(models.Model):
    agency = models.OneToOneField(Agency, on_delete=models.CASCADE, related_name='voucher_sequence')
    current_sequence = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_next_voucher_number(self):
        company_name = self.agency.name.replace(' ', '').replace('.', '').replace(',', '')
        prefix = company_name[:4].upper() if company_name else 'V'
        return f"{prefix}-{(self.current_sequence + 1):06d}"
    
    def increment_and_get_next(self):
        self.current_sequence += 1
        self.save()
        company_name = self.agency.name.replace(' ', '').replace('.', '').replace(',', '')
        prefix = company_name[:4].upper() if company_name else 'V'
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
    voucher_number = models.CharField(max_length=50, unique=True)
    manual_number = models.CharField(max_length=50, blank=True)
    package_name = models.CharField(max_length=200, blank=True)
    client_company = models.CharField(max_length=200, blank=True)
    client_country = models.CharField(max_length=100, blank=True)
    client_whatsapp = models.CharField(max_length=20, blank=True)
    pax_adults = models.PositiveIntegerField(default=0)
    pax_children = models.PositiveIntegerField(default=0)
    pax_infants = models.PositiveIntegerField(default=0)
    total_beds = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='bookings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking {self.voucher_number} - {self.client_company}"

    class Meta:
        ordering = ['-created_at']

class BookingHotel(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='hotels')
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
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
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='flights')
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE)
    flight_type = models.CharField(max_length=20, choices=[('outbound', 'Outbound'), ('return', 'Return')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.flight.airline} {self.flight.flight_number}"
    
    class Meta:
        ordering = ['flight_type']

class BookingTransport(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='transports')
    transport = models.ForeignKey(Transport, on_delete=models.CASCADE)
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
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booking_mutamers')
    mutamer = models.ForeignKey(Mutamer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.mutamer.name}"
    
    class Meta:
        ordering = ['mutamer__name']

class BookingContact(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booking_contacts')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.contact.name}"
    
    class Meta:
        ordering = ['contact__name']


class BookingContactInstruction(models.Model):
    """Links a booking voucher to saved contact instructions (contacts page)."""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booking_instructions')
    instruction = models.ForeignKey(ContactInstruction, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.instruction}"

    class Meta:
        unique_together = [['booking', 'instruction']]
        ordering = ['instruction__city', 'instruction__role', 'instruction__contact_name']


class BookingTeamContact(models.Model):
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
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booking_payments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.amount} for {self.booking.voucher_number}"
    
    class Meta:
        ordering = ['-created_at']

# ==========================================
# VOUCHERS
# ==========================================

class Voucher(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    voucher_number = models.CharField(max_length=50, unique=True, blank=True)
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vouchers_created')
    mutamer = models.ForeignKey(Mutamer, on_delete=models.CASCADE, related_name='vouchers')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vouchers_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    public_token = models.CharField(max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def balance_amount(self):
        return self.total_amount - self.paid_amount
    
    def save(self, *args, **kwargs):
        if not self.voucher_number:
            self.voucher_number = f"V-{uuid.uuid4().hex[:8].upper()}"
        if not self.public_token:
            self.public_token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Voucher {self.voucher_number} ({self.status})"
    
    class Meta:
        ordering = ['-created_at']

class VoucherService(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='services')
    service_type = models.CharField(max_length=20)
    service_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)
    
    @property
    def total(self):
        return self.amount * self.quantity
    
    def __str__(self):
        return f"{self.voucher.voucher_number} - {self.service_name}"

# ==========================================
# LEDGER
# ==========================================

class LedgerEntry(models.Model):
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('booking', 'Booking'),
        ('voucher', 'Voucher'),
        ('refund', 'Refund'),
        ('commission', 'Commission'),
        ('other', 'Other'),
    ]
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
    ]
    transaction_date = models.DateField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    # Ledger organization (party accounts + expenses)
    ENTRY_BUCKETS = [
        ("lein_dein", "Party accounts (People/Companies)"),
        ("company_expense", "Company expense"),
    ]
    ENTRY_DIRECTIONS = [
        ("debit", "Debit (Paid / Given)"),
        ("credit", "Credit (Received / Taken)"),
    ]
    bucket = models.CharField(max_length=30, choices=ENTRY_BUCKETS, default="company_expense")
    direction = models.CharField(max_length=10, choices=ENTRY_DIRECTIONS, default="debit")
    counterparty_type = models.CharField(max_length=20, blank=True)  # person / company / other (free-form for now)
    counterparty_name = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='PKR')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(max_length=100, blank=True)
    trans_no = models.CharField(max_length=100, blank=True)  # Trans.#
    inv_ref = models.CharField(max_length=100, blank=True)   # Inv/Ref
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    voucher = models.ForeignKey(Voucher, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='ledger_entries')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ledger_entries_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.agency.name})"
    
    class Meta:
        verbose_name_plural = 'Ledger Entries'
        ordering = ['-transaction_date', '-created_at']
