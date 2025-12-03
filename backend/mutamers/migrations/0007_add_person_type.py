from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mutamers', '0006_add_family_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='mutamer',
            name='person_type',
            field=models.CharField(
                max_length=10,
                choices=[('adult', 'Adult'), ('child', 'Child'), ('infant', 'Infant')],
                blank=True,
                null=True,
            ),
        ),
    ]


