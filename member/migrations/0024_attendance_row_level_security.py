"""
Row-Level Security for the attendance self check-in tables — same
tenant_isolation policy as the other tenant tables (see
0009_row_level_security.py). The field_staff M2M through-table has no
agency_id; it is only reachable through its (RLS-protected) settings row.
"""
from django.db import migrations

TABLES = ["member_attendancesettings", "member_attendancecorrection"]

ENABLE_SQL = "\n".join(
    f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;\n"
    f"CREATE POLICY tenant_isolation ON {t} USING (\n"
    f"    agency_id::text = current_setting('app.current_tenant_id', true)\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
    for t in TABLES
)
DISABLE_SQL = "\n".join(
    f"DROP POLICY IF EXISTS tenant_isolation ON {t};\nALTER TABLE {t} DISABLE ROW LEVEL SECURITY;\n" for t in TABLES
)


def _forwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(ENABLE_SQL)


def _backwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DISABLE_SQL)


class Migration(migrations.Migration):

    dependencies = [
        ("member", "0023_attendance_self_checkin"),
    ]

    operations = [
        migrations.RunPython(_forwards, _backwards),
    ]
