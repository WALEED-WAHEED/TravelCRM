# Generated manually to make voucher_number required (non-nullable)

from django.db import migrations, models


def populate_voucher_numbers(apps, schema_editor):
    """Populate voucher_number for existing bookings"""
    Booking = apps.get_model('bookings', 'Booking')
    for booking in Booking.objects.filter(voucher_number__isnull=True):
        # Generate a temporary voucher number based on booking ID
        booking.voucher_number = f"TEMP-{booking.id:06d}"
        booking.save()


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_add_booking_fields'),
    ]

    operations = [
        # First, populate existing bookings with voucher numbers
        migrations.RunPython(populate_voucher_numbers, migrations.RunPython.noop),
        # Then make it non-nullable
        migrations.AlterField(
            model_name='booking',
            name='voucher_number',
            field=models.CharField(max_length=50, unique=True),
        ),
    ]

