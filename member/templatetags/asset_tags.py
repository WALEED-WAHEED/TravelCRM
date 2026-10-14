"""Cache-busting for our own CSS/JS: {% versioned_static 'js/app.js' %} adds
?v=<file modification time>, so browsers fetch a new copy as soon as the file
changes instead of running a stale cached one."""
import os

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def versioned_static(path):
    url = static(path)
    found = finders.find(path) or os.path.join(settings.STATIC_ROOT or "", path)
    try:
        return f"{url}?v={int(os.path.getmtime(found)):x}"
    except (OSError, TypeError):
        return url
