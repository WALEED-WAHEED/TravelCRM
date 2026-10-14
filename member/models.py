import datetime
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from agencies.models import Agency
from travelcrm.languages import SUPPORTED_LANGUAGES
from utils.tenancy import TenantManager, UnscopedManager

User = settings.AUTH_USER_MODEL

# ==========================================
# HOTELS
# ==========================================

class Hotel(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
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
    supplier = models.ForeignKey(
        'Contact', on_delete=models.SET_NULL, null=True, blank=True, related_name='hotels_supplied',
        help_text="Who this is purchased from — drives the supplier payables dashboard.",
    )
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='hotels')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='hotels_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"{self.name} - {self.city}"

    def save(self, *args, **kwargs):
        if not (self.code and str(self.code).strip()):
            base = (slugify(self.name or "") or "hotel")[:24]
            for _ in range(24):
                cand = f"{base}-{uuid.uuid4().hex[:6].upper()}"
                cand = cand[:50]
                if not Hotel.all_tenants.filter(agency_id=self.agency_id, code=cand).exclude(pk=self.pk).exists():
                    self.code = cand
                    break
            else:
                self.code = f"H-{uuid.uuid4().hex[:12].upper()}"[:50]
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
        base_manager_name = 'all_tenants'
        constraints = [
            models.UniqueConstraint(fields=['agency', 'code'], name='member_hotel_unique_code_per_agency'),
        ]

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


def _airport_code(code, city):
    """An airport code if it's a real one, otherwise the city ("N/A" or blank codes are ignored)."""
    code = (code or "").strip()
    return code if code and code.upper() not in ("N/A", "NA", "-", "—") else (city or "").strip()


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
    supplier = models.ForeignKey(
        'Contact', on_delete=models.SET_NULL, null=True, blank=True, related_name='flights_supplied',
        help_text="Who this is purchased from — drives the supplier payables dashboard.",
    )
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

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"{self.airline} {self.flight_number} - {self.departure_city} to {self.arrival_city}"

    class Meta:
        ordering = ['-created_at']
        base_manager_name = 'all_tenants'

    @property
    def sector(self):
        a = _airport_code(self.departure_airport, self.departure_city)
        b = _airport_code(self.arrival_airport, self.arrival_city)
        return f"{a}-{b}" if a or b else ""

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
    supplier = models.ForeignKey(
        'Contact', on_delete=models.SET_NULL, null=True, blank=True, related_name='transports_supplied',
        help_text="Who this is purchased from — drives the supplier payables dashboard.",
    )
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='transports')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transports_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"{self.name} ({self.transport_type}) - {self.agency}"

    class Meta:
        ordering = ['-created_at']
        base_manager_name = 'all_tenants'

# ==========================================
# PACKAGES
# ==========================================

class Package(models.Model):
    """A ready-made Umrah/Hajj/tour offer built from inventory, priced per
    person by room sharing (the way Pakistani Umrah packages are sold)."""
    PACKAGE_TYPES = [
        ('umrah', _('Umrah')),
        ('hajj', _('Hajj')),
        ('ziyarat', _('Ziyarat')),
        ('tour', _('Tour')),
        ('other', _('Other')),
    ]
    INCLUSIONS = [
        ('visa', _('Visa')),
        ('ticket', _('Air ticket')),
        ('hotel', _('Hotel')),
        ('transport', _('Transport')),
        ('ziyarat', _('Ziyarat')),
        ('meals', _('Meals')),
        ('insurance', _('Insurance')),
        ('taif', _('Umrah from Taif')),
        ('refreshments', _('Refreshments during Ziyarat')),
        ('ihram', _('Ihram')),
        ('scarf', _('Scarf')),
        ('shoe_bag', _('Shoe bag')),
        ('zamzam', _('5-litre Zamzam water')),
        ('card_holder', _('Card holder')),
        ('private_bus', _('Private luxury bus')),
        ('guide', _('Guide & group leader')),
        ('meet_greet', _('Meet & greet / airport assistance')),
    ]
    # Room-sharing price fields, in display order.
    SHARING_FIELDS = [
        ('price_sharing', _('Sharing')),
        ('price_double', _('Double')),
        ('price_triple', _('Triple')),
        ('price_quad', _('Quad')),
        ('price_quint', _('Quint')),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True, help_text="Package code, e.g. UP-100252 (assigned automatically).")
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPES, default='umrah')
    group_leader = models.CharField(max_length=150, blank=True)
    makkah_nights = models.PositiveIntegerField(default=0)
    madina_nights = models.PositiveIntegerField(default=0)
    makkah_hotel = models.ForeignKey(Hotel, on_delete=models.SET_NULL, null=True, blank=True, related_name='packages_makkah')
    madina_hotel = models.ForeignKey(Hotel, on_delete=models.SET_NULL, null=True, blank=True, related_name='packages_madina')
    # Distance of each hotel from the Haram / Masjid-e-Nabawi, in metres, and whether a shuttle is needed.
    makkah_distance = models.PositiveIntegerField(null=True, blank=True)
    makkah_shuttle = models.BooleanField(default=False)
    madina_distance = models.PositiveIntegerField(null=True, blank=True)
    madina_shuttle = models.BooleanField(default=False)
    flight = models.ForeignKey(Flight, on_delete=models.SET_NULL, null=True, blank=True, related_name='packages')
    return_flight = models.ForeignKey(Flight, on_delete=models.SET_NULL, null=True, blank=True, related_name='packages_return')
    baggage = models.CharField(max_length=60, blank=True, help_text="e.g. 23 kg, or 23 + 23 kg")
    transport = models.ForeignKey(Transport, on_delete=models.SET_NULL, null=True, blank=True, related_name='packages')
    inclusions = models.JSONField(default=list, blank=True)
    extra_services = models.TextField(blank=True, help_text="Other services included, one per line.")
    price_sharing = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_child = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Child without bed")
    price_infant = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_double = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_triple = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_quad = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_quint = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Your cost per person — used to show margin.",
    )
    departure_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    total_seats = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='packages')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='packages_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    @property
    def total_nights(self):
        return self.makkah_nights + self.madina_nights

    @property
    def sharing_prices(self):
        """[(label, price)] for the sharing options that have a price."""
        return [(label, getattr(self, f)) for f, label in self.SHARING_FIELDS if getattr(self, f) is not None]

    @property
    def starting_price(self):
        prices = [p for _label, p in self.sharing_prices]
        return min(prices) if prices else None

    def get_inclusions_display(self):
        labels = dict(self.INCLUSIONS)
        return [labels[i] for i in self.inclusions if i in labels] + self.extra_services_list

    @property
    def extra_services_list(self):
        return [line.strip() for line in (self.extra_services or "").splitlines() if line.strip()]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"UP-{100000 + self.pk}"
            type(self).all_tenants.filter(pk=self.pk).update(code=self.code)

    def __str__(self):
        return f"{self.name} - {self.agency}"

    class Meta:
        ordering = ['-created_at']
        base_manager_name = 'all_tenants'

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
    SOURCE_CHOICES = [
        ('manual', _('Manual entry')),
        ('self', _('Self check-in')),
        ('field', _('Field check-in')),
        ('auto', _('Automatic')),
        ('correction', _('Approved correction')),
    ]
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    # Server-side timestamps for self check-in/out (never typed by staff), plus
    # what was verified: {"ip", "lat", "lng", "accuracy", "distance_m", "checks": {...}}.
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    check_in_meta = models.JSONField(default=dict, blank=True)
    check_out_meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        label = self.person_name or (self.user.username if self.user_id else "Unknown")
        return f"{label} - {self.date} ({self.status})"

    class Meta:
        unique_together = ['agency', 'person_name', 'date']
        ordering = ['-date', '-created_at']
        base_manager_name = 'all_tenants'


def _new_kiosk_token():
    import secrets
    return secrets.token_urlsafe(24)


def _default_work_days():
    return [0, 1, 2, 3, 4, 5]  # Mon-Sat


class AttendanceSettings(models.Model):
    """How self check-in is verified for one agency (see member/attendance.py)."""
    agency = models.OneToOneField(Agency, on_delete=models.CASCADE, related_name='attendance_settings')
    # Which checks office staff must pass to check in/out.
    require_network = models.BooleanField(default=False)
    require_qr = models.BooleanField(default=False)
    require_location = models.BooleanField(default=False)
    office_ips = models.JSONField(default=list, blank=True)  # public IPs of the office connection(s)
    office_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    office_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    radius_m = models.PositiveIntegerField(default=150)
    max_accuracy_m = models.PositiveIntegerField(
        default=150, help_text="Location readings vaguer than this are rejected.",
    )
    # Field staff (airport reps, Makkah/Madina team) check in with location only, anywhere.
    field_staff = models.ManyToManyField(User, blank=True, related_name='attendance_field_agencies')
    # Staff not expected to check in (e.g. the owner) — never auto-marked absent.
    exempt_staff = models.ManyToManyField(User, blank=True, related_name='attendance_exempt_agencies')
    # Office hours drive automatic Present / Late / Absent.
    workday_start = models.TimeField(default=datetime.time(9, 0))
    late_after_minutes = models.PositiveIntegerField(default=15)
    absent_after = models.TimeField(default=datetime.time(12, 0))
    workday_end = models.TimeField(default=datetime.time(18, 0))
    work_days = models.JSONField(default=_default_work_days, blank=True)  # 0=Mon … 6=Sun
    # Office hours are judged in the office's own timezone (the server runs in UTC).
    time_zone = models.CharField(max_length=64, default='Asia/Karachi')
    # Secret in the office-display link; rotating it invalidates the old link and its QR codes.
    kiosk_token = models.CharField(max_length=64, unique=True, default=_new_kiosk_token)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"Attendance settings - {self.agency}"

    class Meta:
        base_manager_name = 'all_tenants'
        verbose_name_plural = 'Attendance settings'


class AttendanceCorrection(models.Model):
    """A staff member's request to fix their own record — only a manager's approval changes it."""
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
    ]
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='attendance_corrections')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_corrections')
    date = models.DateField()
    requested_status = models.CharField(max_length=20, choices=AttendanceLog.STATUS_CHOICES)
    requested_check_in = models.TimeField(null=True, blank=True)
    requested_check_out = models.TimeField(null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_corrections_reviewed',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"Correction {self.user} {self.date} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        base_manager_name = 'all_tenants'

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
    preferred_language = models.CharField(
        max_length=10, choices=SUPPORTED_LANGUAGES, blank=True, null=True,
        help_text="Language this contact's notification emails are sent in. Blank falls back to English.",
    )
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='contacts')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='contacts_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"{self.name} ({self.contact_type})"

    class Meta:
        ordering = ['-created_at']
        base_manager_name = 'all_tenants'

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

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"{self.city} - {self.role} ({self.contact_name})"

    class Meta:
        base_manager_name = 'all_tenants'

class BookingNote(models.Model):
    """An internal note on one voucher: who wrote it and when. Never printed on the voucher."""
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="booking_notes")
    booking = models.ForeignKey("Booking", on_delete=models.CASCADE, related_name="voucher_notes")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="booking_notes_written")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return self.text[:60]

    class Meta:
        ordering = ["-created_at", "-id"]
        base_manager_name = "all_tenants"


class VoucherInstruction(models.Model):
    """General travel instructions printed, in order, at the end of every voucher
    (e.g. Haram rules, check-out times). Managed on the Contacts page."""
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="voucher_instructions")
    text = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="voucher_instructions_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return self.text[:60]

    class Meta:
        ordering = ["sort_order", "id"]
        base_manager_name = "all_tenants"


# ==========================================
# MUTAMERS
# ==========================================

# ==========================================
# BOOKINGS
# ==========================================

class VoucherSequence(models.Model):
    agency = models.OneToOneField(Agency, on_delete=models.CASCADE, related_name='voucher_sequence')
    current_sequence = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

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
        base_manager_name = 'all_tenants'

class Booking(models.Model):
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending', _('Pending approval')),
        ('rejected', _('Sent back')),
        ('confirmed', _('Confirmed')),
        ('cancelled', _('Cancelled')),
        ('completed', _('Completed')),
    ]
    voucher_number = models.CharField(max_length=50)
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
    # Approval workflow for vouchers an agent creates: submitted -> approved (saved) or sent back with a reason.
    submitted_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')
    decided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings_decided')
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"{self.voucher_number} · {self.package_name}" if self.package_name else str(self.voucher_number)

    @property
    def status_group(self):
        """What the app shows: Draft, Pending, Sent back, Saved (confirmed or completed) or, for older records, Cancelled."""
        return "saved" if self.status in ("confirmed", "completed") else self.status

    @property
    def status_group_label(self):
        return {"draft": _("Drafted"), "pending": _("Pending"), "rejected": _("Sent back"), "saved": _("Saved"),
                "cancelled": _("Cancelled")}.get(self.status_group, self.status)

    class Meta:
        ordering = ['-created_at']
        base_manager_name = 'all_tenants'
        constraints = [
            models.UniqueConstraint(fields=['agency', 'voucher_number'], name='member_booking_unique_voucher_per_agency'),
        ]

class BookingHotel(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='hotels')
    # SET_NULL, not CASCADE: `hotel_name`/`city` below are already a full
    # snapshot at booking time (voucher_document.html — the actual printed
    # voucher — renders those, never a live `hotel.name` lookup), so a
    # deleted catalog Hotel doesn't need to take an already-issued
    # voucher's line item down with it. Draft (not-yet-finalized) bookings
    # are handled differently — see member/signals.py — since those
    # should actually lose the line item, not silently keep a reference
    # to a hotel that no longer exists in the catalog.
    hotel = models.ForeignKey(Hotel, on_delete=models.SET_NULL, null=True, blank=True)
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
    # SET_NULL — same reasoning as BookingHotel.hotel: the fields below
    # are a full snapshot taken at booking time (see
    # _replace_booking_line_items in views.py), so voucher_document.html
    # renders those, not a live `flight.*` lookup, and a deleted catalog
    # Flight doesn't take an already-issued voucher's leg down with it.
    flight = models.ForeignKey(Flight, on_delete=models.SET_NULL, null=True, blank=True)
    flight_type = models.CharField(max_length=20, choices=[('outbound', 'Outbound'), ('return', 'Return')])
    airline = models.CharField(max_length=100, blank=True, default='')
    flight_number = models.CharField(max_length=20, blank=True, default='')
    departure_city = models.CharField(max_length=100, blank=True, default='')
    arrival_city = models.CharField(max_length=100, blank=True, default='')
    flight_class = models.CharField(max_length=20, choices=Flight.FLIGHT_CLASS, default='economy')
    pnr_number = models.CharField(max_length=20, blank=True, default='')
    # Schedule for this trip (the catalog flight has no dates) — printed on the voucher.
    departure_at = models.DateTimeField(null=True, blank=True)
    arrival_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.airline} {self.flight_number}"

    class Meta:
        ordering = ['flight_type']

    @property
    def sector(self):
        if self.flight_id and self.flight:
            return self.flight.sector
        a, b = (self.departure_city or "").strip(), (self.arrival_city or "").strip()
        return f"{a}-{b}" if a or b else ""

class BookingTransport(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='transports')
    # SET_NULL — same reasoning as BookingHotel.hotel above: `transporter`/
    # `vehicle_type`/`description` are already a full snapshot.
    transport = models.ForeignKey(Transport, on_delete=models.SET_NULL, null=True, blank=True)
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
    GENDER_CHOICES = [
        ('male', _('Male')),
        ('female', _('Female')),
    ]
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booking_mutamers')
    # No catalog FK — travelers are entered directly on the booking as free
    # text (there is no separate Mutamer catalog to pick from), so these
    # fields ARE the record, not a snapshot of something else.
    name = models.CharField(max_length=200)
    passport_number = models.CharField(max_length=50, blank=True, default='')
    visa_number = models.CharField(max_length=50, blank=True, default='')
    nationality = models.CharField(max_length=100, blank=True, default='')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    family_label = models.CharField(max_length=100, blank=True, default='')
    # Voucher columns (Umrah paperwork): passenger type, bed, MOFA, group and PNR numbers.
    PAX_TYPES = [('adult', _('Adult')), ('child', _('Child')), ('infant', _('Infant'))]
    pax_type = models.CharField(max_length=10, choices=PAX_TYPES, default='adult')
    bed = models.BooleanField(default=True)
    mofa_number = models.CharField(max_length=50, blank=True, default='')
    group_number = models.CharField(max_length=50, blank=True, default='')
    pnr = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.voucher_number} - {self.name}"

    class Meta:
        ordering = ['name']

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
        ('pending', _('Pending')),
        ('partial', _('Partial')),
        ('paid', _('Paid')),
        ('refunded', _('Refunded')),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cash', _('Cash')),
        ('card', _('Card')),
        ('bank_transfer', _('Bank Transfer')),
        ('check', _('Check')),
        ('other', _('Other')),
    ]
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    installment = models.ForeignKey(
        'payments.Installment', on_delete=models.SET_NULL, null=True, blank=True, related_name='booking_payments',
        help_text="Set when this payment was recorded against a specific installment rather than ad hoc.",
    )
    idempotency_key = models.CharField(
        max_length=64, blank=True, null=True, unique=True,
        help_text="Set by the 'collect payment' form to stop a double-click/double-submit from recording the same payment twice.",
    )
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
    voucher_number = models.CharField(max_length=50, blank=True)
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vouchers_created')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='vouchers')
    # Set when this voucher was generated from a completed Booking (member
    # workflow) rather than submitted directly by an agent for approval —
    # see _sync_completed_booking_voucher in views.py. SET_NULL so deleting
    # the source booking doesn't take an already-issued voucher down with it.
    booking = models.OneToOneField(
        Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_voucher',
    )
    # No catalog FK — same reasoning as BookingMutamer above: the traveler
    # is entered directly on the voucher, these fields ARE the record.
    mutamer_name = models.CharField(max_length=200)
    mutamer_passport_number = models.CharField(max_length=50, blank=True, default='')
    mutamer_visa_number = models.CharField(max_length=50, blank=True, default='')
    mutamer_nationality = models.CharField(max_length=100, blank=True, default='')
    mutamer_gender = models.CharField(max_length=10, choices=BookingMutamer.GENDER_CHOICES, blank=True, default='')
    mutamer_phone = models.CharField(max_length=20, blank=True, default='')
    mutamer_email = models.EmailField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    # Why a member sent it back; the agent sees this, fixes the voucher and resubmits.
    rejection_reason = models.TextField(blank=True, default='')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vouchers_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    # Public token, not the voucher_number, is what unauthenticated visitors
    # use (see the public_voucher view) — it must stay globally unique.
    public_token = models.CharField(max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_tenants = UnscopedManager()

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
        base_manager_name = 'all_tenants'
        constraints = [
            models.UniqueConstraint(fields=['agency', 'voucher_number'], name='member_voucher_unique_number_per_agency'),
        ]

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
    # Mirrors the voucher types on a travel-trade party statement (BR/BP/JV,
    # Ticket/Hotel/MOFA lines). The first block is what the UI offers; the
    # legacy values stay valid because older rows and payments/signals.py
    # ('booking', 'expense') still use them.
    TRANSACTION_TYPES = [
        ('receipt', _('Receipt (money in)')),
        ('payment', _('Payment (money out)')),
        ('ticket', _('Ticket')),
        ('hotel', _('Hotel')),
        ('visa', _('Visa / MOFA')),
        ('transport', _('Transport')),
        ('package', _('Package')),
        ('journal', _('Journal (JV)')),
        ('expense', _('Expense')),
        ('refund', _('Refund')),
        ('commission', _('Commission')),
        ('income', _('Income')),
        ('booking', _('Booking')),
        ('voucher', _('Voucher')),
        ('other', _('Other')),
    ]
    # Service lines whose PAX count is totalled on the statement footer.
    SERVICE_TYPES = ('ticket', 'hotel', 'visa', 'transport', 'package')
    _TYPE_CODES = {
        'ticket': 'TK', 'hotel': 'HT', 'visa': 'VS', 'transport': 'TR',
        'package': 'PK', 'journal': 'JV', 'expense': 'EX', 'refund': 'RF',
        'commission': 'CM', 'income': 'IN', 'booking': 'BK', 'voucher': 'VC',
        'other': 'OT',
    }
    FX_CURRENCIES = [
        ('SAR', 'SAR'),
        ('USD', 'USD'),
        ('AED', 'AED'),
    ]
    PAYMENT_METHODS = [
        ('cash', _('Cash')),
        ('card', _('Card')),
        ('bank_transfer', _('Bank Transfer')),
        ('cheque', _('Cheque')),
        ('online', _('Online Payment')),
    ]
    transaction_date = models.DateField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    # Ledger organization (party accounts + expenses)
    ENTRY_BUCKETS = [
        ("lein_dein", _("Party accounts (People/Companies)")),
        ("company_expense", _("Company expense")),
    ]
    ENTRY_DIRECTIONS = [
        ("debit", _("Debit (Paid / Given)")),
        ("credit", _("Credit (Received / Taken)")),
    ]
    bucket = models.CharField(max_length=30, choices=ENTRY_BUCKETS, default="company_expense")
    direction = models.CharField(max_length=10, choices=ENTRY_DIRECTIONS, default="debit")
    counterparty_type = models.CharField(max_length=20, blank=True)  # person / company / other (free-form for now)
    counterparty_name = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='PKR')
    # Optional foreign-currency source of `amount` (e.g. 400 SAR @ 77.75).
    # When both fx_amount and rate are set, amount = fx_amount * rate.
    fx_currency = models.CharField(max_length=3, choices=FX_CURRENCIES, blank=True)
    fx_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    pax = models.PositiveIntegerField(null=True, blank=True)
    # Blank for non-cash lines (a ticket sale or supplier bill moves no money).
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True)
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

    objects = TenantManager()
    all_tenants = UnscopedManager()

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.agency.name})"

    @property
    def type_code(self):
        """Short voucher code shown in the Type column (BR, CP, TK, JV...)."""
        if self.transaction_type in ('receipt', 'payment'):
            medium = 'C' if self.payment_method == 'cash' else 'B'
            return medium + ('R' if self.transaction_type == 'receipt' else 'P')
        return self._TYPE_CODES.get(self.transaction_type, 'OT')

    @property
    def debit(self):
        return self.amount if self.direction == 'debit' else 0

    @property
    def credit(self):
        return self.amount if self.direction == 'credit' else 0

    def save(self, *args, **kwargs):
        if self.fx_amount is not None and self.rate:
            self.amount = (self.fx_amount * self.rate).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
        if not self.trans_no:
            # Needs the pk, so it is assigned after the first insert.
            self.trans_no = f"{self.type_code}-{self.pk:06d}"
            LedgerEntry.all_tenants.filter(pk=self.pk).update(trans_no=self.trans_no)

    class Meta:
        verbose_name_plural = 'Ledger Entries'
        ordering = ['-transaction_date', '-created_at']
        base_manager_name = 'all_tenants'
        indexes = [
            models.Index(fields=['agency', 'counterparty_name'], name='ledger_agency_party_idx'),
            models.Index(fields=['agency', 'transaction_date'], name='ledger_agency_date_idx'),
        ]
