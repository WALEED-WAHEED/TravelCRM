"""{% pdfcard %}: a rounded card for the printed voucher.

The browser print view draws it with CSS (border-radius). The PDF engine (xhtml2pdf) cannot round corners,
so there the same card is a small table whose four corners are pre-drawn PNG images — it looks the same.

    {% pdfcard _("Mutamers") split %} ...content... {% endpdfcard %}      (titled, coloured header band)
    {% pdfcard "" plain %} ...content... {% endpdfcard %}                 (no title)

Flags: ``split``  the card may break across pages between rows;  ``plain`` no top margin (cards in a row).
"""
import base64
import io
from functools import lru_cache

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()

BORDER = "#cfd6e3"
BAND = "#dbe5f2"
WHITE = "#ffffff"
RADIUS = 10          # px in the PDF


@lru_cache(maxsize=None)
def _corner(pos, fill):
    """An opaque RADIUS x RADIUS PNG (white outside the arc, `fill` inside, thin border on the arc), as a data URI."""
    from PIL import Image, ImageDraw

    scale = 6
    s = RADIUS * scale
    sw = int(scale * 1.6)
    big = Image.new("RGB", (s * 2, s * 2), "white")
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0, 0, s * 2 - 1, s * 2 - 1), radius=s, fill=BORDER)
    d.rounded_rectangle((sw, sw, s * 2 - 1 - sw, s * 2 - 1 - sw), radius=s - sw, fill=fill)
    box = {"tl": (0, 0, s, s), "tr": (s, 0, s * 2, s), "bl": (0, s, s, s * 2), "br": (s, s, s * 2, s * 2)}[pos]
    buf = io.BytesIO()
    big.crop(box).resize((RADIUS * 2, RADIUS * 2), Image.LANCZOS).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _img(pos, fill):
    return f'<img src="{_corner(pos, fill)}" width="{RADIUS}" height="{RADIUS}">'


class PdfCardNode(template.Node):
    def __init__(self, nodelist, title, flags):
        self.nodelist, self.title, self.flags = nodelist, title, flags

    def render(self, context):
        body = self.nodelist.render(context)
        title = conditional_escape(self.title.resolve(context) or "") if self.title else ""
        split, plain = "split" in self.flags, "plain" in self.flags
        if not context.get("for_pdf"):
            cls = "card" + ("" if plain else " sec") + (" split" if split else "")
            head = f'<div class="sec-title">{title}</div>' if title else ""
            return mark_safe(f'<div class="{cls}">{head}{body}</div>')

        fill = BAND if title else WHITE
        tiny = "padding:0; font-size:1px; line-height:1px;"
        edge = f"border-left:1px solid {BORDER};"
        edge_r = f"border-right:1px solid {BORDER};"
        top_mid = (f'<td class="rct" style="background-color:{fill}; border-top:1px solid {BORDER};">{title}</td>' if title else
                   f'<td style="border-top:1px solid {BORDER}; {tiny}"><img src="{_corner("tl", WHITE)}" width="1" height="{RADIUS}"></td>')
        card = (
            '<table class="rc"><tr>'
            f'<td class="rcc" style="background-color:{fill}; {edge} {tiny}">{_img("tl", fill)}</td>'
            f'{top_mid}'
            f'<td class="rcc" style="background-color:{fill}; {edge_r} {tiny}">{_img("tr", fill)}</td>'
            '</tr><tr>'
            f'<td class="rcc" style="{edge} {tiny}">&nbsp;</td>'
            f'<td class="rcm">{body}</td>'
            f'<td class="rcc" style="{edge_r} {tiny}">&nbsp;</td>'
            '</tr><tr>'
            f'<td class="rcc" style="{edge} {tiny}">{_img("bl", WHITE)}</td>'
            f'<td style="border-bottom:1px solid {BORDER}; {tiny}"><img src="{_corner("bl", WHITE)}" width="1" height="{RADIUS}"></td>'
            f'<td class="rcc" style="{edge_r} {tiny}">{_img("br", WHITE)}</td>'
            '</tr></table>'
        )
        if not split:
            # A one-row table cannot be cut by a page break, so the whole card moves to the next page together.
            card = f'<table class="rcw"><tr><td style="padding:0;">{card}</td></tr></table>'
        html = f'<div style="margin-top:{0 if plain else 9}px;">{card}</div>'
        return mark_safe(html)


@register.tag("pdfcard")
def do_pdfcard(parser, token):
    bits = token.split_contents()[1:]
    title = parser.compile_filter(bits[0]) if bits else None
    flags = set(bits[1:])
    nodelist = parser.parse(("endpdfcard",))
    parser.delete_first_token()
    return PdfCardNode(nodelist, title, flags)
