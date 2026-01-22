#!/bin/bash
# Don't use set -e, we want to handle errors gracefully
set +e

echo "=========================================="
echo "Backend Container Starting..."
echo "=========================================="

# Wait for database to be ready
# Database wait logic removed for SQLite usage
DB_READY=0
# if [ $DB_READY -ne 0 ]; then
#     echo "FATAL: Database connection failed. Exiting."
#     exit 1
# fi

# Run database migrations
echo ""
echo "Running database migrations..."
python manage.py migrate --noinput
MIGRATE_STATUS=$?
if [ $MIGRATE_STATUS -ne 0 ]; then
    echo "WARNING: Migrations failed (exit code: $MIGRATE_STATUS), but continuing..."
fi

# Collect static files
echo ""
echo "Collecting static files..."
python manage.py collectstatic --noinput
STATIC_STATUS=$?
if [ $STATIC_STATUS -ne 0 ]; then
    echo "WARNING: Static file collection failed (exit code: $STATIC_STATUS), but continuing..."
fi

# Verify Django can start (non-critical check)
echo ""
echo "Verifying Django configuration..."
python manage.py check --deploy 2>/dev/null || {
    echo "INFO: Django check completed (warnings are acceptable)"
}

echo ""
echo "=========================================="
echo "Starting server..."
echo "=========================================="

# Use set -e for the actual server command
set -e
exec "$@"

