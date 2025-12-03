from django.db import models
from django.conf import settings
from agencies.models import Agency

User = settings.AUTH_USER_MODEL


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
    currency = models.CharField(max_length=3, default='USD')
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
    """Represents individual segments of a multi-city flight"""
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
