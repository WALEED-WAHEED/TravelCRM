# Backup & restore

Three pieces, all built on standard `pg_dump`/`pg_restore` — no extra
infrastructure required.

## Taking a backup

```bash
DB_NAME=TravelCRM DB_USER=postgres DB_PASSWORD=... DB_HOST=localhost \
  ./scripts/backup.sh /path/to/backup/directory
```

Writes a timestamped, compressed custom-format dump and prunes anything
beyond the most recent 14 backups in that directory. Run this on a
schedule (cron / Windows Task Scheduler) pointed at wherever backups
should land — off the application host, ideally.

Always run backup/restore with the `postgres` admin credentials, not the
app's own scoped `travelcrm_app` role — see `travelcrm/settings.py` and
`.env` for why that role is deliberately limited.

## Restoring a backup

```bash
DB_NAME=TravelCRM DB_USER=postgres DB_PASSWORD=... DB_HOST=localhost \
  ./scripts/restore.sh /path/to/backup/travelcrm_20260101_120000.dump
```

By default this restores into a throwaway `<DB_NAME>_restore_test`
database, never the real one — safe to run any time to confirm a backup
is actually restorable. Pass `--force-target` (with an interactive
confirmation prompt) to restore directly into the real database instead;
that's a destructive operation and should only be used for actual
disaster recovery.

## Automated verification

```bash
python manage.py verify_backup
```

Dumps the live database, restores it into a throwaway database, checks
that row counts roughly match, then cleans up. This is what actually
proves a backup is usable — `pg_dump` exiting 0 only proves the dump
*ran*, not that the result restores cleanly. Schedule this to run
regularly (e.g. weekly) against a non-production replica, or in a
low-traffic window; it never writes to the live database.

Needs `PG_ADMIN_USER`/`PG_ADMIN_PASSWORD` env vars (falls back to the
app's own `DB_USER`/`DB_PASSWORD` if unset) — the verification database
create/drop step needs `CREATEDB`, which the scoped `travelcrm_app` role
intentionally does not have.

## The scoped app role (`travelcrm_app`)

Row-Level Security only applies to a role that neither owns the tables nor is a superuser, so the
running app connects as `travelcrm_app` while migrations run as the admin/owner.
`init-scoped-role.sql` creates that role, sets its password and grants it access to every current
and future table/sequence (via `ALTER DEFAULT PRIVILEGES`, so later migrations need no extra step):

```bash
psql -U postgres -d travelcrm -v app_password='...' -f scripts/init-scoped-role.sql
```

Run it as the admin that runs `migrate`. It is safe to re-run. In Docker
(`docker-compose.prod.yml`) `init-scoped-role.sh` runs it automatically on the first start of a fresh
database volume, using `DB_PASSWORD`; CI runs the same file.
