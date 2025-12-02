# Generated manually to add missing Booking fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0003_add_voucher_sequence'),
    ]

    operations = [
        # Add new fields to Booking model
        # First add voucher_number as nullable
        migrations.AddField(
            model_name='booking',
            name='voucher_number',
            field=models.CharField(max_length=50, unique=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='manual_number',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='booking',
            name='package_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='booking',
            name='client_company',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='booking',
            name='client_country',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='booking',
            name='client_whatsapp',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='booking',
            name='pax_adults',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='booking',
            name='pax_children',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='booking',
            name='pax_infants',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='booking',
            name='total_beds',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='booking',
            name='total_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]

