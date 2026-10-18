from django import template
from django.utils.translation import gettext

register = template.Library()


@register.filter
def tr(value):
    """Translate a value stored in the database in English (standard role names, plan names...). Anything
    without a translation, such as a name an agency typed itself, comes back unchanged."""
    return gettext(value) if value else value


@register.filter
def ago(value):
    """'16 hours' (largest unit only) for a past datetime — short enough for a narrow menu."""
    from django.utils.timesince import timesince

    return timesince(value, depth=1) if value else ""
