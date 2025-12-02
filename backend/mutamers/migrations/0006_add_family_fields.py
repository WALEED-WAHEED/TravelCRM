# Generated manually for family clustering feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mutamers', '0005_auto_20251024_1624'),
    ]

    operations = [
        migrations.AddField(
            model_name='mutamer',
            name='family_id',
            field=models.CharField(blank=True, help_text='Unique identifier for family group', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='mutamer',
            name='is_family_head',
            field=models.BooleanField(default=False, help_text='Whether this mutamer is the head of the family'),
        ),
        migrations.AddField(
            model_name='mutamer',
            name='family_head_name',
            field=models.CharField(blank=True, help_text='Name of the family head', max_length=200, null=True),
        ),
    ]
