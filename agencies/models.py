from django.db import models
from django.conf import settings


class Agency(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    attendance_admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_admin_for_agencies",
    )
    attendance_admin_password_hash = models.CharField(max_length=256, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def member_count(self):
        return self.users.filter(role='member').count()
    
    @property
    def agent_count(self):
        return self.users.filter(role='agent').count()
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Agencies'
        ordering = ['-created_at']
