from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def superadmin_required(view_func):
    """Restrict a view to a real Django superuser — unconditional, no
    capability can substitute for this. Reserved for the handful of
    bootstrap-sensitive views (granting/revoking other staff access)
    where "root only" is the point."""
    @wraps(view_func)
    @login_required(login_url='/login/')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("Super Admin access required.")
        return view_func(request, *args, **kwargs)
    return wrapper


def platform_staff_required(capability):
    """
    Restrict a view to a real superuser (always passes, same as
    superadmin_required — mirrors rbac/engine.py::has_capability()'s
    "root bypasses the permission system" shape) OR a non-superuser
    is_staff account holding the given capability via StaffAccess.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='/login/')
        def wrapper(request, *args, **kwargs):
            user = request.user
            if user.is_superuser:
                return view_func(request, *args, **kwargs)
            if user.is_staff:
                from .models import StaffAccess
                access = StaffAccess.objects.filter(user=user).first()
                if access and capability in access.capabilities:
                    return view_func(request, *args, **kwargs)
            raise PermissionDenied("You don't have access to this part of the Super Admin panel.")
        return wrapper
    return decorator


def has_platform_capability(user, capability):
    """Same rule as platform_staff_required, usable outside a view (e.g.
    in a template context processor for nav visibility)."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False
    from .models import StaffAccess
    access = StaffAccess.objects.filter(user=user).first()
    return bool(access and capability in access.capabilities)
