from django.shortcuts import redirect

# Always reachable regardless of subscription state — otherwise an agency
# whose trial expired could never even reach the page that lets them pay.
ALWAYS_ALLOWED_PREFIXES = (
    '/member/billing/',
    '/login/',
    '/logout/',
    '/forgot-password/',
    '/public/',
    '/static/',
    '/media/',
    '/health/',
    '/platform-admin/',
    '/admin/',
    '/api/',
)


class SubscriptionGateMiddleware:
    """
    Blocks tenant users from the app once their trial or subscription has
    lapsed, sending them to the billing page instead — the enforcement
    side of "self-serve signup with a trial", not just a UI hint.
    Super Admin and unauthenticated requests are never gated here.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            user
            and getattr(user, 'is_authenticated', False)
            and not getattr(user, 'is_superuser', False)
            and getattr(user, 'agency_id', None)
            and not request.path.startswith(ALWAYS_ALLOWED_PREFIXES)
        ):
            from .models import Subscription

            sub = Subscription.all_tenants.filter(agency_id=user.agency_id).select_related('plan').first()
            if sub and not sub.is_usable:
                return redirect('member-billing')

        return self.get_response(request)
