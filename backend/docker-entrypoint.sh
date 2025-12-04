#!/bin/bash
# Don't use set -e, we want to handle errors gracefully
set +e

echo "=========================================="
echo "Backend Container Starting..."
echo "=========================================="

# Wait for database to be ready
echo "Waiting for database to be ready..."
python << 'END'
import sys
import time
import psycopg2
from os import getenv

def wait_for_db():
    max_attempts = 30
    for i in range(max_attempts):
        try:
            conn = psycopg2.connect(
                dbname=getenv("POSTGRES_DB", "travelcrm"),
                user=getenv("POSTGRES_USER", "postgres"),
                password=getenv("POSTGRES_PASSWORD", "password"),
                host=getenv("POSTGRES_HOST", "db"),
                port=getenv("POSTGRES_PORT", "5432"),
                connect_timeout=5
            )
            conn.close()
            print("✓ Database is ready!")
            return True
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            if i < max_attempts - 1:
                print(f"Waiting for database... ({i+1}/{max_attempts})")
                time.sleep(2)
            else:
                print(f"✗ Database connection failed after maximum attempts: {e}")
                return False
    return False

if not wait_for_db():
    print("ERROR: Could not connect to database. Exiting.")
    sys.exit(1)
END

DB_READY=$?
if [ $DB_READY -ne 0 ]; then
    echo "FATAL: Database connection failed. Exiting."
    exit 1
fi

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

