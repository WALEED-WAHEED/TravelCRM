"""
Removes the "Accountant" role template. It's gone from rbac/catalog.py's
TEMPLATES/TEMPLATE_LEVELS as of this change (fresh installs never seed
it — see 0002_seed_catalog.py, which reads catalog.py live), but an
already-migrated database still has the row from when 0002 ran, so it
needs an explicit removal here.

Any user (or tenant-cloned custom Role) still pointing at the Accountant
template is reassigned to Agent — the same tier Accountant users already
landed in on the coarse `role` field (rbac/views.py's
`role = 'member' if template.level >= 75 else 'agent'`; Accountant's
level was 50), so this doesn't change what such a user could already do
via has_capability(), just which named role/custom_role_id they show.
"""
from django.db import migrations


def remove_accountant(apps, schema_editor):
    Role = apps.get_model('rbac', 'Role')
    User = apps.get_model('accounts', 'User')

    accountant = Role.objects.filter(agency__isnull=True, is_template=True, name='Accountant').first()
    if not accountant:
        return
    agent_template = Role.objects.filter(agency__isnull=True, is_template=True, name='Agent').first()

    User.objects.filter(custom_role=accountant).update(custom_role=agent_template)
    # Tenant-owned Roles cloned from Accountant keep their own permission
    # set (cloning copies permissions, it doesn't stay linked) — only the
    # traceability pointer needs to move so it doesn't dangle.
    Role.objects.filter(cloned_from=accountant).update(cloned_from=agent_template)

    accountant.delete()


def restore_accountant(apps, schema_editor):
    """Reverse migration: not restoring the role — if you're rolling back
    this far, re-run rbac's seed migration logic manually instead."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('rbac', '0003_row_level_security'),
        ('accounts', '0006_user_preferred_language'),
    ]

    operations = [
        migrations.RunPython(remove_accountant, reverse_code=restore_accountant),
    ]
