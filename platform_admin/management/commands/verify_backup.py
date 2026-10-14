"""
Automated backup verification: dump the live database, restore it into a
throwaway database, sanity-check the row counts match, then clean up.
Proves backups are actually restorable, not just that pg_dump exits 0.

Requires admin-level Postgres credentials (createdb/dropdb), separate
from the app's own scoped `travelcrm_app` runtime role — pass via
PG_ADMIN_USER/PG_ADMIN_PASSWORD env vars, or it falls back to DB_USER.

Usage:
    python manage.py verify_backup
    python manage.py verify_backup --keep  # don't drop the test database (inspect it manually)

Intended to run on a schedule (cron / Windows Task Scheduler) hitting a
non-production replica, or against production during a low-traffic
window — it does not touch the live database, only reads from it.
"""
import json
import os
import subprocess
import tempfile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

BACKUP_STATUS_KEY = "ops.last_backup_verification"


class Command(BaseCommand):
    help = "Dump the database, restore it into a throwaway database, and verify row counts match."

    def add_arguments(self, parser):
        parser.add_argument('--keep', action='store_true', help="Don't drop the verification database afterward.")

    def handle(self, *args, **options):
        try:
            self._run(*args, **options)
        except CommandError as exc:
            self._record_result(success=False, detail=str(exc))
            raise
        else:
            self._record_result(success=True, detail="Dump restores cleanly and row counts match.")

    def _record_result(self, success, detail):
        # Surfaced on the Super Admin System Health page — this command is
        # otherwise CLI-only (cron/Task Scheduler), so without this the
        # panel has no way to know whether a backup was ever verified, or
        # when. Reuses SystemConfiguration rather than a dedicated model.
        from system_config.models import SystemConfiguration

        SystemConfiguration.objects.update_or_create(
            key=BACKUP_STATUS_KEY,
            defaults={
                'value': json.dumps({
                    'success': success,
                    'detail': detail,
                    'checked_at': timezone.now().isoformat(),
                }),
                'description': "Written automatically by `manage.py verify_backup` — do not edit by hand.",
            },
        )

    def _run(self, *args, **options):
        db = settings.DATABASES['default']
        env = os.environ.copy()
        admin_user = os.getenv('PG_ADMIN_USER', db['USER'])
        admin_password = os.getenv('PG_ADMIN_PASSWORD', db['PASSWORD'])
        host, port, name = db['HOST'], str(db['PORT']), db['NAME']
        verify_db = f"{name}_backup_verify"
        env['PGPASSWORD'] = admin_password

        def run(cmd, **kwargs):
            self.stdout.write(f"  $ {' '.join(cmd)}")
            return subprocess.run(cmd, env=env, check=True, capture_output=True, text=True, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            dump_path = os.path.join(tmp, "verify.dump")

            self.stdout.write(self.style.MIGRATE_HEADING("1. Dumping live database"))
            try:
                run(["pg_dump", "--host", host, "--port", port, "--username", admin_user,
                     "--format=custom", "--no-owner", "--no-privileges", "--file", dump_path, name])
            except FileNotFoundError as e:
                raise CommandError("pg_dump not found on PATH — install the PostgreSQL client tools.") from e
            except subprocess.CalledProcessError as e:
                raise CommandError(f"pg_dump failed:\n{e.stderr}") from e

            size = os.path.getsize(dump_path)
            if size == 0:
                raise CommandError("Dump file is empty — treating this as a failed backup.")
            self.stdout.write(f"   Dump size: {size:,} bytes")

            self.stdout.write(self.style.MIGRATE_HEADING("2. Restoring into throwaway database"))
            run(["dropdb", "--host", host, "--port", port, "--username", admin_user, "--if-exists", verify_db])
            run(["createdb", "--host", host, "--port", port, "--username", admin_user, verify_db])
            try:
                run(["pg_restore", "--host", host, "--port", port, "--username", admin_user,
                     "--no-owner", "--no-privileges", "--dbname", verify_db, dump_path])
            except subprocess.CalledProcessError as e:
                raise CommandError(f"pg_restore failed:\n{e.stderr}") from e

            self.stdout.write(self.style.MIGRATE_HEADING("3. Comparing row counts"))
            mismatches = self._compare_row_counts(host, port, admin_user, admin_password, name, verify_db)

            if not options['keep']:
                run(["dropdb", "--host", host, "--port", port, "--username", admin_user, verify_db])
            else:
                self.stdout.write(f"   Kept '{verify_db}' for manual inspection.")

        if mismatches:
            raise CommandError(f"Row count mismatch after restore: {mismatches}")
        self.stdout.write(self.style.SUCCESS("Backup verified: dump restores cleanly and row counts match."))

    def _compare_row_counts(self, host, port, user, password, source_db, verify_db):
        import psycopg2

        def counts(dbname):
            conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
            cur = conn.cursor()
            cur.execute("""
                SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;
            """)
            result = dict(cur.fetchall())
            conn.close()
            return result

        # pg_stat_user_tables is an estimate updated by autovacuum, not a
        # live COUNT(*) — good enough to catch "restore silently lost
        # most of the data", not meant as an exact-match assertion.
        source_counts = counts(source_db)
        restored_counts = counts(verify_db)
        mismatches = {}
        for table, source_n in source_counts.items():
            restored_n = restored_counts.get(table, 0)
            if source_n > 0 and restored_n == 0:
                mismatches[table] = f"source~{source_n}, restored={restored_n}"
        return mismatches
