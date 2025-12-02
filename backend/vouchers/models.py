import uuid
from django.db import models
from django.conf import settings
from mutamers.models import Mutamer

User = settings.AUTH_USER_MODEL


class Voucher(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    voucher_number = models.CharField(max_length=50, unique=True, blank=True)
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vouchers_created')
    mutamer = models.ForeignKey(Mutamer, on_delete=models.CASCADE, related_name='vouchers')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vouchers_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    public_token = models.CharField(max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
    
    class Meta:
        pass
