from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from member.models import Booking, BookingPayment

from .tasks import dispatch


@receiver(pre_save, sender=Booking)
def _snapshot_booking_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._notif_old_status = None
        return
    old = Booking.all_tenants.filter(pk=instance.pk).values_list('status', flat=True).first()
    instance._notif_old_status = old


@receiver(post_save, sender=Booking)
def _on_booking_saved(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_notif_old_status', None)
    if created or old_status == instance.status:
        return
    if instance.status == 'confirmed':
        dispatch('voucher_generated', instance)


@receiver(post_save, sender=BookingPayment)
def _on_payment_recorded(sender, instance, created, **kwargs):
    if created:
        dispatch('payment_receipt', instance.booking, payment=instance)
