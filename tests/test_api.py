"""
Simplified integration tests for Flask API endpoints
Tests basic functionality without complex mocking
"""
import pytest
import os


@pytest.fixture
def app():
    """Create minimal Flask app for testing"""
    # Set test environment before importing app
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['FEATURE_ASYNC_TASKS'] = 'False'
    os.environ['FEATURE_CACHING'] = 'False'
    os.environ['FEATURE_CSRF_PROTECTION'] = 'False'
    
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    return flask_app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestHealthEndpoint:
    """Tests for health check endpoint"""
    
    def test_health_endpoint_exists(self, client):
        """Test that health endpoint exists"""
        response = client.get('/api/health')
        
        # Should return 200 or 503 (if DB is down)
        assert response.status_code in [200, 503]
        
        # Should return JSON
        data = response.get_json()
        assert data is not None
        assert 'status' in data


class TestCSRFEndpoint:
    """Tests for CSRF token endpoint"""
    
    def test_csrf_token_endpoint(self, client):
        """Test CSRF token generation"""
        response = client.get('/api/csrf-token')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # CSRF can be enabled or disabled via feature flag
        # If enabled, should have csrf_token
        # If disabled, should have message
        assert 'csrf_token' in data or 'message' in data


class TestCORSHeaders:
    """Tests for CORS configuration"""
    
    def test_cors_headers_on_api_routes(self, client):
        """Test that CORS headers are present on API routes"""
        response = client.get('/api/health')
        
        # Check CORS headers
        assert 'Access-Control-Allow-Origin' in response.headers
        assert response.headers['Access-Control-Allow-Origin'] == '*'


class TestErrorHandling:
    """Tests for error handling"""
    
    def test_404_not_found(self, client):
        """Test 404 error for non-existent endpoint"""
        response = client.get('/api/nonexistent-endpoint-12345')
        
        assert response.status_code == 404
    
    def test_options_request(self, client):
        """Test OPTIONS request (CORS preflight)"""
        response = client.options('/api/health')
        
        # Should return 200 or 204
        assert response.status_code in [200, 204]


class TestTaskStatusEndpoint:
    """Tests for Celery task status endpoint"""
    
    def test_task_status_endpoint_exists(self, client):
        """Test that task status endpoint exists"""
        response = client.get('/api/tasks/test-task-id')
        
        # Should return 200, 404, or 503 (if Celery disabled)
        assert response.status_code in [200, 404, 503]
        
        # Should return JSON
        data = response.get_json()
        assert data is not None


class TestAPIStructure:
    """Tests for API structure and configuration"""
    
    def test_app_has_routes(self, app):
        """Test that app has routes configured"""
        # Check that app has URL rules
        assert len(app.url_map._rules) > 0
    
    def test_app_in_testing_mode(self, app):
        """Test that app is in testing mode"""
        assert app.config['TESTING'] is True
    
    def test_csrf_disabled_in_tests(self, app):
        """Test that CSRF is disabled for testing"""
        assert app.config['WTF_CSRF_ENABLED'] is False
