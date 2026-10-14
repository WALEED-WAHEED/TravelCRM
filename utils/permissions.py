from rest_framework import permissions

from rbac.engine import role_level

# Matches rbac.catalog.TEMPLATE_LEVELS — see member/decorators.py for the
# same bridge on the template-view side. These are coarse "at least this
# senior" checks; prefer rbac.engine.has_capability() for anything new.
MEMBER_TIER_LEVEL = 75
AGENT_TIER_LEVEL = 10


class IsSuperAdmin(permissions.BasePermission):
    """
    Platform-level access only — the Super Admin, not any tenant's
    'member' role. Backs the global/cross-tenant endpoints (platform
    branding, global API keys, the platform-wide audit log) that must
    never be reachable by an ordinary agency owner.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsMember(permissions.BasePermission):
    """Manager-tier or above (owns/runs the agency) — the old 'member' role."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and role_level(request.user) >= MEMBER_TIER_LEVEL


class IsAgent(permissions.BasePermission):
    """Agent-tier specifically (not Manager/Owner) — the old 'agent' role. Unused by any view today; kept for compatibility."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        level = role_level(request.user)
        return AGENT_TIER_LEVEL <= level < MEMBER_TIER_LEVEL


class IsMemberOrAgent(permissions.BasePermission):
    """Any assigned tenant role at all — the old 'member' or 'agent' role."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and role_level(request.user) >= AGENT_TIER_LEVEL


class IsOwnerOrMember(permissions.BasePermission):
    """
    Permission class for object-level permissions
    - Manager-tier+ can access all agency data
    - Everyone else can only access their own data
    """
    def has_object_permission(self, request, view, obj):
        if role_level(request.user) >= MEMBER_TIER_LEVEL:
            if hasattr(obj, 'agency'):
                return obj.agency == request.user.agency
            return False

        if hasattr(obj, 'agent'):
            return obj.agent == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        return False


class IsSameAgency(permissions.BasePermission):
    """
    Ensure the user belongs to the same agency as the object
    """
    def has_object_permission(self, request, view, obj):
        # Check if object belongs to user's agency
        if hasattr(obj, 'agency'):
            return obj.agency == request.user.agency

        return False


class IsOwner(permissions.BasePermission):
    """
    Only the owner/creator of the object can access it
    """
    def has_object_permission(self, request, view, obj):
        # Check various owner fields
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'agent'):
            return obj.agent == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user

        return False
