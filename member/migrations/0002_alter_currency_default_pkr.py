# Generated manually: default currency is PKR across the product.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flight',
            name='currency',
            field=models.CharField(default='PKR', max_length=3),
        ),
        migrations.AlterField(
            model_name='ledgerentry',
            name='currency',
            field=models.CharField(default='PKR', max_length=3),
        ),
    ]
