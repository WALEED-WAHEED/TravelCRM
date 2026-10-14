from django.db import migrations

from rbac.catalog import LEGACY_ROLE_TEMPLATE


def backfill(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Role = apps.get_model('rbac', 'Role')

    templates = {
        role.name: role
        for role in Role.objects.filter(agency__isnull=True, is_template=True)
    }
    for legacy_role, template_name in LEGACY_ROLE_TEMPLATE.items():
        template = templates.get(template_name)
        if not template:
            continue
        User.objects.filter(role=legacy_role, custom_role__isnull=True).update(custom_role=template)

    # Anything left over (unexpected role value) gets the lowest-privilege
    # template rather than staying unassigned.
    fallback = templates.get('Read-only')
    if fallback:
        User.objects.filter(custom_role__isnull=True).exclude(is_superuser=True).update(custom_role=fallback)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_custom_role'),
        ('rbac', '0002_seed_catalog'),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=noop_reverse),
    ]
