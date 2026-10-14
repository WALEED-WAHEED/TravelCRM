"""Voucher PDF made by a headless Chrome / Chromium — the same engine that draws the View page,
so the downloaded file is exactly what the user sees (rounded cards, fonts, Urdu shaping).

If no browser is installed on the server, ``html_to_pdf`` returns None and the caller falls back to xhtml2pdf.
Point ``VOUCHER_PDF_CHROME`` (setting or environment variable) at the executable to use a specific one.
"""
import base64
import logging
import mimetypes
import os
import shutil
import subprocess
import tempfile
from functools import lru_cache

from django.conf import settings

log = logging.getLogger(__name__)

TIMEOUT = 60
_WINDOWS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge")


@lru_cache(maxsize=1)
def find_chrome():
    configured = getattr(settings, "VOUCHER_PDF_CHROME", "") or os.environ.get("VOUCHER_PDF_CHROME", "")
    if configured and os.path.isfile(configured):
        return configured
    for name in _NAMES:
        found = shutil.which(name)
        if found:
            return found
    for path in _WINDOWS:
        if os.path.isfile(path):
            return path
    return ""


def data_uri(path):
    """A file as a data: URI (so the PDF page needs no network or file access for its logo / fonts)."""
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as fh:
        return f"data:{mime};base64," + base64.b64encode(fh.read()).decode()


@lru_cache(maxsize=1)
def font_data_uri():
    path = os.path.join(settings.BASE_DIR, "static", "fonts", "NotoNaskhArabic-Regular.ttf")
    try:
        return data_uri(path).replace("application/octet-stream", "font/ttf")
    except OSError:
        return ""


def html_to_pdf(html):
    """Print `html` to an A4 PDF with headless Chrome. Returns bytes, or None if that is not possible."""
    chrome = find_chrome()
    if not chrome:
        return None
    with tempfile.TemporaryDirectory(prefix="voucher-pdf-") as tmp:
        src, out = os.path.join(tmp, "voucher.html"), os.path.join(tmp, "voucher.pdf")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(html)
        cmd = [
            chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
            "--no-pdf-header-footer", "--virtual-time-budget=4000",
            f"--user-data-dir={os.path.join(tmp, 'profile')}",     # never touch (or wait on) the user's own browser
            f"--print-to-pdf={out}", "file:///" + src.replace("\\", "/").lstrip("/"),
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=TIMEOUT, check=False,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.SubprocessError):
            log.exception("Chrome could not print the voucher")
            return None
        if not os.path.isfile(out):
            return None
        with open(out, "rb") as fh:
            data = fh.read()
    return data if data[:4] == b"%PDF" else None
