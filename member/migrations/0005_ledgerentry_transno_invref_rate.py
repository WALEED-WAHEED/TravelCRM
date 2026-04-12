from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("member", "0004_ledgerentry_bucket_direction_counterparty"),
    ]

    operations = [
        migrations.AddField(
            model_name="ledgerentry",
            name="trans_no",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="ledgerentry",
            name="inv_ref",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="ledgerentry",
            name="rate",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]

