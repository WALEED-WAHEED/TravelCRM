"""
Standard tenant RLS for PaymentPlan, Installment, and SupplierPayment —
all three are only ever written from real HTTP request context (the
collect_payment, payment_plan, and record_supplier_payment views), never
from a background worker or management command, so the AuditLog
write-path exception (see system_config/migrations/0010) doesn't apply
here.
"""
from django.db import migrations

TABLES = ["payments_paymentplan", "payments_installment", "payments_supplierpayment"]

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
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_SQL, reverse_sql=DISABLE_SQL),
    ]
