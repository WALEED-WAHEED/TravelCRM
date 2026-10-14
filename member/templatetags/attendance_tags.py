from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def hours_hm(value):
    """8.42 (decimal hours) -> '8 h 25 m'. Empty/zero -> ''."""
    try:
        minutes = int(round(Decimal(str(value)) * 60))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    if minutes <= 0:
        return ""
    h, m = divmod(minutes, 60)
    return f"{h} h {m:02d} m" if h else f"{m} m"
