"""
Redis Cache Utilities for AnalytIQ
Provides caching functionality for frequently accessed endpoints
"""

import json
import functools
import config

REDIS_URL = config.REDIS_URL
CACHE_DEFAULT_TTL = config.CACHE_DEFAULT_TTL
FEATURE_CACHING = config.FEATURE_CACHING

# Initialize Redis client
try:
    import redis

    redis_client = redis.from_url(
        REDIS_URL, decode_responses=True, socket_connect_timeout=5, socket_timeout=5
    )

    # Test connection
    redis_client.ping()
    print(f"✅ Redis cache initialized (TTL: {CACHE_DEFAULT_TTL}s)")
except Exception as e:
    print(f"⚠️  Redis not available: {e}")
    redis_client = None


def get_cached(key):
    """
    Get value from cache

    Args:
        key: Cache key

    Returns:
        Cached value (dict) or None if not found
    """
    if not redis_client or not FEATURE_CACHING:
        return None

    try:
        value = redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        print(f"Cache get error: {e}")
        return None


def set_cached(key, value, ttl=None):
    """
    Set value in cache

    Args:
        key: Cache key
        value: Value to cache (must be JSON serializable)
        ttl: Time to live in seconds (default: CACHE_DEFAULT_TTL)

    Returns:
        bool: True if successful, False otherwise
    """
    if not redis_client or not FEATURE_CACHING:
        return False

    if ttl is None:
        ttl = CACHE_DEFAULT_TTL

    try:
        redis_client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        print(f"Cache set error: {e}")
        return False


def invalidate_cache(pattern):
    """
    Delete cache keys matching pattern

    Args:
        pattern: Redis key pattern (e.g., 'class:*', 'user:123:*')

    Returns:
        int: Number of keys deleted
    """
    if not redis_client or not FEATURE_CACHING:
        return 0

    try:
        keys = redis_client.keys(pattern)
        if keys:
            return redis_client.delete(*keys)
        return 0
    except Exception as e:
        print(f"Cache invalidation error: {e}")
        return 0


def cache_response(ttl=None, key_prefix=""):
    """
    Decorator to cache Flask endpoint responses

    Args:
        ttl: Cache TTL in seconds
        key_prefix: Prefix for cache key

    Usage:
        @app.route('/api/classes/<class_id>')
        @cache_response(ttl=300, key_prefix='class')
        def get_class(class_id):
            # ... endpoint logic
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Skip caching if disabled
            if not FEATURE_CACHING or not redis_client:
                return func(*args, **kwargs)

            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{':'.join(map(str, args))}"
            if kwargs:
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"

            # Try to get from cache
            cached_value = get_cached(cache_key)
            if cached_value is not None:
                # Return cached response
                from flask import jsonify

                return jsonify(cached_value), 200

            # Call function and cache result
            response = func(*args, **kwargs)

            # Extract JSON data from response
            if hasattr(response, "get_json"):
                data = response.get_json()
                if data:
                    set_cached(cache_key, data, ttl)

            return response

        return wrapper

    return decorator


def cache_health_check():
    """
    Check if Redis cache is healthy

    Returns:
        dict: {'healthy': bool, 'message': str}
    """
    if not redis_client:
        return {"healthy": False, "message": "Redis client not initialized"}

    try:
        redis_client.ping()

        # Get cache stats
        info = redis_client.info("stats")

        return {
            "healthy": True,
            "message": "Redis cache accessible",
            "stats": {
                "total_connections": info.get("total_connections_received", 0),
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            },
        }
    except Exception as e:
        return {"healthy": False, "message": f"Redis error: {str(e)}"}


def get_cache_stats():
    """
    Get cache hit/miss statistics

    Returns:
        dict: Cache statistics
    """
    if not redis_client:
        return {"error": "Redis not available"}

    try:
        info = redis_client.info("stats")
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses

        hit_rate = (hits / total * 100) if total > 0 else 0

        return {
            "hits": hits,
            "misses": misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "enabled": FEATURE_CACHING,
        }
    except Exception as e:
        return {"error": str(e)}
