from django.db import models
from django.conf import settings
from agencies.models import Agency

User = settings.AUTH_USER_MODEL


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
    is_active = models.BooleanField(default=True)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='hotels')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='hotels_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.city}"
    
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
    
    class Meta:
        pass


class HotelImage(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='hotels/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.hotel.name} - Image"
    
    class Meta:
        pass
