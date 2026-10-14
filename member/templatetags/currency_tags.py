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


def _amount_text(d):
    d = d.quantize(Decimal("0.01"))
    whole, frac = format(abs(d), "f").split(".")
    text = _comma_whole(whole)
    return text if frac == "00" else f"{text}.{frac}"


@register.filter
def amt(value):
    """Statement-style amount: 1,115,713 (decimals only when non-zero). 0 for empty."""
    try:
        d = Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    return ("-" if d < 0 else "") + _amount_text(d)


@register.filter
def drcr(value):
    """Party balance with side: '7,265 Dr' (party owes you) / '7,265 Cr' (you owe party)."""
    try:
        d = Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    if d == 0:
        return "0"
    return f"{_amount_text(d)} {'Dr' if d > 0 else 'Cr'}"
