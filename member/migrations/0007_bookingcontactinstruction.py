# Generated manually for BookingContactInstruction

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0006_attendance_person_name_nullable_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingContactInstruction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='booking_instructions', to='member.booking')),
                ('instruction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='member.contactinstruction')),
            ],
            options={
                'ordering': ['instruction__city', 'instruction__role', 'instruction__contact_name'],
                'unique_together': {('booking', 'instruction')},
            },
        ),
    ]
