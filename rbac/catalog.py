"""
The single source of truth for what a role can grant, and what the four
default templates grant out of the box. Used by the seeding migration
(rbac/migrations/0002...), the permission engine (rbac/engine.py), and
the Team & Roles UI — nowhere else should hard-code a capability name.

Capabilities are deliberately coarse ("bookings", not "bookings.void" /
"bookings.discount" / ...) — per-capability view/manage is enough to stop
role micro-variation sprawl while still letting an agency owner keep an
agent out of the ledger.
"""
from django.utils.translation import gettext_lazy

# Note: don't alias gettext_lazy as `_` in this file — `_` is reused
# below as a throwaway loop variable (`for cap, _ in CAPABILITIES`),
# which would silently shadow the translation function.

CAPABILITIES = [
    ("bookings", gettext_lazy("Bookings")),
    ("vouchers", gettext_lazy("Vouchers")),
    ("hotels", gettext_lazy("Hotel inventory")),
    ("flights", gettext_lazy("Flight inventory")),
    ("transports", gettext_lazy("Transport inventory")),
    ("contacts", gettext_lazy("Contacts")),
    ("ledger", gettext_lazy("Ledger / accounting")),
    ("attendance", gettext_lazy("Attendance")),
    ("reports", gettext_lazy("Reports")),
    ("team", gettext_lazy("Team & roles")),
    ("agency_settings", gettext_lazy("Agency settings")),
]

ACTIONS = [
    ("view", gettext_lazy("View")),
    ("manage", gettext_lazy("Manage (create, edit, delete)")),
]

_ALL_VIEW = {cap: {"view"} for cap, _ in CAPABILITIES}
_ALL_FULL = {cap: {"view", "manage"} for cap, _ in CAPABILITIES}

# name -> {capability: {actions granted}}
TEMPLATES = {
    "Owner": _ALL_FULL,
    "Manager": {
        **{cap: {"view", "manage"} for cap in [
            "bookings", "vouchers", "hotels", "flights",
            "transports", "contacts", "ledger", "attendance", "reports",
        ]},
        "team": {"view"},
        "agency_settings": set(),
    },
    "Agent": {
        **{cap: {"view", "manage"} for cap in ["bookings", "vouchers"]},
        **{cap: {"view"} for cap in ["hotels", "flights", "transports", "contacts", "attendance"]},
        "ledger": set(), "reports": set(), "team": set(), "agency_settings": set(),
    },
    "Read-only": _ALL_VIEW,
}

# Coarse seniority ranking. Only exists to bridge the legacy
# member_required/agent_required decorators and IsMember/IsAgent DRF
# permission classes onto real role data without having to retrofit
# every one of the ~30 existing views to a specific capability check in
# this same pass — new screens should use has_capability() directly.
TEMPLATE_LEVELS = {
    "Owner": 100,
    "Manager": 75,
    "Agent": 25,
    "Read-only": 10,
}

# How pre-Phase-02 accounts.User.role values map onto the new templates,
# used once by the data migration that assigns every existing user a
# real Role, and as a defensive fallback for any user that somehow still
# has no custom_role.
LEGACY_ROLE_TEMPLATE = {
    "member": "Owner",
    "agent": "Agent",
    "admin": "Owner",
}

MAX_CUSTOM_ROLES_PER_AGENCY = 10
