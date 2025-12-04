"""
Simple health check view that doesn't require database access
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def health_check(request):
    """
    Simple health check endpoint that returns 200 OK.
    This endpoint doesn't require database access or authentication.
    """
    return JsonResponse({"status": "healthy", "service": "backend"}, status=200)

