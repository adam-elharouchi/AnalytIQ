"""
Tests for api_docs.py - OpenAPI specification generation
Mocks marshmallow if not installed
"""
import pytest
import json
import sys
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def mock_marshmallow():
    """Mock marshmallow if not installed"""
    needs_mock = 'marshmallow' not in sys.modules
    if needs_mock:
        mock_mm = MagicMock()
        modules = {
            'marshmallow': mock_mm,
            'marshmallow.fields': mock_mm.fields,
            'marshmallow.schema': mock_mm.schema,
            'apispec': MagicMock(),
            'apispec.ext': MagicMock(),
            'apispec.ext.marshmallow': MagicMock(),
        }
        # Only add if not already present
        added = {}
        for name, mod in modules.items():
            if name not in sys.modules:
                sys.modules[name] = mod
                added[name] = mod
        yield
        # Cleanup
        for name in added:
            if name in sys.modules:
                del sys.modules[name]
    else:
        yield


def _try_import_api_docs():
    """Try to import api_docs, skip if dependencies missing"""
    try:
        # Force reimport
        if 'api_docs' in sys.modules:
            del sys.modules['api_docs']
        import api_docs
        return api_docs
    except (ImportError, ModuleNotFoundError):
        pytest.skip("api_docs dependencies not available")


class TestCreateApiSpec:
    """Test API specification creation"""

    def test_create_api_spec_returns_spec(self):
        """Test that create_api_spec returns a valid spec object"""
        api_docs = _try_import_api_docs()
        spec = api_docs.create_api_spec()
        assert spec is not None

    def test_spec_has_correct_title(self):
        """Test spec has correct title"""
        api_docs = _try_import_api_docs()
        spec = api_docs.create_api_spec()
        spec_dict = spec.to_dict()
        assert spec_dict["info"]["title"] == "AnalytIQ API"

    def test_spec_has_correct_version(self):
        """Test spec has correct version"""
        api_docs = _try_import_api_docs()
        spec = api_docs.create_api_spec()
        spec_dict = spec.to_dict()
        assert spec_dict["info"]["version"] == "1.0.0"

    def test_spec_has_servers(self):
        """Test spec has server definitions"""
        api_docs = _try_import_api_docs()
        spec = api_docs.create_api_spec()
        spec_dict = spec.to_dict()
        assert len(spec_dict["servers"]) >= 1

    def test_spec_has_paths(self):
        """Test spec has API paths defined"""
        api_docs = _try_import_api_docs()
        spec = api_docs.create_api_spec()
        spec_dict = spec.to_dict()
        assert "paths" in spec_dict
        assert len(spec_dict["paths"]) > 0


class TestGetOpenapiSpecJson:
    """Test JSON spec generation"""

    def test_get_spec_json_returns_string(self):
        """Test that get_openapi_spec_json returns a JSON string"""
        api_docs = _try_import_api_docs()
        result = api_docs.get_openapi_spec_json()
        assert isinstance(result, str)

    def test_get_spec_json_is_valid_json(self):
        """Test that the JSON string is valid"""
        api_docs = _try_import_api_docs()
        result = api_docs.get_openapi_spec_json()
        parsed = json.loads(result)
        assert "info" in parsed


class TestGetOpenapiSpecDict:
    """Test dict spec generation"""

    def test_get_spec_dict_returns_dict(self):
        """Test that get_openapi_spec_dict returns a dictionary"""
        api_docs = _try_import_api_docs()
        result = api_docs.get_openapi_spec_dict()
        assert isinstance(result, dict)
        assert "info" in result
