from rest_framework import permissions


class IsDeveloper(permissions.BasePermission):
    """
    Permission class that allows only users with 'developer' role
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'developer'


class IsMember(permissions.BasePermission):
    """
    Permission class that allows only users with 'member' role
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'member'


class IsAgent(permissions.BasePermission):
    """
    Permission class that allows only users with 'agent' role
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'agent'


class IsMemberOrAgent(permissions.BasePermission):
    """
    Permission class that allows users with 'member' or 'agent' role
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['member', 'agent']


class IsOwnerOrMember(permissions.BasePermission):
    """
    Permission class for object-level permissions
    - Members can access all agency data
    - Agents can only access their own data
    """
    def has_object_permission(self, request, view, obj):
        # Developers have full access
        if request.user.role == 'developer':
            return True
        
        # Members can access all agency data
        if request.user.role == 'member':
            # Check if object has agency attribute
            if hasattr(obj, 'agency'):
                return obj.agency == request.user.agency
            return False
        
        # Agents can only access their own data
        if request.user.role == 'agent':
            # Check if the object was created by the agent
            if hasattr(obj, 'agent'):
                return obj.agent == request.user
            if hasattr(obj, 'created_by'):
                return obj.created_by == request.user
            return False
        
        return False


class IsSameAgency(permissions.BasePermission):
    """
    Ensure the user belongs to the same agency as the object
    """
    def has_object_permission(self, request, view, obj):
        # Developers can access everything
        if request.user.role == 'developer':
            return True
        
        # Check if object belongs to user's agency
        if hasattr(obj, 'agency'):
            return obj.agency == request.user.agency
        
        return False


class IsOwner(permissions.BasePermission):
    """
    Only the owner/creator of the object can access it
    """
    def has_object_permission(self, request, view, obj):
        # Developers can access everything
        if request.user.role == 'developer':
            return True
        
        # Check various owner fields
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'agent'):
            return obj.agent == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False

