from django.db import models


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
