#!/bin/bash
# Dumps the Postgres database to a timestamped, compressed custom-format
# file. Run as the `postgres` admin credentials (or any role with SELECT
# on everything), not the scoped `travelcrm_app` runtime role.
#
# Usage: DB_NAME=... DB_USER=postgres DB_PASSWORD=... DB_HOST=... ./scripts/backup.sh [output_dir]
set -euo pipefail

OUTPUT_DIR="${1:-./backups}"
mkdir -p "$OUTPUT_DIR"

: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_HOST:=localhost}"
: "${DB_PORT:=5432}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTFILE="$OUTPUT_DIR/travelcrm_${TIMESTAMP}.dump"

echo "Backing up $DB_NAME@$DB_HOST:$DB_PORT -> $OUTFILE"
PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
  --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
  --format=custom --no-owner --no-privileges \
  --file="$OUTFILE" "$DB_NAME"

SIZE=$(stat -c%s "$OUTFILE" 2>/dev/null || stat -f%z "$OUTFILE")
echo "Done: $OUTFILE ($SIZE bytes)"

# Keep the last 14 backups in this directory, prune older ones.
ls -1t "$OUTPUT_DIR"/travelcrm_*.dump 2>/dev/null | tail -n +15 | xargs -r rm -v
