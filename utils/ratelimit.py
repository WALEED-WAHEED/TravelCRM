"""
Lightweight rate limiting for plain Django views (login, password reset)
that DRF's throttle classes don't cover — those only wrap DRF API views.

Uses Django's cache framework, same as DRF's own throttles. With the
default LocMemCache that only limits per worker process; point CACHES at
Redis/memcached in production so it's enforced across all workers.
"""
from django.core.cache import cache


def is_rate_limited(key, limit, window_seconds):
    """Returns True if `key` has been hit `limit` times in the last
    `window_seconds`, incrementing the counter as a side effect."""
    cache_key = f"ratelimit:{key}"
    count = cache.get(cache_key, 0)
    if count >= limit:
        return True
    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
    return False


def reset(key):
    cache.delete(f"ratelimit:{key}")
