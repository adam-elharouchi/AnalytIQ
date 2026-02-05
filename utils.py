"""
AnalytIQ Utility Functions
Shared utilities for pagination, validation, and common operations
"""
import config


def get_pagination_params(request_args):
    """
    Extract and validate pagination parameters from request arguments
    
    Args:
        request_args: Flask request.args object
        
    Returns:
        tuple: (limit, offset) with validated values
    """
    try:
        limit = int(request_args.get('limit', config.DEFAULT_PAGE_SIZE))
        offset = int(request_args.get('offset', 0))
    except (ValueError, TypeError):
        # If invalid values, use defaults
        limit = config.DEFAULT_PAGE_SIZE
        offset = 0
    
    # Enforce maximum page size
    if limit > config.MAX_PAGE_SIZE:
        limit = config.MAX_PAGE_SIZE
    
    # Ensure non-negative values
    if limit < 1:
        limit = config.DEFAULT_PAGE_SIZE
    if offset < 0:
        offset = 0
    
    return limit, offset


def build_pagination_metadata(total_count, limit, offset):
    """
    Build pagination metadata for API responses
    
    Args:
        total_count: Total number of items available
        limit: Number of items per page
        offset: Current offset
        
    Returns:
        dict: Pagination metadata including total, limit, offset, has_more
    """
    has_more = (offset + limit) < total_count
    
    return {
        'total': total_count,
        'limit': limit,
        'offset': offset,
        'has_more': has_more,
        'current_page': (offset // limit) + 1 if limit > 0 else 1,
        'total_pages': (total_count + limit - 1) // limit if limit > 0 else 1
    }


def build_paginated_response(data, total_count, limit, offset, data_key='data'):
    """
    Build a standardized paginated API response
    
    Args:
        data: List of items for current page
        total_count: Total number of items available
        limit: Number of items per page
        offset: Current offset
        data_key: Key name for the data array in response (default: 'data')
        
    Returns:
        dict: Standardized response with data and pagination metadata
    """
    return {
        data_key: data,
        'pagination': build_pagination_metadata(total_count, limit, offset)
    }
