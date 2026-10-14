"""
The fixed set of capabilities a non-superuser platform staff account
(StaffAccess) can be granted. Mirrors rbac/catalog.py's shape, but scoped
to platform-level operations rather than tenant-internal ones — a real
Django superuser bypasses this catalog entirely (see
platform_admin/decorators.py::platform_staff_required), the same way
rbac/engine.py::has_capability() short-circuits for is_superuser.
"""
from django.utils.translation import gettext_lazy

CAPABILITIES = [
    ("tenants.view", gettext_lazy("View tenants")),
    ("tenants.manage", gettext_lazy("Manage tenants (create, suspend, reactivate, announcements)")),
    ("billing.view", gettext_lazy("View billing (plans, payments, subscriptions)")),
    ("billing.manage", gettext_lazy("Manage billing (plans, confirm/reject payments, assign subscriptions)")),
    ("analytics.view", gettext_lazy("View analytics")),
    ("audit.view", gettext_lazy("View audit log")),
    ("system_config.manage", gettext_lazy("Manage system configuration, email templates, API keys")),
]

CAPABILITY_KEYS = {key for key, _label in CAPABILITIES}
