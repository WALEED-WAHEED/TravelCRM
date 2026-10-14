"""
Standard tenant RLS for Subscription and PaymentRecord — both are only
ever written from real HTTP request context (signup, Super Admin
actions, tenant billing actions), never from a background worker, so
the AuditLog write-path exception (see system_config/migrations/0010)
doesn't apply here.

Plan is intentionally excluded — it's a global, Super-Admin-managed
catalog with no agency column, same as SystemConfiguration.
"""
from django.db import migrations

TABLES = ["billing_subscription", "billing_paymentrecord"]

ENABLE_SQL = "\n".join(
    f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n'
    f'CREATE POLICY tenant_isolation ON {table} USING (\n'
    f"    agency_id::text = current_setting('app.current_tenant_id', true)\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
    for table in TABLES
)

DISABLE_SQL = "\n".join(
    f"DROP POLICY IF EXISTS tenant_isolation ON {table};\n"
    f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;\n"
    for table in TABLES
)


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_SQL, reverse_sql=DISABLE_SQL),
    ]
