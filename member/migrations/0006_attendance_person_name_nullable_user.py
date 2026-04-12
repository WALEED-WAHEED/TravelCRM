from django.db import migrations, models
import django.db.models.deletion


def backfill_person_name(apps, schema_editor):
    AttendanceLog = apps.get_model("member", "AttendanceLog")
    for row in AttendanceLog.objects.select_related("user").all().iterator():
        if row.person_name and str(row.person_name).strip():
            continue
        if row.user_id:
            fn = (getattr(row.user, "full_name", "") or "").strip()
            if not fn:
                fn = ((getattr(row.user, "first_name", "") or "") + " " + (getattr(row.user, "last_name", "") or "")).strip()
            row.person_name = fn or getattr(row.user, "username", "") or "Unknown"
        else:
            row.person_name = "Unknown"
        row.save(update_fields=["person_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("member", "0005_ledgerentry_transno_invref_rate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attendancelog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="attendance_logs",
                to="accounts.user",
            ),
        ),
        migrations.AddField(
            model_name="attendancelog",
            name="person_name",
            field=models.CharField(default="", max_length=200),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_person_name, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="attendancelog",
            unique_together={("agency", "person_name", "date")},
        ),
    ]

