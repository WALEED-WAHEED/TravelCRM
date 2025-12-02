from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0007_auto_20251022_2035'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='flight',
            name='departure_time',
        ),
        migrations.RemoveField(
            model_name='flight',
            name='arrival_time',
        ),
    ]
