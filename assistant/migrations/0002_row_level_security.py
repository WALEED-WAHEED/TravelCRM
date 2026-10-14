"""
Standard tenant RLS for ChatSession, ChatMessage, and PendingAction — all
three are only ever written from real HTTP request context (the chat
send/confirm/reject views), never from a background worker, so the
AuditLog write-path exception (see system_config/migrations/0010)
doesn't apply here.
"""
from django.db import migrations

TABLES = ["assistant_chatsession", "assistant_chatmessage", "assistant_pendingaction"]

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
        ("assistant", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_SQL, reverse_sql=DISABLE_SQL),
    ]
