#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelcrm.settings')
django.setup()

from django.db import connection

def fix_migration_history():
    """Fix migration history by inserting missing agencies migration"""
    with connection.cursor() as cursor:
        # Check if agencies migration exists
        cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app='agencies' AND name='0001_initial'")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insert the agencies migration record
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied)
                VALUES ('agencies', '0001_initial', NOW());
            """)
            print("Fixed migration history - inserted agencies migration")
        else:
            print("Agencies migration already exists")

if __name__ == "__main__":
    fix_migration_history()
