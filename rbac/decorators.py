from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .engine import has_capability


def permission_required(capability, action='view'):
    """Fine-grained template-view gate: @permission_required('ledger', 'manage')."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='/login/')
        def wrapper(request, *args, **kwargs):
            if not has_capability(request.user, capability, action):
                raise PermissionDenied(f"Requires {capability}:{action}.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
