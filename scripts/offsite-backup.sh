#!/bin/bash
# Nightly off-site backup for docker-compose.prod.yml (the `backup` service): dumps the database with
# backup.sh, keeps 14 copies on the server, and sends an encrypted copy of each dump plus the uploaded
# images to Cloudflare R2 (any S3-compatible bucket works). Encryption is rclone `crypt` with
# BACKUP_PASSPHRASE, done on this server before upload: the bucket only ever holds unreadable files,
# and without the passphrase the backups cannot be restored.
#
#   schedule                      (default) back up every day at BACKUP_TIME (UTC, HH:MM)
#   now                           back up once, immediately
#   list                          list the dumps stored in R2
#   restore <file|latest> [--force-target]
#                                 download a dump from R2 and restore it with restore.sh. Without
#                                 --force-target it goes into a throwaway <DB_NAME>_restore_test database
#                                 (safe test); with it, the real database and the images are replaced.
#
# Run the one-off commands with:  docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backup <command>
set -euo pipefail

: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_HOST:=db}"
: "${BACKUP_TIME:=21:00}"            # UTC; 21:00 UTC = 02:00 in Pakistan
: "${BACKUP_KEEP:=14}"
LOCAL_DIR=/backups
MEDIA_DIR=/app/media

offsite_enabled() { [ -n "${R2_BUCKET:-}" ]; }

if offsite_enabled; then
  : "${BACKUP_PASSPHRASE:?BACKUP_PASSPHRASE is required when R2_BUCKET is set}"
  # `r2` is the bucket, `secure` encrypts everything written through it.
  export RCLONE_CONFIG_R2_TYPE="${RCLONE_CONFIG_R2_TYPE:-s3}"
  export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
  export RCLONE_CONFIG_R2_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID:-}"
  export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY:-}"
  export RCLONE_CONFIG_R2_ENDPOINT="${R2_ENDPOINT:-}"
  export RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true      # bucket-scoped R2 tokens cannot create buckets
  export RCLONE_CONFIG_SECURE_TYPE=crypt
  export RCLONE_CONFIG_SECURE_REMOTE="r2:${R2_BUCKET}"
  RCLONE_CONFIG_SECURE_PASSWORD="$(rclone obscure "$BACKUP_PASSPHRASE")"
  export RCLONE_CONFIG_SECURE_PASSWORD
fi

log() { echo "[backup $(date -u '+%F %T') UTC] $*"; }

backup_once() {
  bash /scripts/backup.sh "$LOCAL_DIR"
  local dump
  dump=$(ls -1t "$LOCAL_DIR"/travelcrm_*.dump | head -n 1)
  if offsite_enabled; then
    rclone copy "$dump" secure:db/ --retries 5
    # Keep the newest BACKUP_KEEP dumps in R2 (names sort by date). Only reached after a successful upload.
    rclone lsf secure:db/ --files-only | sort -r | tail -n +"$((BACKUP_KEEP + 1))" | while read -r old; do
      rclone deletefile "secure:db/$old" && log "pruned $old from R2"
    done
    # Images: only new files are uploaded; files deleted on the server stay in R2.
    rclone copy "$MEDIA_DIR" secure:media/ --retries 5
    log "uploaded $(basename "$dump") and images to R2 bucket '$R2_BUCKET'"
  else
    log "WARNING: R2_BUCKET is not set; the dump is kept on this server only"
  fi
  touch "$LOCAL_DIR/last-success"
}

# A separate process, so `set -e` still stops a failing backup (it is ignored inside an `if` condition).
run_logged() {
  bash "$0" now || log "ERROR: backup FAILED (see above)"
}

case "${1:-schedule}" in
  schedule)
    log "scheduled daily at $BACKUP_TIME UTC, keeping $BACKUP_KEEP copies"
    # Back up straight away unless a recent one exists (e.g. after a redeploy).
    if [ -z "$(find "$LOCAL_DIR/last-success" -mmin -1200 2>/dev/null)" ]; then run_logged; fi
    last_day=""
    while true; do
      if [ "$(date -u +%H:%M)" = "$BACKUP_TIME" ] && [ "$last_day" != "$(date -u +%F)" ]; then
        last_day=$(date -u +%F)
        run_logged
      fi
      sleep 30
    done
    ;;
  now)
    backup_once
    log "backup OK"
    ;;
  list)
    offsite_enabled || { echo "R2_BUCKET is not set"; exit 1; }
    rclone lsl secure:db/ | sort -k4
    ;;
  restore)
    offsite_enabled || { echo "R2_BUCKET is not set"; exit 1; }
    name="${2:?Usage: restore <file|latest> [--force-target]}"
    [ "$name" = latest ] && name=$(rclone lsf secure:db/ --files-only | sort | tail -n 1)
    [ -n "$name" ] || { echo "No dumps in R2"; exit 1; }
    mkdir -p "$LOCAL_DIR/restore"
    rclone copy "secure:db/$name" "$LOCAL_DIR/restore/"
    log "downloaded $name"
    bash /scripts/restore.sh "$LOCAL_DIR/restore/$name" "${3:-}"
    if [ "${3:-}" = "--force-target" ]; then
      # A recreated database has lost the travelcrm_app grants; re-apply them.
      PGPASSWORD="${DB_PASSWORD:-}" psql -v ON_ERROR_STOP=1 -v app_password="${APP_DB_PASSWORD:?APP_DB_PASSWORD is required}" \
        --host="$DB_HOST" --username="$DB_USER" --dbname="$DB_NAME" -f /scripts/init-scoped-role.sql
      rclone copy secure:media/ "$MEDIA_DIR"
      log "database and images restored; start the app again"
    fi
    rm -f "$LOCAL_DIR/restore/$name"
    ;;
  *)
    echo "Unknown command: $1 (schedule | now | list | restore <file|latest> [--force-target])"
    exit 1
    ;;
esac
