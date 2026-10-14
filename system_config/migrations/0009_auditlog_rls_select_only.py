"""
The RLS policy from 0008 applied to ALL commands by default (SELECT,
INSERT, UPDATE, DELETE), which is the right call for tenant data tables
but wrong for AuditLog specifically: its writes come from trusted
internal signal code (utils/audit.py) reacting to *any* model save,
including from contexts that won't always have the Postgres session
GUCs set (management commands, Django's own auth signals outside a
request, future background jobs) — audit logging must never be able to
block the operation it's observing. Reads stay strictly tenant-scoped;
only the write restriction is lifted.
"""
from django.db import migrations

TABLE = "system_config_auditlog"

UPGRADE_SQL = (
    f"DROP POLICY IF EXISTS tenant_isolation ON {TABLE};\n"
    f'CREATE POLICY tenant_isolation_read ON {TABLE} FOR SELECT USING (\n'
    f"    (agency_id IS NOT NULL AND agency_id::text = current_setting('app.current_tenant_id', true))\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
    f'CREATE POLICY allow_insert ON {TABLE} FOR INSERT WITH CHECK (true);\n'
)

DOWNGRADE_SQL = (
    f"DROP POLICY IF EXISTS tenant_isolation_read ON {TABLE};\n"
    f"DROP POLICY IF EXISTS allow_insert ON {TABLE};\n"
    f'CREATE POLICY tenant_isolation ON {TABLE} USING (\n'
    f"    (agency_id IS NOT NULL AND agency_id::text = current_setting('app.current_tenant_id', true))\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
)


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0008_auditlog_row_level_security'),
    ]

    operations = [
        migrations.RunSQL(sql=UPGRADE_SQL, reverse_sql=DOWNGRADE_SQL),
    ]
