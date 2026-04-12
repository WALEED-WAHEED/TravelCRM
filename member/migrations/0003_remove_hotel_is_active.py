from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0002_alter_currency_default_pkr'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='hotel',
            name='is_active',
        ),
    ]
