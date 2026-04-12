from django.contrib import admin
from .models import (
    Hotel, HotelRoom, HotelImage,
    Flight, FlightSegment,
    Transport,
    AttendanceLog,
    Contact, ContactInstruction,
    Mutamer, MutamerDocument,
    VoucherSequence, Booking, BookingHotel, BookingFlight, BookingTransport, BookingMutamer, BookingContact, BookingTeamContact, BookingPayment,
    Voucher, VoucherService,
    LedgerEntry
)

# Basic registration for all models
admin.site.register(Hotel)
admin.site.register(HotelRoom)
admin.site.register(HotelImage)
admin.site.register(Flight)
admin.site.register(FlightSegment)
admin.site.register(Transport)
admin.site.register(AttendanceLog)
admin.site.register(Contact)
admin.site.register(ContactInstruction)
admin.site.register(Mutamer)
admin.site.register(MutamerDocument)
admin.site.register(VoucherSequence)
admin.site.register(Booking)
admin.site.register(BookingHotel)
admin.site.register(BookingFlight)
admin.site.register(BookingTransport)
admin.site.register(BookingMutamer)
admin.site.register(BookingContact)
admin.site.register(BookingTeamContact)
admin.site.register(BookingPayment)
admin.site.register(Voucher)
admin.site.register(VoucherService)
admin.site.register(LedgerEntry)
