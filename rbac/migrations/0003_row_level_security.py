"""
Postgres RLS for rbac_role, matching the nullable-agency pattern used for
system_config_emailtemplate / system_config_apikey (see
system_config/migrations/0006_row_level_security.py): global templates
(agency IS NULL) are visible to everyone, a tenant's own custom roles
are visible only to that tenant (or Super Admin bypass).

rbac_permission is excluded — it's a fixed global catalog with no
agency column at all, not a data-leak surface.
"""
from django.db import migrations

TABLE = "rbac_role"

ENABLE_SQL = (
    f'ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;\n'
    f'CREATE POLICY tenant_isolation ON {TABLE} USING (\n'
    f"    agency_id IS NULL\n"
    f"    OR agency_id::text = current_setting('app.current_tenant_id', true)\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
)

DISABLE_SQL = (
    f"DROP POLICY IF EXISTS tenant_isolation ON {TABLE};\n"
    f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;\n"
)


class Migration(migrations.Migration):

    dependencies = [
        ('rbac', '0002_seed_catalog'),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_SQL, reverse_sql=DISABLE_SQL),
    ]
