"""
Role-based access decorators.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def role_required(*roles):
    """Restrict view to users with specific roles."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='/login/')
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                redirect_map = {
                    'member': '/member/dashboard/',
                    'agent': '/agent/dashboard/',
                }
                return redirect(redirect_map.get(request.user.role, '/login/'))
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def member_required(view_func):
    return role_required('member')(view_func)

def agent_required(view_func):
    return role_required('agent', 'member')(view_func)
