from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model with role-based access
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('agent', 'Agent'),
    ]
    
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES,
        default='agent'
    )
    agency = models.ForeignKey(
        'agencies.Agency',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users'
    )
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    class Meta:
        ordering = ['-created_at']
