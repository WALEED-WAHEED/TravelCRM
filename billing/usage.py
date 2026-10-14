"""
Usage is always computed live from the real data (staff count, bookings
this month) rather than cached in a running counter — a counter can
drift out of sync with reality (a user deleted outside the normal flow,
a booking cancelled and re-created); a live count can't.
"""
from django.utils import timezone

from accounts.models import User
from member.models import Booking

from .models import Subscription


def get_subscription(agency):
    return Subscription.all_tenants.filter(agency=agency).select_related('plan').first()


def get_seat_usage(agency):
    return User.objects.filter(agency=agency, is_active=True).count()


def get_booking_usage_this_month(agency):
    now = timezone.now()
    return Booking.all_tenants.filter(agency=agency, created_at__year=now.year, created_at__month=now.month).count()


def check_seat_limit(agency):
    """Returns (allowed: bool, message: str | None)."""
    sub = get_subscription(agency)
    if not sub or sub.plan.max_seats is None:
        return True, None
    used = get_seat_usage(agency)
    if used >= sub.plan.max_seats:
        return False, (
            f"Your '{sub.plan.name}' plan is limited to {sub.plan.max_seats} active staff seats "
            f"(you have {used}). Upgrade your plan to add more."
        )
    return True, None


def check_booking_limit(agency):
    """Returns (allowed: bool, message: str | None)."""
    sub = get_subscription(agency)
    if not sub or sub.plan.max_bookings_per_month is None:
        return True, None
    used = get_booking_usage_this_month(agency)
    if used >= sub.plan.max_bookings_per_month:
        return False, (
            f"Your '{sub.plan.name}' plan is limited to {sub.plan.max_bookings_per_month} bookings per month "
            f"(you've made {used} this month). Upgrade your plan to create more."
        )
    return True, None
