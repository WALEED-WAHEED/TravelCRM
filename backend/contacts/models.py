from django.db import models
from django.conf import settings
from agencies.models import Agency

User = settings.AUTH_USER_MODEL


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


# Keep the old ContactInstruction model for backward compatibility if needed
class ContactInstruction(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="contact_instructions")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contact_instructions")

    city = models.CharField(max_length=100)
    role = models.CharField(max_length=100)  # e.g. "Makkah Management", "Madina Helpline"
    contact_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.city} - {self.role} ({self.contact_name})"
    
    class Meta:
        pass
