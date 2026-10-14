"""
The standalone Reports page is gone (every section has its own insights), but
the `reports` capability also guarded the Activity Log. It is renamed to
`activity_log` in place, so every role keeps exactly the access it had.

A fresh database never sees the old key: 0002 seeds from rbac/catalog.py live.
"""
from django.db import migrations


def rename(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    if Permission.objects.filter(capability='activity_log').exists():
        # Already seeded under the new key (fresh install): drop any stale rows.
        Permission.objects.filter(capability='reports').delete()
        return
    Permission.objects.filter(capability='reports').update(capability='activity_log')


def unrename(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    Permission.objects.filter(capability='activity_log').update(capability='reports')


class Migration(migrations.Migration):

    dependencies = [
        ('rbac', '0004_remove_accountant_template'),
    ]

    operations = [
        migrations.RunPython(rename, reverse_code=unrename),
    ]
