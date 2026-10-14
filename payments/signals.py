"""
Automatic ledger reconciliation: recording a BookingPayment or
SupplierPayment writes the matching LedgerEntry itself, closing the gap
the audit flagged — previously an agent had to remember to duplicate
every payment into the ledger by hand.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from member.models import BookingPayment, LedgerEntry

from .models import SupplierPayment

# BookingPayment/SupplierPayment and LedgerEntry each grew their
# payment-method choices independently — map rather than assume they match.
_BOOKING_TO_LEDGER_METHOD = {
    'cash': 'cash', 'card': 'card', 'bank_transfer': 'bank_transfer',
    'check': 'cheque', 'other': 'online',
}
_SUPPLIER_TO_LEDGER_METHOD = {
    'cash': 'cash', 'card': 'card', 'bank_transfer': 'bank_transfer', 'other': 'online',
}


@receiver(post_save, sender=BookingPayment)
def _reconcile_booking_payment(sender, instance, created, **kwargs):
    if not created:
        return

    LedgerEntry.objects.create(
        transaction_date=timezone.localdate(),
        transaction_type='booking',
        bucket='lein_dein',
        direction='credit',
        counterparty_type='company',
        counterparty_name=instance.booking.client_company or instance.booking.voucher_number,
        amount=instance.amount,
        currency=instance.booking.agency.default_currency,
        payment_method=_BOOKING_TO_LEDGER_METHOD.get(instance.payment_method, 'cash'),
        reference_number=instance.transaction_id,
        description=f"Payment received for booking {instance.booking.voucher_number}",
        booking=instance.booking,
        agency=instance.booking.agency,
        created_by=instance.agent,
    )

    if instance.installment_id:
        instance.installment.status = 'paid'
        instance.installment.save(update_fields=['status', 'updated_at'])


@receiver(post_save, sender=SupplierPayment)
def _reconcile_supplier_payment(sender, instance, created, **kwargs):
    if not created:
        return

    LedgerEntry.objects.create(
        transaction_date=timezone.localdate(),
        transaction_type='expense',
        bucket='lein_dein',
        direction='debit',
        counterparty_type='company',
        counterparty_name=instance.supplier.name,
        amount=instance.amount,
        currency=instance.currency,
        payment_method=_SUPPLIER_TO_LEDGER_METHOD.get(instance.method, 'cash'),
        reference_number=instance.reference,
        description=f"Payment to supplier {instance.supplier.name}",
        agency=instance.agency,
        created_by=instance.paid_by,
    )
