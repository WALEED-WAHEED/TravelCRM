# Generated manually to fix phone_number NOT NULL constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0003_fix_agency_branding_fields'),
    ]

    operations = [
        # Make phone_number nullable
        migrations.AlterField(
            model_name='agencybranding',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        # Make email_address nullable
        migrations.AlterField(
            model_name='agencybranding',
            name='email_address',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        # Make website_url nullable
        migrations.AlterField(
            model_name='agencybranding',
            name='website_url',
            field=models.URLField(blank=True, null=True),
        ),
    ]
