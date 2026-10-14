"""
Role-based access decorators.

Backed by rbac.engine (see rbac/engine.py) rather than a raw string
comparison on request.user.role, so template-view access control and
the DRF permission classes in utils/permissions.py share one
authorization source. member_required/agent_required are a coarse,
seniority-level bridge for the ~30 existing views that predate the
per-capability rbac system (Phase 02) — new views should prefer
rbac.decorators.permission_required(capability, action) instead.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from rbac.engine import role_level

# Matches rbac.catalog.TEMPLATE_LEVELS: Owner=100, Manager=75,
# Agent=25, Read-only=10.
MEMBER_TIER_LEVEL = 75
AGENT_TIER_LEVEL = 10


def _level_required(min_level):
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='/login/')
        def wrapper(request, *args, **kwargs):
            if role_level(request.user) < min_level:
                redirect_map = {
                    'member': '/member/dashboard/',
                    'agent': '/agent/dashboard/',
                }
                return redirect(redirect_map.get(request.user.role, '/login/'))
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def role_required(*roles):
    """Legacy signature kept for any external caller; maps straight onto
    the level bridge (member -> Manager/Owner tier, agent -> any tier)."""
    min_level = MEMBER_TIER_LEVEL if 'member' in roles and 'agent' not in roles else AGENT_TIER_LEVEL
    return _level_required(min_level)


def member_required(view_func):
    return _level_required(MEMBER_TIER_LEVEL)(view_func)

def agent_required(view_func):
    return _level_required(AGENT_TIER_LEVEL)(view_func)
