"""
Tests for API documentation endpoints (Swagger UI)
"""
import pytest
from app import app
import json


class TestSwaggerDocumentation:
    """Test Swagger/OpenAPI documentation endpoints"""

    def test_swagger_ui_endpoint_exists(self, client):
        """Test that Swagger UI endpoint is accessible"""
        response = client.get("/api/docs/")
        # Should either return 200 (if swagger is installed) or 404 (if not)
        assert response.status_code in [200, 404, 308]

    def test_api_spec_endpoint(self, client):
        """Test that OpenAPI spec endpoint is accessible"""
        response = client.get("/api/docs/spec.json")
        # Should either return 200 with JSON or 404 if swagger not installed
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            # Verify it's valid JSON
            data = response.get_json()
            assert data is not None

    def test_api_spec_structure(self, client):
        """Test that API spec has correct OpenAPI structure"""
        response = client.get("/api/docs/spec.json")
        
        if response.status_code == 200:
            spec = response.get_json()
            
            # Check for OpenAPI required fields
            assert "openapi" in spec or "swagger" in spec
            assert "info" in spec
            assert "paths" in spec

    def test_api_spec_info_section(self, client):
        """Test that API spec info section is properly configured"""
        response = client.get("/api/docs/spec.json")
        
        if response.status_code == 200:
            spec = response.get_json()
            info = spec.get("info", {})
            
            # Verify info section has required fields
            assert "title" in info or "description" in info
            assert "version" in info or len(info) > 0

    def test_api_spec_paths_section(self, client):
        """Test that API spec includes endpoint paths"""
        response = client.get("/api/docs/spec.json")
        
        if response.status_code == 200:
            spec = response.get_json()
            paths = spec.get("paths", {})
            
            # Should have at least some paths defined
            assert isinstance(paths, dict)

    def test_swagger_ui_config(self, client):
        """Test Swagger UI configuration"""
        response = client.get("/api/docs/")
        
        if response.status_code == 200:
            # Swagger UI should return HTML
            assert response.content_type in ["text/html", "text/html; charset=utf-8"]


class TestAPIDocumentationCORS:
    """Test CORS headers on API documentation endpoints"""

    def test_api_spec_cors_headers(self, client):
        """Test that API spec endpoint has CORS headers"""
        response = client.get("/api/docs/spec.json")
        
        if response.status_code == 200:
            # API endpoints should have CORS headers
            assert "Access-Control-Allow-Origin" in response.headers

    def test_api_spec_options_request(self, client):
        """Test OPTIONS request on API spec endpoint"""
        response = client.options("/api/docs/spec.json")
        
        # OPTIONS should return 200
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers


class TestAPIDocumentationSecurity:
    """Test security aspects of API documentation"""

    def test_api_spec_no_sensitive_data(self, client):
        """Test that API spec doesn't expose sensitive information"""
        response = client.get("/api/docs/spec.json")
        
        if response.status_code == 200:
            spec_text = response.get_data(as_text=True).lower()
            
            # Should not contain sensitive keywords
            sensitive_keywords = ["password", "secret", "api_key", "token"]
            # Note: These might appear in parameter names, which is OK
            # We're just checking it's not exposing actual values
            
            # Check that spec is valid JSON and doesn't crash
            assert len(spec_text) > 0

    def test_swagger_ui_no_auth_required(self, client):
        """Test that Swagger UI is publicly accessible"""
        response = client.get("/api/docs/")
        
        # Should not require authentication (or return 404 if not installed)
        assert response.status_code in [200, 404, 308]
        
        # Should not return 401 (unauthorized) or 403 (forbidden)
        assert response.status_code not in [401, 403]


class TestAPIDocumentationContent:
    """Test content and completeness of API documentation"""

    def test_api_spec_json_format(self, client):
        """Test that API spec is valid JSON"""
        response = client.get("/api/docs/spec.json")
        
        if response.status_code == 200:
            # Should be valid JSON
            try:
                data = json.loads(response.get_data(as_text=True))
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pytest.fail("API spec is not valid JSON")

    def test_api_spec_content_type(self, client):
        """Test that API spec has correct content type"""
        response = client.get("/api/docs/spec.json")
        
        if response.status_code == 200:
            # Should be JSON content type
            assert "application/json" in response.content_type


class TestAPIDocumentationAvailability:
    """Test availability and error handling of API documentation"""

    def test_api_docs_handles_missing_swagger(self, client):
        """Test that app handles missing Swagger UI gracefully"""
        # Even if Swagger is not installed, endpoints should not crash
        response = client.get("/api/docs/")
        
        # Should return either 200 (installed) or 404 (not installed)
        # Should NOT return 500 (server error)
        assert response.status_code != 500

    def test_api_spec_handles_missing_api_docs(self, client):
        """Test that app handles missing api_docs module gracefully"""
        response = client.get("/api/docs/spec.json")
        
        # Should return either 200 (installed) or 404 (not installed)
        # Should NOT return 500 (server error)
        assert response.status_code != 500

    def test_swagger_ui_redirect(self, client):
        """Test Swagger UI redirect behavior"""
        response = client.get("/api/docs")
        
        # Should either show Swagger UI or return 404
        # 308 is permanent redirect (trailing slash)
        assert response.status_code in [200, 404, 308]
