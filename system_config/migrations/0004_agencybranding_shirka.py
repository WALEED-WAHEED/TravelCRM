from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("system_config", "0003_saasproductconfig_slogan"),
    ]

    operations = [
        migrations.AddField(
            model_name="agencybranding",
            name="shirka_company_name",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="agencybranding",
            name="shirka_company_country",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="agencybranding",
            name="shirka_company_whatsapp",
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
