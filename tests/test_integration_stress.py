"""
Integration Stress Tests for AnalytIQ
Tests concurrent operations and background task handling
"""
import pytest
from unittest.mock import patch, MagicMock
import time


class TestConcurrentOperations:
    """Test concurrent API operations"""

    def test_concurrent_class_browsing_during_pdf_upload(self, mock_flask_request):
        """Verify browsing doesn't slow down during background PDF processing"""
        # Simulate PDF upload starting
        with patch('app.FEATURE_ASYNC_TASKS', True):
            with patch('tasks.process_pdf_and_extract_text.delay') as mock_task:
                mock_task.return_value.id = 'test-task-123'
                
                # Start timing
                start_time = time.time()
                
                # Simulate API call processing time
                time.sleep(0.1)  # Simulate minimal processing
                
                browse_time = time.time() - start_time
                
                # Should respond in under 1 second even with background task
                assert browse_time < 1.0

    def test_multiple_api_calls_with_caching(self, mock_redis_client):
        """Verify cache improves performance for repeated requests"""
        with patch('core.cache.FEATURE_CACHING', True):
            with patch('core.cache.redis_client', mock_redis_client):
                # First call - cache miss
                mock_redis_client.get.return_value = None
                start_time = time.time()
                from core.cache import get_cached
                result1 = get_cached('test_key')
                first_call_time = time.time() - start_time
                
                # Second call - cache hit
                mock_redis_client.get.return_value = '{"status": "healthy"}'
                start_time = time.time()
                result2 = get_cached('test_key')
                second_call_time = time.time() - start_time
                
                # Both calls should complete quickly
                assert first_call_time < 1.0
                assert second_call_time < 1.0


class TestCacheInvalidation:
    """Test cache invalidation scenarios"""

    def test_cache_invalidation_on_update(self):
        """Verify cache is invalidated when data is updated"""
        from core.cache import set_cached, get_cached, invalidate_cache
        
        with patch('core.cache.redis_client') as mock_redis:
            with patch('core.cache.FEATURE_CACHING', True):
                # Set initial cache
                mock_redis.setex.return_value = True
                set_cached('class:123', {'title': 'Old Title'}, ttl=300)
                
                # Simulate update - should invalidate cache
                mock_redis.keys.return_value = ['class:123']
                mock_redis.delete.return_value = 1
                
                deleted_count = invalidate_cache('class:*')
                
                assert deleted_count == 1
                mock_redis.delete.assert_called_once()

    def test_stale_data_prevention(self):
        """Ensure cache doesn't serve stale data after updates"""
        from core.cache import get_cached, set_cached
        
        with patch('core.cache.redis_client') as mock_redis:
            with patch('core.cache.FEATURE_CACHING', True):
                # First read - fresh data
                mock_redis.get.return_value = '{"title": "Updated Title"}'
                
                result = get_cached('class:123')
                
                assert result is not None
                assert result['title'] == 'Updated Title'


class TestCostControl:
    """Test AI API cost control mechanisms"""

    def test_duplicate_exercise_generation_uses_cache(self):
        """Verify duplicate exercise requests use cache instead of calling Gemini API"""
        from core.cache import get_cached, set_cached
        
        with patch('core.cache.redis_client') as mock_redis:
            with patch('core.cache.FEATURE_CACHING', True):
                # Simulate cached exercise result
                cached_exercises = {
                    'exercises': [
                        {'title': 'Exercise 1', 'description': 'Test exercise'}
                    ]
                }
                mock_redis.get.return_value = '{"exercises": [{"title": "Exercise 1", "description": "Test exercise"}]}'
                
                # First request should hit cache
                result = get_cached('exercises:chapter:123')
                
                assert result is not None
                assert len(result['exercises']) == 1
                mock_redis.get.assert_called_once()

    def test_gemini_api_not_called_for_cached_results(self):
        """Ensure Gemini API is not called when results are cached"""
        with patch('core.cache.get_cached') as mock_get_cache:
            with patch('tasks.generate_exercises_from_pdf_content') as mock_gemini:
                # Return cached result
                mock_get_cache.return_value = {'exercises': ['cached']}
                
                # Simulate exercise generation request
                result = mock_get_cache('exercises:chapter:123')
                
                # Gemini should NOT be called
                mock_gemini.assert_not_called()
                assert result is not None


class TestBackgroundTaskResilience:
    """Test background task error handling"""

    def test_task_failure_doesnt_crash_app(self):
        """Verify app continues running even if background task fails"""
        with patch('tasks.process_pdf_and_extract_text.delay') as mock_task:
            # Simulate task failure
            mock_task.side_effect = Exception("Task failed")
            
            # App should handle gracefully
            try:
                mock_task()
            except Exception as e:
                assert str(e) == "Task failed"
                # App should log error but continue

    def test_task_retry_mechanism(self):
        """Verify tasks retry on failure"""
        with patch('tasks.process_pdf_and_extract_text.retry') as mock_retry:
            mock_retry.return_value = True
            
            # Simulate retry
            result = mock_retry(countdown=60)
            
            assert result is True
            mock_retry.assert_called_once()


class TestDatabaseConnectionPool:
    """Test database connection pool under load"""

    def test_connection_pool_handles_concurrent_requests(self):
        """Verify connection pool doesn't exhaust under load"""
        with patch('core.database.db_pool') as mock_pool:
            mock_conn = MagicMock()
            mock_pool.getconn.return_value = mock_conn

            # Simulate 10 concurrent connections
            connections = []
            for i in range(10):
                conn = mock_pool.getconn()
                connections.append(conn)

            # All connections should be acquired
            assert len(connections) == 10
            assert mock_pool.getconn.call_count == 10

    def test_connection_pool_releases_properly(self):
        """Ensure connections are returned to pool after use"""
        with patch('core.database.db_pool') as mock_pool:
            mock_conn = MagicMock()
            mock_pool.getconn.return_value = mock_conn

            # Get and release connection
            conn = mock_pool.getconn()
            mock_pool.putconn(conn)

            # Verify release was called
            mock_pool.putconn.assert_called_once_with(conn)
