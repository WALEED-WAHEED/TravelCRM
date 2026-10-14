"""Row-Level Security for member_bookingnote (same policy as 0009)."""
from django.db import migrations

ENABLE_SQL = """
ALTER TABLE member_bookingnote ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON member_bookingnote USING (
    agency_id::text = current_setting('app.current_tenant_id', true)
    OR current_setting('app.is_platform_admin', true) = 'true'
);
"""
DISABLE_SQL = """
DROP POLICY IF EXISTS tenant_isolation ON member_bookingnote;
ALTER TABLE member_bookingnote DISABLE ROW LEVEL SECURITY;
"""


def _forwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(ENABLE_SQL)


def _backwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DISABLE_SQL)


class Migration(migrations.Migration):

    dependencies = [
        ("member", "0029_bookingnote"),
    ]

    operations = [
        migrations.RunPython(_forwards, _backwards),
    ]
