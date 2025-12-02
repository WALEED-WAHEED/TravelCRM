from django.db import models
from django.conf import settings
from agencies.models import Agency

User = settings.AUTH_USER_MODEL


class LedgerEntry(models.Model):
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('booking', 'Booking'),
        ('voucher', 'Voucher'),
        ('refund', 'Refund'),
        ('commission', 'Commission'),
        ('other', 'Other'),
    ]
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
    ]
    
    transaction_date = models.DateField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    voucher = models.ForeignKey('vouchers.Voucher', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='ledger_entries')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ledger_entries_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.agency.name})"
    
    class Meta:
        verbose_name_plural = 'Ledger Entries'
        ordering = ['-transaction_date', '-created_at']
