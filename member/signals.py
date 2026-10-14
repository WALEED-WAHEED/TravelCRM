"""
Deleting a Hotel/Flight/Transport from the catalog must not silently
rewrite an already-issued voucher's history — see the on_delete=SET_NULL
comments on BookingHotel.hotel / BookingFlight.flight /
BookingTransport.transport in models.py for why that alone is safe (all
three snapshot their display fields at booking time).

What SET_NULL alone doesn't give us: a *draft* booking's line item should
actually disappear (it's still being built — an agent shouldn't be left
staring at a row that silently lost its catalog link and looks broken),
while a confirmed/completed/cancelled booking's line item must survive
untouched. That distinction depends on the related Booking's status,
which a bare on_delete= can't express — hence this pre_delete signal,
which runs before the FK-nulling happens and removes just the
draft-booking rows.

pre_delete fires for both instance.delete() and QuerySet.delete() (e.g.
Django admin's "Delete selected" bulk action), so this can't be
sidestepped by skipping a model-level delete() override — same reasoning
as utils/audit.py's own pre_delete usage elsewhere in this codebase.
"""
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import BookingFlight, BookingHotel, BookingTransport, Flight, Hotel, Transport


@receiver(pre_delete, sender=Hotel, dispatch_uid="member_pre_delete_hotel_drop_draft_lines")
def _drop_draft_booking_hotel_lines(sender, instance, **kwargs):
    BookingHotel.objects.filter(hotel=instance, booking__status='draft').delete()


@receiver(pre_delete, sender=Transport, dispatch_uid="member_pre_delete_transport_drop_draft_lines")
def _drop_draft_booking_transport_lines(sender, instance, **kwargs):
    BookingTransport.objects.filter(transport=instance, booking__status='draft').delete()


@receiver(pre_delete, sender=Flight, dispatch_uid="member_pre_delete_flight_drop_draft_lines")
def _drop_draft_booking_flight_lines(sender, instance, **kwargs):
    BookingFlight.objects.filter(flight=instance, booking__status='draft').delete()
