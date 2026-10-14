"""
Postgres Row-Level Security — the second, database-enforced layer of
tenant isolation behind the TenantManager ORM layer (utils/tenancy.py).

Only takes effect for connections that are neither the table owner nor a
superuser (see docs/travelcrm_app role, created outside migrations —
`postgres` remains the owner/superuser and therefore bypasses these
policies, which is intentional: it's the migration/admin credential, not
the one the running application connects with).

A no-op on any backend other than Postgres.
"""
from django.db import migrations

TENANT_TABLES = [
    "member_hotel",
    "member_flight",
    "member_transport",
    "member_attendancelog",
    "member_contact",
    "member_contactinstruction",
    "member_mutamer",
    "member_booking",
    "member_voucher",
    "member_ledgerentry",
    "member_vouchersequence",
]

ENABLE_SQL = "\n".join(
    f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n'
    f'CREATE POLICY tenant_isolation ON {table} USING (\n'
    f"    agency_id::text = current_setting('app.current_tenant_id', true)\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
    for table in TENANT_TABLES
)

DISABLE_SQL = "\n".join(
    f"DROP POLICY IF EXISTS tenant_isolation ON {table};\n"
    f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;\n"
    for table in TENANT_TABLES
)


class Migration(migrations.Migration):

    dependencies = [
        ("member", "0008_alter_attendancelog_options_alter_booking_options_and_more"),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_SQL, reverse_sql=DISABLE_SQL),
    ]
