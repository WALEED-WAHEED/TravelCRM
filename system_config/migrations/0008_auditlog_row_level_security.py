"""
RLS for system_config_auditlog. Unlike the nullable-agency policy used
for EmailTemplate/APIKey (migration 0006), NULL here means "platform-
level entry" and must stay Super-Admin-only, not visible to everyone —
so this policy does NOT include an `agency_id IS NULL` visibility clause.
"""
from django.db import migrations

TABLE = "system_config_auditlog"

ENABLE_SQL = (
    f'ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;\n'
    f'CREATE POLICY tenant_isolation ON {TABLE} USING (\n'
    f"    (agency_id IS NOT NULL AND agency_id::text = current_setting('app.current_tenant_id', true))\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
)

DISABLE_SQL = (
    f"DROP POLICY IF EXISTS tenant_isolation ON {TABLE};\n"
    f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;\n"
)


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0007_alter_auditlog_options_alter_auditlog_managers_and_more'),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_SQL, reverse_sql=DISABLE_SQL),
    ]
