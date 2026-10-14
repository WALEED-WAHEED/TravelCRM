"""
Row-Level Security for member_package — same tenant_isolation policy as the
other tenant tables (see 0009_row_level_security.py for the rationale).
"""
from django.db import migrations

ENABLE_SQL = """
ALTER TABLE member_package ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON member_package USING (
    agency_id::text = current_setting('app.current_tenant_id', true)
    OR current_setting('app.is_platform_admin', true) = 'true'
);
"""

DISABLE_SQL = """
DROP POLICY IF EXISTS tenant_isolation ON member_package;
ALTER TABLE member_package DISABLE ROW LEVEL SECURITY;
"""


def _forwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(ENABLE_SQL)


def _backwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DISABLE_SQL)


class Migration(migrations.Migration):

    dependencies = [
        ("member", "0021_package"),
    ]

    operations = [
        migrations.RunPython(_forwards, _backwards),
    ]
