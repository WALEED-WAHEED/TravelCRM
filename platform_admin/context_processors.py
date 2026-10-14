from django.db.models import Q
from django.utils import timezone


def active_announcements(request):
    """
    Same pattern as system_config.context_processors.saas_config — makes
    the currently-live Super Admin announcements available to every
    tenant template as {{ active_announcements }}. Platform-admin/staff
    viewers never see these (they have their own shell), and a request
    with no authenticated agency (login page, public signup, etc.) gets
    an empty list rather than an error.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not getattr(user, 'agency_id', None):
        return {'active_announcements': []}

    from .models import Announcement

    now = timezone.now()
    try:
        announcements = list(
            Announcement.objects.filter(
                is_active=True, starts_at__lte=now,
            ).filter(
                Q(ends_at__isnull=True) | Q(ends_at__gte=now),
            ).filter(
                Q(target_agencies__isnull=True) | Q(target_agencies=user.agency_id),
            ).distinct()
        )
    except Exception:
        announcements = []
    return {'active_announcements': announcements}
