from django.db import models
from django.conf import settings
from agencies.models import Agency

User = settings.AUTH_USER_MODEL


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
    
    class Meta:
        pass
