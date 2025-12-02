# Generated manually to fix field name mismatch

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0002_auto_20251016_0445'),
    ]

    operations = [
        # Add new fields that match the model
        migrations.AddField(
            model_name='agencybranding',
            name='phone',
            field=models.CharField(blank=True, max_length=20, default=''),
        ),
        migrations.AddField(
            model_name='agencybranding',
            name='email',
            field=models.EmailField(blank=True, max_length=254, default=''),
        ),
        migrations.AddField(
            model_name='agencybranding',
            name='website',
            field=models.URLField(blank=True, default=''),
        ),
        # Add missing fields from model
        migrations.AddField(
            model_name='agencybranding',
            name='social_facebook',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agencybranding',
            name='social_twitter',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agencybranding',
            name='social_instagram',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agencybranding',
            name='social_linkedin',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agencybranding',
            name='booking_confirmation_template',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agencybranding',
            name='payment_receipt_template',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agencybranding',
            name='voucher_template',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='agencybranding',
            name='custom_fields',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        # Create SAASProductConfig model
        migrations.CreateModel(
            name='SAASProductConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(default='Nahd Travels CRM', max_length=200)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='saas_product/')),
                ('address', models.TextField(blank=True)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'SAAS Product Configuration',
                'verbose_name_plural': 'SAAS Product Configuration',
            },
        ),
    ]

