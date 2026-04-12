"""Template filters for PKR (Pakistani Rupee) display."""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _comma_whole(whole_str: str) -> str:
    w = whole_str.lstrip("0") or "0"
    parts = []
    while w:
        parts.insert(0, w[-3:])
        w = w[:-3]
    return ",".join(parts)


@register.filter
def pkr(value):
    """Format a numeric amount as Rs. X,XXX.XX (PKR). None/empty → —."""
    if value is None or value == "":
        return "—"
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    sign = "-" if d < 0 else ""
    d = abs(d).quantize(Decimal("0.01"))
    text = format(d, "f")
    if "." in text:
        whole, frac = text.split(".")
        frac = (frac + "00")[:2]
    else:
        whole, frac = text, "00"
    return f"{sign}Rs. {_comma_whole(whole)}.{frac}"
