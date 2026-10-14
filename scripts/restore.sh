#!/bin/bash
# Restores a backup produced by scripts/backup.sh into a database.
# Defaults to restoring into a throwaway `<DB_NAME>_restore_test`
# database rather than overwriting the real one — pass --force-target
# to restore directly into DB_NAME instead (destructive; drops existing
# data in that database first).
#
# Usage: DB_NAME=... DB_USER=postgres DB_PASSWORD=... DB_HOST=... ./scripts/restore.sh path/to/backup.dump [--force-target]
set -euo pipefail

DUMP_FILE="${1:?Usage: restore.sh path/to/backup.dump [--force-target]}"
FORCE_TARGET="${2:-}"

: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_HOST:=localhost}"
: "${DB_PORT:=5432}"

if [ "$FORCE_TARGET" = "--force-target" ]; then
  TARGET_DB="$DB_NAME"
  echo "WARNING: restoring directly into '$TARGET_DB' — this drops and recreates it."
  read -p "Type the database name to confirm: " CONFIRM
  if [ "$CONFIRM" != "$TARGET_DB" ]; then
    echo "Confirmation did not match. Aborting."
    exit 1
  fi
else
  TARGET_DB="${DB_NAME}_restore_test"
  echo "Restoring into throwaway database '$TARGET_DB' (pass --force-target to overwrite '$DB_NAME' instead)."
fi

export PGPASSWORD="${DB_PASSWORD:-}"

dropdb --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --if-exists "$TARGET_DB"
createdb --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" "$TARGET_DB"

pg_restore \
  --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
  --no-owner --no-privileges --dbname="$TARGET_DB" "$DUMP_FILE"

echo "Restored '$DUMP_FILE' into '$TARGET_DB'."
if [ "$TARGET_DB" != "$DB_NAME" ]; then
  echo "This was a throwaway restore-test database — verify it, then drop it:"
  echo "  dropdb --host=$DB_HOST --port=$DB_PORT --username=$DB_USER $TARGET_DB"
fi
