from django.db import models
from django.conf import settings
from agencies.models import Agency

User = settings.AUTH_USER_MODEL


class AttendanceLog(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('leave', 'Leave'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_logs')
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
        return f"{self.user.username} - {self.date} ({self.status})"
    
    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date', '-created_at']
