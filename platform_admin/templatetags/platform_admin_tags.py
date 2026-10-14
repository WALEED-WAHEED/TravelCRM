from django import template

from platform_admin.decorators import has_platform_capability

register = template.Library()


@register.filter
def has_capability(user, capability):
    """Usage: {% if request.user|has_capability:'billing.view' %}...{% endif %}"""
    return has_platform_capability(user, capability)
