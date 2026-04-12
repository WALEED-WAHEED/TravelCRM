from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("member", "0003_remove_hotel_is_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="ledgerentry",
            name="bucket",
            field=models.CharField(
                choices=[("lein_dein", "Party accounts (People/Companies)"), ("company_expense", "Company expense")],
                default="company_expense",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="ledgerentry",
            name="direction",
            field=models.CharField(
                choices=[("debit", "Debit (Paid / Given)"), ("credit", "Credit (Received / Taken)")],
                default="debit",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="ledgerentry",
            name="counterparty_type",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="ledgerentry",
            name="counterparty_name",
            field=models.CharField(blank=True, max_length=200),
        ),
    ]

