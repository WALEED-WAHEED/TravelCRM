"""
Generic audit trail: every create/update/delete on a registered model is
recorded automatically via signals, with a field-level diff for updates.
No view needs to remember to call anything — that was the point (a
hand-maintained "remember to log this" convention is exactly the kind of
thing that gets forgotten under deadline pressure).

Wiring: register_audited_models() is called once from
system_config/apps.py's ready(); the "current actor" (user, IP, user
agent) is supplied by TenantMiddleware via set_current_actor(), since
signal receivers have no access to the request.
"""
import contextvars
import datetime
import decimal

from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.forms.models import model_to_dict

_current_actor = contextvars.ContextVar("audit_current_actor", default=(None, None, ""))

# Agency ids currently mid-delete in this thread/task — see
# _pre_delete_agency and _resolve_agency_id below.
_agencies_being_deleted = contextvars.ContextVar("audit_agencies_being_deleted", default=frozenset())

EXCLUDED_FIELDS = {
    "password", "created_at", "updated_at",
    # Bumped on every sign-in, before the request knows who the actor is —
    # logging it buried real changes under anonymous "User updated" rows.
    "last_login",
    # Secrets that must never land in an AuditLog.changes JSON diff.
    "api_key", "api_secret", "attendance_admin_password_hash",
}


def set_current_actor(user, ip_address, user_agent):
    _current_actor.set((user, ip_address, user_agent or ""))


def clear_current_actor():
    _current_actor.set((None, None, ""))


def _jsonable(value):
    if isinstance(value, (decimal.Decimal,)):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _snapshot(instance):
    try:
        return {
            field: _jsonable(value)
            for field, value in model_to_dict(instance).items()
            if field not in EXCLUDED_FIELDS
        }
    except Exception:
        return {}


def _resolve_agency_id(instance, deleted=False):
    from agencies.models import Agency
    if isinstance(instance, Agency):
        # A deleted Agency can't be its own FK target. Log it as a
        # platform-level entry (agency=NULL) instead — Super Admin still
        # sees it via bypass; object_repr already records which agency
        # it was.
        return None if deleted else instance.pk

    # Read the cached FK id directly rather than `instance.agency` — the
    # latter is a descriptor that runs a fresh SELECT if the relation
    # wasn't pre-fetched, which raises Agency.DoesNotExist once the
    # Agency itself has been deleted in the same cascade (see below).
    agency_id = getattr(instance, "agency_id", None)
    if agency_id is None:
        return None
    if deleted and agency_id in _agencies_being_deleted.get():
        # Deleting a whole tenant cascades to every dependent row —
        # Hotel, Booking, User, etc. — each of which would otherwise log
        # a "delete" entry that still points at the Agency about to
        # disappear in this same transaction. Django's own on_delete=
        # SET_NULL only clears *pre-existing* AuditLog rows when the
        # collector runs; it can't know about rows this very signal is
        # about to insert. _pre_delete_agency (below) records which
        # agencies are currently being deleted before any DELETE
        # statement runs, so this is known upfront rather than raced
        # against — an existence check here would still see the Agency
        # as "not yet deleted", since children are removed before their
        # parent, and only fail once the Agency's own DELETE lands a
        # moment later in the same transaction.
        return None
    return agency_id


def _pre_delete_agency(sender, instance, **kwargs):
    _agencies_being_deleted.set(_agencies_being_deleted.get() | {instance.pk})


def _write(action, instance, changes=None):
    from system_config.models import AuditLog

    user, ip_address, user_agent = _current_actor.get()
    try:
        repr_ = str(instance)[:200]
    except Exception:
        # __str__ on some models (e.g. LedgerEntry: f"...{self.agency.name}")
        # dereferences a related object that can be gone for the same
        # already-deleted-mid-cascade reason as _resolve_agency_id above.
        repr_ = f"{instance.__class__.__name__} #{instance.pk}"
    AuditLog.all_tenants.create(
        user=user if user and getattr(user, "is_authenticated", False) else None,
        agency_id=_resolve_agency_id(instance, deleted=(action == "delete")),
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(instance.pk),
        object_repr=repr_,
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )


def log_event(instance, changes, action="update"):
    """Record a change the field-level signals cannot see (e.g. a voucher's hotels, flights or travellers
    being replaced). `changes` is {label: {"old": text, "new": text}}."""
    if changes:
        _write(action, instance, changes)


def _pre_save(sender, instance, **kwargs):
    if not instance.pk:
        instance._audit_old_snapshot = None
        return
    # Not every audited model has an `all_tenants` escape-hatch manager —
    # User deliberately doesn't (it must stay globally queryable for
    # login, independent of tenant context). Fall back to the model's
    # own default manager rather than assuming all_tenants exists.
    manager = getattr(sender, 'all_tenants', None) or sender._default_manager
    try:
        old = manager.get(pk=instance.pk)
        instance._audit_old_snapshot = _snapshot(old)
    except sender.DoesNotExist:
        instance._audit_old_snapshot = None


def _post_save(sender, instance, created, **kwargs):
    if created:
        _write("create", instance)
        return
    old = getattr(instance, "_audit_old_snapshot", None)
    if old is None:
        return
    new = _snapshot(instance)
    changes = {
        field: {"old": old.get(field), "new": new_val}
        for field, new_val in new.items()
        if old.get(field) != new_val
    }
    if changes:
        _write("update", instance, changes)


def _post_delete(sender, instance, **kwargs):
    from agencies.models import Agency

    _write("delete", instance)
    if isinstance(instance, Agency):
        # Per-model batches are deleted in FK-dependency order — every
        # dependent row (Hotel, Booking, User, ...) is removed, and its
        # post_delete fired, before the Agency itself is; this always
        # runs last for a given agency's cascade, so it's safe to clear
        # here rather than needing a try/finally around the whole delete().
        _agencies_being_deleted.set(_agencies_being_deleted.get() - {instance.pk})


def register_audited_models():
    from accounts.models import User
    from agencies.models import Agency
    from billing.models import PaymentRecord, Plan, Subscription
    from member.models import (
        AttendanceCorrection,
        AttendanceLog,
        Booking,
        BookingPayment,
        Contact,
        ContactInstruction,
        Flight,
        Hotel,
        LedgerEntry,
        Package,
        Transport,
        Voucher,
        VoucherInstruction,
    )
    from rbac.models import Role
    from system_config.models import (
        AgencyBranding,
        APIKey,
        EmailTemplate,
        NotificationSettings,
        SystemConfiguration,
    )

    for model in [
        Agency, User, Role,
        Hotel, Flight, Transport, Package, Contact,
        Booking, Voucher, LedgerEntry, AttendanceLog, VoucherInstruction,
        ContactInstruction, AttendanceCorrection, BookingPayment,
        Plan, Subscription, PaymentRecord,
        SystemConfiguration, AgencyBranding, EmailTemplate, NotificationSettings, APIKey,
    ]:
        uid = model.__name__
        pre_save.connect(_pre_save, sender=model, dispatch_uid=f"audit_pre_save_{uid}")
        post_save.connect(_post_save, sender=model, dispatch_uid=f"audit_post_save_{uid}")
        post_delete.connect(_post_delete, sender=model, dispatch_uid=f"audit_post_delete_{uid}")

    # pre_delete fires for *every* collected instance (the whole cascade)
    # before any DELETE statement runs at all — the only point at which
    # "is this Agency about to be deleted" can be known for certain ahead
    # of the children being processed. See _resolve_agency_id.
    pre_delete.connect(_pre_delete_agency, sender=Agency, dispatch_uid="audit_pre_delete_agency")
