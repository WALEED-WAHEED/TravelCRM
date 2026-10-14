"""
Postgres Row-Level Security for the agency-scoped system_config models.
See member/migrations/0009_row_level_security.py for the full rationale.

SAASProductConfig, SystemConfiguration and AuditLog are intentionally
platform-global (no agency column) and are excluded — their protection
is that only Super Admin views can reach them (see the IsSuperAdmin
permission fix in system_config/views.py), not row-level tenant scoping.
"""
from django.db import migrations

STRICT_TABLES = [
    "system_config_agencybranding",
    "system_config_notificationsettings",
]

NULLABLE_AGENCY_TABLES = [
    "system_config_emailtemplate",
    "system_config_apikey",
]

STRICT_SQL = "\n".join(
    f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n'
    f'CREATE POLICY tenant_isolation ON {table} USING (\n'
    f"    agency_id::text = current_setting('app.current_tenant_id', true)\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
    for table in STRICT_TABLES
)

NULLABLE_SQL = "\n".join(
    f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n'
    f'CREATE POLICY tenant_isolation ON {table} USING (\n'
    f"    agency_id IS NULL\n"
    f"    OR agency_id::text = current_setting('app.current_tenant_id', true)\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
    for table in NULLABLE_AGENCY_TABLES
)

DISABLE_SQL = "\n".join(
    f"DROP POLICY IF EXISTS tenant_isolation ON {table};\n"
    f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;\n"
    for table in STRICT_TABLES + NULLABLE_AGENCY_TABLES
)


class Migration(migrations.Migration):

    dependencies = [
        ("system_config", "0005_alter_agencybranding_options_alter_apikey_options_and_more"),
    ]

    operations = [
        migrations.RunSQL(sql=STRICT_SQL + NULLABLE_SQL, reverse_sql=DISABLE_SQL),
    ]
