#!/bin/sh
# Postgres image init hook (mounted into /docker-entrypoint-initdb.d/, runs once on a fresh data volume):
# creates the scoped role the app runs as, with the password from APP_DB_PASSWORD.
set -e
psql -v ON_ERROR_STOP=1 -v app_password="$APP_DB_PASSWORD" \
     --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -f /scripts/init-scoped-role.sql
