"""
Standard tenant RLS for NotificationDeliveryLog. Rows are written by
notifications/engine.py either inline in the request (tenant context set by the
middleware) or by send_notification_task, which sets the tenant and the
platform-admin bypass on the DB session first — so the policy below allows
every legitimate write.
"""
from django.db import migrations

TABLE = "notifications_notificationdeliverylog"

ENABLE_SQL = (
    f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;\n"
    f"CREATE POLICY tenant_isolation ON {TABLE} USING (\n"
    f"    agency_id::text = current_setting('app.current_tenant_id', true)\n"
    f"    OR current_setting('app.is_platform_admin', true) = 'true'\n"
    f");\n"
)

DISABLE_SQL = (
    f"DROP POLICY IF EXISTS tenant_isolation ON {TABLE};\n"
    f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;\n"
)


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0003_drop_duplicate_booking_index"),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_SQL, reverse_sql=DISABLE_SQL),
    ]
