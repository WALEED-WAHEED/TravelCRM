from django.db import migrations

from rbac.catalog import CAPABILITIES, TEMPLATES, TEMPLATE_LEVELS


def seed(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    Role = apps.get_model('rbac', 'Role')

    perm_by_key = {}
    for capability, _label in CAPABILITIES:
        for action in ('view', 'manage'):
            perm, _ = Permission.objects.get_or_create(capability=capability, action=action)
            perm_by_key[(capability, action)] = perm

    for name, grants in TEMPLATES.items():
        role, _ = Role.objects.get_or_create(
            agency=None, name=name,
            defaults={'is_template': True, 'level': TEMPLATE_LEVELS[name]},
        )
        role.is_template = True
        role.level = TEMPLATE_LEVELS[name]
        role.save()
        perm_ids = [
            perm_by_key[(capability, action)].id
            for capability, actions in grants.items()
            for action in actions
        ]
        role.permissions.set(perm_ids)


def unseed(apps, schema_editor):
    Role = apps.get_model('rbac', 'Role')
    Permission = apps.get_model('rbac', 'Permission')
    Role.objects.filter(agency__isnull=True, is_template=True, name__in=list(TEMPLATES.keys())).delete()
    Permission.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('rbac', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]
