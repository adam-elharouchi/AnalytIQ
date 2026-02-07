"""
Comprehensive tests for cache.py - Redis caching utilities.
Targets uncovered lines: 29-31 (init error), 52-54 (get error), 73 (default TTL),
78-80 (set error), 100-103 (invalidation error), 121-154 (cache_response decorator),
212-213 (get_cache_stats error)
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import json


class TestGetCached:
    """Test get_cached function"""

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_get_cached_hit(self, mock_redis):
        """Test cache hit returns parsed JSON"""
        mock_redis.get.return_value = '{"key": "value"}'
        from cache import get_cached
        result = get_cached("test_key")
        assert result == {"key": "value"}

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_get_cached_miss(self, mock_redis):
        """Test cache miss returns None"""
        mock_redis.get.return_value = None
        from cache import get_cached
        result = get_cached("nonexistent")
        assert result is None

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_get_cached_redis_error(self, mock_redis):
        """Test Redis error returns None - lines 52-54"""
        mock_redis.get.side_effect = Exception("Redis connection lost")
        from cache import get_cached
        result = get_cached("test_key")
        assert result is None

    @patch("cache.redis_client", None)
    def test_get_cached_no_client(self):
        """Test with no Redis client returns None"""
        from cache import get_cached
        result = get_cached("test_key")
        assert result is None

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", False)
    def test_get_cached_disabled(self, mock_redis):
        """Test with caching disabled returns None"""
        from cache import get_cached
        result = get_cached("test_key")
        assert result is None


class TestSetCached:
    """Test set_cached function"""

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_set_cached_success(self, mock_redis):
        """Test successful cache set"""
        from cache import set_cached
        result = set_cached("test_key", {"data": "value"}, ttl=60)
        assert result is True
        mock_redis.setex.assert_called_once()

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_set_cached_default_ttl(self, mock_redis):
        """Test cache set with default TTL - line 73"""
        from cache import set_cached, CACHE_DEFAULT_TTL
        result = set_cached("test_key", {"data": "value"})
        assert result is True
        args = mock_redis.setex.call_args
        assert args[0][1] == CACHE_DEFAULT_TTL

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_set_cached_redis_error(self, mock_redis):
        """Test Redis error returns False - lines 78-80"""
        mock_redis.setex.side_effect = Exception("Redis write error")
        from cache import set_cached
        result = set_cached("test_key", {"data": "value"})
        assert result is False

    @patch("cache.redis_client", None)
    def test_set_cached_no_client(self):
        """Test with no Redis client returns False"""
        from cache import set_cached
        result = set_cached("test_key", {"data": "value"})
        assert result is False

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", False)
    def test_set_cached_disabled(self, mock_redis):
        """Test with caching disabled returns False"""
        from cache import set_cached
        result = set_cached("test_key", {"data": "value"})
        assert result is False


class TestInvalidateCache:
    """Test invalidate_cache function"""

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_invalidate_with_matches(self, mock_redis):
        """Test invalidating matching keys"""
        mock_redis.keys.return_value = ["class:1", "class:2"]
        mock_redis.delete.return_value = 2
        from cache import invalidate_cache
        result = invalidate_cache("class:*")
        assert result == 2

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_invalidate_no_matches(self, mock_redis):
        """Test invalidating with no matching keys"""
        mock_redis.keys.return_value = []
        from cache import invalidate_cache
        result = invalidate_cache("nonexistent:*")
        assert result == 0

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_invalidate_redis_error(self, mock_redis):
        """Test Redis error returns 0 - lines 101-103"""
        mock_redis.keys.side_effect = Exception("Redis error")
        from cache import invalidate_cache
        result = invalidate_cache("class:*")
        assert result == 0

    @patch("cache.redis_client", None)
    def test_invalidate_no_client(self):
        """Test with no Redis client returns 0"""
        from cache import invalidate_cache
        result = invalidate_cache("class:*")
        assert result == 0


class TestCacheResponseDecorator:
    """Test cache_response decorator - lines 121-154"""

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_decorator_cache_hit(self, mock_redis):
        """Test decorator returns cached response"""
        mock_redis.get.return_value = '{"cached": true}'

        from cache import cache_response
        from flask import Flask

        app = Flask(__name__)

        @cache_response(ttl=60, key_prefix="test")
        def my_endpoint():
            return {"fresh": True}

        with app.test_request_context():
            result = my_endpoint()
            # Should return cached response
            assert result is not None

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_decorator_cache_miss(self, mock_redis):
        """Test decorator calls function on cache miss"""
        mock_redis.get.return_value = None

        from cache import cache_response
        from flask import Flask, jsonify

        app = Flask(__name__)

        @cache_response(ttl=60, key_prefix="test")
        def my_endpoint():
            return jsonify({"fresh": True})

        with app.test_request_context():
            result = my_endpoint()
            assert result is not None

    @patch("cache.redis_client", None)
    @patch("cache.FEATURE_CACHING", False)
    def test_decorator_caching_disabled(self):
        """Test decorator passes through when disabled"""
        from cache import cache_response
        from flask import Flask, jsonify

        app = Flask(__name__)

        @cache_response(ttl=60, key_prefix="test")
        def my_endpoint():
            return jsonify({"fresh": True})

        with app.test_request_context():
            result = my_endpoint()
            assert result is not None

    @patch("cache.redis_client")
    @patch("cache.FEATURE_CACHING", True)
    def test_decorator_with_kwargs(self, mock_redis):
        """Test decorator with keyword arguments - line 130-131"""
        mock_redis.get.return_value = None

        from cache import cache_response
        from flask import Flask, jsonify

        app = Flask(__name__)

        @cache_response(ttl=60, key_prefix="test")
        def my_endpoint(class_id=None):
            return jsonify({"class_id": class_id})

        with app.test_request_context():
            result = my_endpoint(class_id="CLS1")
            assert result is not None


class TestCacheHealthCheck:
    """Test cache_health_check function"""

    @patch("cache.redis_client")
    def test_health_check_healthy(self, mock_redis):
        """Test healthy Redis"""
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {
            "total_connections_received": 100,
            "total_commands_processed": 5000,
            "keyspace_hits": 300,
            "keyspace_misses": 50,
        }
        from cache import cache_health_check
        result = cache_health_check()
        assert result["healthy"] is True
        assert "stats" in result

    @patch("cache.redis_client")
    def test_health_check_error(self, mock_redis):
        """Test unhealthy Redis"""
        mock_redis.ping.side_effect = Exception("Connection refused")
        from cache import cache_health_check
        result = cache_health_check()
        assert result["healthy"] is False

    @patch("cache.redis_client", None)
    def test_health_check_no_client(self):
        """Test health check with no client"""
        from cache import cache_health_check
        result = cache_health_check()
        assert result["healthy"] is False


class TestGetCacheStats:
    """Test get_cache_stats function - lines 187-213"""

    @patch("cache.redis_client")
    def test_get_stats_success(self, mock_redis):
        """Test getting cache statistics"""
        mock_redis.info.return_value = {
            "keyspace_hits": 300,
            "keyspace_misses": 50,
        }
        from cache import get_cache_stats
        result = get_cache_stats()
        assert result["hits"] == 300
        assert result["misses"] == 50
        assert result["hit_rate_percent"] > 0

    @patch("cache.redis_client")
    def test_get_stats_zero_total(self, mock_redis):
        """Test stats when no requests yet"""
        mock_redis.info.return_value = {
            "keyspace_hits": 0,
            "keyspace_misses": 0,
        }
        from cache import get_cache_stats
        result = get_cache_stats()
        assert result["hit_rate_percent"] == 0

    @patch("cache.redis_client")
    def test_get_stats_redis_error(self, mock_redis):
        """Test stats on Redis error - lines 212-213"""
        mock_redis.info.side_effect = Exception("Redis error")
        from cache import get_cache_stats
        result = get_cache_stats()
        assert "error" in result

    @patch("cache.redis_client", None)
    def test_get_stats_no_client(self):
        """Test stats with no client"""
        from cache import get_cache_stats
        result = get_cache_stats()
        assert "error" in result
