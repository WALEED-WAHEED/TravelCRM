# Generated manually to add parent company fields to SAASProductConfig

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0004_fix_nullable_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='saasproductconfig',
            name='company_name',
            field=models.CharField(blank=True, help_text='Parent company name (e.g., NOORI KAKI CO.)', max_length=200),
        ),
        migrations.AddField(
            model_name='saasproductconfig',
            name='country',
            field=models.CharField(blank=True, help_text='Parent company country', max_length=100),
        ),
        migrations.AddField(
            model_name='saasproductconfig',
            name='email',
            field=models.EmailField(blank=True, help_text='Parent company email', max_length=254),
        ),
    ]

