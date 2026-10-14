"""
The one place that answers "can this user do X" — used by both the
template-view decorators (rbac/decorators.py, member/decorators.py) and
the DRF permission classes (utils/permissions.py), so there is a single
authorization code path instead of the old me two-decorator/permission-
class systems each re-implementing their own role check.
"""
from functools import lru_cache

from .catalog import LEGACY_ROLE_TEMPLATE
from .models import Role


@lru_cache(maxsize=8)
def _template_role(name):
    """Global templates are static seed data — safe to cache per-process."""
    return Role.all_tenants.filter(agency__isnull=True, is_template=True, name=name).first()


def get_effective_role(user):
    """The Role that actually governs this user's access right now."""
    if not getattr(user, 'is_authenticated', False):
        return None
    if getattr(user, 'custom_role_id', None):
        return user.custom_role
    template_name = LEGACY_ROLE_TEMPLATE.get(getattr(user, 'role', None))
    if template_name:
        return _template_role(template_name)
    return None


def has_capability(user, capability, action):
    """action: 'view' or 'manage'. Superusers always pass (platform admin,
    not a tenant role)."""
    if getattr(user, 'is_superuser', False):
        return True
    role = get_effective_role(user)
    if role is None:
        return False
    return role.grants(capability, action)


def role_level(user):
    """Coarse seniority (0-100) — only for bridging legacy pages; prefer
    has_capability() for anything new."""
    if getattr(user, 'is_superuser', False):
        return 100
    role = get_effective_role(user)
    if role is None:
        return 0
    return role.level
