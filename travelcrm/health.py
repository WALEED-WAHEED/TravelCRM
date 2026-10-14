"""
Health check views.

Two deliberately different endpoints, standard liveness/readiness split:

- health_check ("/health/"): is the process even up? No dependencies
  checked — used by things that would otherwise loop-restart the
  container on a transient DB blip. Unchanged from before Phase 11.
- readiness_check ("/health/ready/"): are this process's actual
  dependencies (Postgres, Redis) reachable? For uptime/monitoring tools
  that should page someone when the app can't do its job, even if the
  process itself is technically still running.

check_database()/check_redis() are factored out so the Super Admin
System Health page (platform_admin) can call them directly rather than
making a self-HTTP round trip to this process's own /health/ready/.
"""
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


def check_database():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return "ok"
    except Exception as exc:
        return f"error: {exc}"


def check_redis():
    try:
        import redis
        client = redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return "ok"
    except Exception as exc:
        return f"error: {exc}"


@require_http_methods(["GET"])
def health_check(request):
    """
    Simple health check endpoint that returns 200 OK.
    This endpoint doesn't require database access or authentication.
    """
    return JsonResponse({"status": "healthy", "service": "backend"}, status=200)


@require_http_methods(["GET"])
def readiness_check(request):
    """Checks the dependencies the app actually needs to serve a request."""
    checks = {"database": check_database(), "redis": check_redis()}
    healthy = all(v == "ok" for v in checks.values())
    return JsonResponse({"status": "healthy" if healthy else "unhealthy", "checks": checks}, status=200 if healthy else 503)
