"""
Reverts 0008/0009: RLS is disabled on system_config_auditlog entirely.

Why: Postgres RLS checks a SELECT policy against a row's visibility
whenever an INSERT uses RETURNING — which the Django ORM always does
for Postgres to retrieve the new PK. AuditLog rows are written by
trusted internal signal code (utils/audit.py) reacting to *any* save on
an audited model, including saves that happen outside a normal HTTP
request — management commands, Django's own auth signals (e.g. the
last_login update on login()), and future background jobs — none of
which have the app.current_tenant_id/app.is_platform_admin session GUCs
set. In that combination, the RETURNING visibility check fails and the
INSERT is rejected — which doesn't just lose an audit entry, it raises
inside the post_save signal and aborts the *original* save (login
itself failed during testing this exact way).

Tenant isolation for AuditLog is still enforced at the ORM layer: its
`objects` manager (TenantManager, system_config/models.py) scopes every
read to the current tenant (or Super Admin bypass), and both read call
sites (rbac/views.py:activity_log, platform_admin/views.py) go through
it. That single layer is the right tradeoff here — RLS's write-path
fragility outweighs the marginal extra read protection for a table nothing
but trusted signal code ever writes to.
"""
from django.db import migrations

TABLE = "system_config_auditlog"

DISABLE_SQL = (
    f"DROP POLICY IF EXISTS tenant_isolation ON {TABLE};\n"
    f"DROP POLICY IF EXISTS tenant_isolation_read ON {TABLE};\n"
    f"DROP POLICY IF EXISTS allow_insert ON {TABLE};\n"
    f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;\n"
)

# Reapply the 0009 state if ever rolled back.
REENABLE_SQL = (
    f'ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;\n'
    f'CREATE POLICY tenant_isolation_read ON {TABLE} FOR SELECT USING (\n'
    f"    (agency_id IS NOT NULL AND agency_id::text = current_setting('app.current_tenant_id', true))\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
    f'CREATE POLICY allow_insert ON {TABLE} FOR INSERT WITH CHECK (true);\n'
)


class Migration(migrations.Migration):

    dependencies = [
        ('system_config', '0009_auditlog_rls_select_only'),
    ]

    operations = [
        migrations.RunSQL(sql=DISABLE_SQL, reverse_sql=REENABLE_SQL),
    ]
