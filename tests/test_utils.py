"""
Unit tests for utility functions (utils.py)
"""
import pytest
from utils import get_pagination_params, build_pagination_metadata, build_paginated_response
from unittest.mock import Mock


class TestGetPaginationParams:
    """Tests for get_pagination_params function"""
    
    def test_default_values(self):
        """Test default pagination parameters"""
        request_args = {}
        limit, offset = get_pagination_params(request_args)
        
        assert limit == 20  # DEFAULT_PAGE_SIZE from config
        assert offset == 0
    
    def test_valid_params(self):
        """Test valid limit and offset"""
        request_args = {'limit': '10', 'offset': '5'}
        limit, offset = get_pagination_params(request_args)
        
        assert limit == 10
        assert offset == 5
    
    def test_max_limit_enforcement(self):
        """Test that limit is capped at MAX_PAGE_SIZE"""
        request_args = {'limit': '1000'}
        limit, offset = get_pagination_params(request_args)
        
        assert limit == 100  # MAX_PAGE_SIZE from config
        assert offset == 0
    
    def test_invalid_limit(self):
        """Test invalid limit falls back to default"""
        request_args = {'limit': 'invalid'}
        limit, offset = get_pagination_params(request_args)
        
        assert limit == 20  # DEFAULT_PAGE_SIZE
        assert offset == 0
    
    def test_negative_offset(self):
        """Test negative offset is set to 0"""
        request_args = {'offset': '-10'}
        limit, offset = get_pagination_params(request_args)
        
        assert limit == 20
        assert offset == 0
    
    def test_zero_limit(self):
        """Test zero limit falls back to default"""
        request_args = {'limit': '0'}
        limit, offset = get_pagination_params(request_args)
        
        assert limit == 20  # DEFAULT_PAGE_SIZE
        assert offset == 0


class TestBuildPaginationMetadata:
    """Tests for build_pagination_metadata function"""
    
    def test_first_page(self):
        """Test metadata for first page"""
        metadata = build_pagination_metadata(total_count=100, limit=10, offset=0)
        
        assert metadata['total'] == 100
        assert metadata['limit'] == 10
        assert metadata['offset'] == 0
        assert metadata['has_more'] is True
        assert metadata['current_page'] == 1
        assert metadata['total_pages'] == 10
    
    def test_middle_page(self):
        """Test metadata for middle page"""
        metadata = build_pagination_metadata(total_count=100, limit=10, offset=50)
        
        assert metadata['total'] == 100
        assert metadata['limit'] == 10
        assert metadata['offset'] == 50
        assert metadata['has_more'] is True
        assert metadata['current_page'] == 6
        assert metadata['total_pages'] == 10
    
    def test_last_page(self):
        """Test metadata for last page"""
        metadata = build_pagination_metadata(total_count=100, limit=10, offset=90)
        
        assert metadata['total'] == 100
        assert metadata['limit'] == 10
        assert metadata['offset'] == 90
        assert metadata['has_more'] is False
        assert metadata['current_page'] == 10
        assert metadata['total_pages'] == 10
    
    def test_empty_results(self):
        """Test metadata with no results"""
        metadata = build_pagination_metadata(total_count=0, limit=10, offset=0)
        
        assert metadata['total'] == 0
        assert metadata['has_more'] is False
        assert metadata['current_page'] == 1
        assert metadata['total_pages'] == 0  # 0 pages when no results
    
    def test_partial_last_page(self):
        """Test metadata when last page is partial"""
        metadata = build_pagination_metadata(total_count=95, limit=10, offset=90)
        
        assert metadata['total'] == 95
        assert metadata['has_more'] is False
        assert metadata['current_page'] == 10
        assert metadata['total_pages'] == 10


class TestBuildPaginatedResponse:
    """Tests for build_paginated_response function"""
    
    def test_basic_response(self):
        """Test basic paginated response structure"""
        data = [{'id': 1}, {'id': 2}]
        response = build_paginated_response(
            data=data,
            total_count=100,
            limit=10,
            offset=0
        )
        
        assert 'data' in response
        assert 'pagination' in response
        assert response['data'] == data
        assert response['pagination']['total'] == 100
        assert response['pagination']['limit'] == 10
        assert response['pagination']['offset'] == 0
    
    def test_empty_data(self):
        """Test response with empty data"""
        response = build_paginated_response(
            data=[],
            total_count=0,
            limit=10,
            offset=0
        )
        
        assert response['data'] == []
        assert response['pagination']['total'] == 0
        assert response['pagination']['has_more'] is False
    
    def test_response_structure(self):
        """Test that response has correct structure"""
        data = [{'id': 1}]
        response = build_paginated_response(
            data=data,
            total_count=50,
            limit=10,
            offset=20
        )
        
        # Check data field
        assert isinstance(response['data'], list)
        
        # Check pagination field
        assert 'total' in response['pagination']
        assert 'limit' in response['pagination']
        assert 'offset' in response['pagination']
        assert 'has_more' in response['pagination']
        assert 'current_page' in response['pagination']
        assert 'total_pages' in response['pagination']
