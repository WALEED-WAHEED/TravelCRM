from django.db import models

from agencies.models import Agency
from utils.tenancy import TenantOrGlobalManager, UnscopedManager


class Permission(models.Model):
    """One row per (capability, action) — a fixed, seeded catalog. See
    rbac/catalog.py for the list; not meant to be created ad hoc."""
    capability = models.CharField(max_length=50)
    action = models.CharField(max_length=20)

    class Meta:
        ordering = ['capability', 'action']
        constraints = [
            models.UniqueConstraint(fields=['capability', 'action'], name='rbac_permission_unique_capability_action'),
        ]

    def __str__(self):
        return f"{self.capability}:{self.action}"


class Role(models.Model):
    """
    A named permission bundle. `agency=None` marks one of the four global
    templates (Owner/Manager/Agent/Read-only) — read-only,
    shared by every tenant. `agency=<tenant>` marks that tenant's own
    role, either cloned from a template and then adjusted, or built from
    scratch; capped at MAX_CUSTOM_ROLES_PER_AGENCY (see catalog.py) so a
    tenant can't accumulate an unmanageable pile of near-duplicate roles.
    """
    name = models.CharField(max_length=100)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, null=True, blank=True, related_name='roles')
    is_template = models.BooleanField(default=False)
    cloned_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='clones')
    level = models.PositiveIntegerField(
        default=10,
        help_text="Coarse seniority ranking (0-100). Only used to bridge legacy pages not yet retrofit to per-capability checks.",
    )
    permissions = models.ManyToManyField(Permission, related_name='roles', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantOrGlobalManager()
    all_tenants = UnscopedManager()

    class Meta:
        ordering = ['-level', 'name']
        base_manager_name = 'all_tenants'
        constraints = [
            models.UniqueConstraint(fields=['agency', 'name'], name='rbac_role_unique_name_per_agency'),
        ]

    def __str__(self):
        return f"{self.name}" + (" (template)" if self.is_template else f" — {self.agency.name}" if self.agency_id else "")

    def grants(self, capability, action):
        if action == 'view':
            return self.permissions.filter(capability=capability, action__in=['view', 'manage']).exists()
        return self.permissions.filter(capability=capability, action=action).exists()
