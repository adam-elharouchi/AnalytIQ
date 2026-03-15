"""
Unit tests for cache utilities (cache.py) - FIXED VERSION
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestCacheOperations:
    """Tests for basic cache operations"""
    
    @patch('core.cache.FEATURE_CACHING', True)
    @patch('core.cache.redis_client')
    def test_get_cached_hit(self, mock_redis):
        """Test cache hit returns cached value"""
        from core.cache import get_cached
        
        # Mock Redis returning cached data
        cached_data = json.dumps({'result': 'cached'})
        mock_redis.get.return_value = cached_data
        
        result = get_cached('test_key')
        
        assert result == {'result': 'cached'}
        mock_redis.get.assert_called_once_with('test_key')
    
    @patch('core.cache.FEATURE_CACHING', True)
    @patch('core.cache.redis_client')
    def test_get_cached_miss(self, mock_redis):
        """Test cache miss returns None"""
        from core.cache import get_cached
        
        # Mock Redis returning None (cache miss)
        mock_redis.get.return_value = None
        
        result = get_cached('test_key')
        
        assert result is None
        mock_redis.get.assert_called_once_with('test_key')
    
    @patch('core.cache.FEATURE_CACHING', True)
    @patch('core.cache.redis_client')
    def test_set_cached_success(self, mock_redis):
        """Test setting cache value"""
        from core.cache import set_cached
        
        mock_redis.setex.return_value = True
        
        result = set_cached('test_key', {'data': 'value'}, ttl=300)
        
        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == 'test_key'
        assert call_args[1] == 300
        assert json.loads(call_args[2]) == {'data': 'value'}
    
    @patch('core.cache.FEATURE_CACHING', True)
    @patch('core.cache.redis_client')
    def test_invalidate_cache_single_key(self, mock_redis):
        """Test invalidating single cache key"""
        from core.cache import invalidate_cache
        
        mock_redis.keys.return_value = ['test_key']
        mock_redis.delete.return_value = 1
        
        result = invalidate_cache('test_key')
        
        assert result == 1
        mock_redis.keys.assert_called_once_with('test_key')
        mock_redis.delete.assert_called_once_with('test_key')
    
    @patch('core.cache.FEATURE_CACHING', True)
    @patch('core.cache.redis_client')
    def test_invalidate_cache_pattern(self, mock_redis):
        """Test invalidating cache by pattern"""
        from core.cache import invalidate_cache
        
        # Mock Redis keys() returning matching keys
        mock_redis.keys.return_value = ['user:1', 'user:2', 'user:3']
        mock_redis.delete.return_value = 3
        
        result = invalidate_cache('user:*')
        
        assert result == 3
        mock_redis.keys.assert_called_once_with('user:*')
        mock_redis.delete.assert_called_once_with('user:1', 'user:2', 'user:3')
    
    @patch('core.cache.FEATURE_CACHING', False)
    def test_cache_disabled(self):
        """Test cache operations when feature disabled"""
        from core.cache import get_cached, set_cached, invalidate_cache
        
        assert get_cached('key') is None
        assert set_cached('key', 'value') is False
        assert invalidate_cache('key') == 0


class TestCacheHealthCheck:
    """Tests for cache_health_check function"""
    
    @patch('core.cache.redis_client')
    def test_health_check_healthy(self, mock_redis):
        """Test health check when Redis is healthy"""
        from core.cache import cache_health_check
        
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {
            'total_connections_received': 100,
            'total_commands_processed': 1000,
            'keyspace_hits': 800,
            'keyspace_misses': 200
        }
        
        result = cache_health_check()
        
        assert result['healthy'] is True
        assert result['message'] == 'Redis cache accessible'
        assert 'stats' in result
        assert result['stats']['total_connections'] == 100
        assert result['stats']['keyspace_hits'] == 800
    
    @patch('core.cache.redis_client', None)
    def test_health_check_no_client(self):
        """Test health check when Redis client not initialized"""
        from core.cache import cache_health_check
        
        result = cache_health_check()
        
        assert result['healthy'] is False
        assert result['message'] == 'Redis client not initialized'
    
    @patch('core.cache.redis_client')
    def test_health_check_connection_error(self, mock_redis):
        """Test health check when Redis connection fails"""
        from core.cache import cache_health_check
        
        mock_redis.ping.side_effect = Exception('Connection refused')
        
        result = cache_health_check()
        
        assert result['healthy'] is False
        assert 'Connection refused' in result['message']


class TestCacheStats:
    """Tests for get_cache_stats function"""
    
    @patch('core.cache.redis_client')
    def test_get_stats_success(self, mock_redis):
        """Test getting cache statistics"""
        from core.cache import get_cache_stats
        
        mock_redis.info.return_value = {
            'keyspace_hits': 1500,
            'keyspace_misses': 500
        }
        
        stats = get_cache_stats()
        
        assert stats['hits'] == 1500
        assert stats['misses'] == 500
        assert stats['hit_rate_percent'] == 75.0
    
    @patch('core.cache.redis_client')
    def test_get_stats_zero_division(self, mock_redis):
        """Test stats with zero hits and misses"""
        from core.cache import get_cache_stats
        
        mock_redis.info.return_value = {
            'keyspace_hits': 0,
            'keyspace_misses': 0
        }
        
        stats = get_cache_stats()
        
        assert stats['hit_rate_percent'] == 0.0
    
    @patch('core.cache.redis_client', None)
    def test_get_stats_no_client(self):
        """Test stats when client not initialized"""
        from core.cache import get_cache_stats
        
        stats = get_cache_stats()
        
        assert 'error' in stats
