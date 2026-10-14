from django.db import migrations


def backfill(apps, schema_editor):
    BookingFlight = apps.get_model('member', 'BookingFlight')
    qs = BookingFlight.objects.filter(flight__isnull=False).select_related('flight')
    for bf in qs:
        bf.airline = bf.flight.airline
        bf.flight_number = bf.flight.flight_number or ''
        bf.departure_city = bf.flight.departure_city
        bf.arrival_city = bf.flight.arrival_city
        bf.flight_class = bf.flight.flight_class
        bf.pnr_number = bf.flight.pnr_number or ''
        bf.save(update_fields=[
            'airline', 'flight_number', 'departure_city', 'arrival_city', 'flight_class', 'pnr_number',
        ])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0014_bookingflight_airline_bookingflight_arrival_city_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=noop),
    ]
