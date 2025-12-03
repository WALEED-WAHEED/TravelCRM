from django.db import models
from django.conf import settings
from agencies.models import Agency

User = settings.AUTH_USER_MODEL


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
