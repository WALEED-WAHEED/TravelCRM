"""
Activity Log helpers: filtering AuditLog rows and turning raw field diffs into
something a person can read ("Status: Draft → Confirmed", local times, Yes/No).
"""
import datetime

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _l

from system_config.models import AuditLog

PRESETS = [
    ("", _l("All time")),
    ("today", _l("Today")),
    ("7d", _l("Last 7 days")),
    ("30d", _l("Last 30 days")),
]


def _models_by_name():
    return {m.__name__: m for m in apps.get_models()}


_LABELS = {}


def model_label(name):
    """'LedgerEntry' -> 'Ledger entry' (the model's own verbose name)."""
    if not _LABELS:
        _LABELS.update({n: str(m._meta.verbose_name).capitalize() for n, m in _models_by_name().items()})
    return _LABELS.get(name, name)


def _field(model_name, field_name):
    model = _models_by_name().get(model_name)
    if not model:
        return None
    try:
        return model._meta.get_field(field_name)
    except FieldDoesNotExist:
        return None


def _display(field, value, tz):
    if value in (None, "", [], {}):
        return "—"
    if field is not None and getattr(field, "choices", None):
        return str(dict(field.flatchoices).get(value, value))
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, str) and len(value) >= 19 and value[4] == "-" and "T" in value:
        try:
            dt = datetime.datetime.fromisoformat(value)
            if timezone.is_aware(dt):
                dt = dt.astimezone(tz)
            return dt.strftime("%d %b %Y, %I:%M %p")
        except ValueError:
            pass
    if field is not None and field.is_relation and isinstance(value, int):
        return f"#{value}"
    text = str(value)
    return text if len(text) <= 120 else text[:117] + "…"


def readable_changes(entry, tz):
    rows = []
    for name, delta in (entry.changes or {}).items():
        f = _field(entry.model_name, name)
        label = str(f.verbose_name).capitalize() if f is not None and hasattr(f, "verbose_name") else name.replace("_", " ").capitalize()
        rows.append({
            "label": label,
            "old": _display(f, (delta or {}).get("old"), tz),
            "new": _display(f, (delta or {}).get("new"), tz),
        })
    return rows


def read_filters(params):
    preset = params.get("preset", "")
    return {
        "q": (params.get("q") or "").strip(),
        "action": (params.get("action") or "").strip(),
        "model": (params.get("model") or "").strip(),
        "who": (params.get("who") or "").strip(),
        "preset": preset if preset in dict(PRESETS) else "",
    }


def filtered(agency, f, tz):
    qs = AuditLog.objects.filter(agency=agency).select_related("user")
    if f["q"]:
        needle = f["q"].lower()
        labelled = [n for n in _models_by_name() if needle in model_label(n).lower()]
        qs = qs.filter(Q(object_repr__icontains=f["q"]) | Q(model_name__icontains=f["q"]) | Q(model_name__in=labelled))
    if f["model"]:
        qs = qs.filter(model_name=f["model"])
    if f["who"] == "system":
        qs = qs.filter(user__isnull=True)
    elif f["who"].isdigit():
        qs = qs.filter(user_id=int(f["who"]))
    if f["preset"]:
        now = timezone.now().astimezone(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if f["preset"] == "7d":
            start -= datetime.timedelta(days=6)
        elif f["preset"] == "30d":
            start -= datetime.timedelta(days=29)
        qs = qs.filter(timestamp__gte=start)
    # Counts ignore the action filter so the cards show the mix for the current scope.
    counts = {r["action"]: r["n"] for r in qs.values("action").annotate(n=Count("id"))}
    if f["action"]:
        qs = qs.filter(action=f["action"])
    return qs.order_by("-timestamp", "-id"), counts


def options(agency):
    base = AuditLog.objects.filter(agency=agency)
    models = sorted({m for m in base.values_list("model_name", flat=True).distinct()}, key=lambda m: model_label(m).lower())
    users = (base.exclude(user__isnull=True).values("user_id", "user__first_name", "user__last_name", "user__username")
             .distinct().order_by("user__first_name", "user__username"))
    return {
        "models": [(m, model_label(m)) for m in models],
        "users": [(u["user_id"], f"{u['user__first_name']} {u['user__last_name']}".strip() or u["user__username"])
                  for u in users],
        "has_system": base.filter(user__isnull=True).exists(),
    }
