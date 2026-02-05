"""
AnalytIQ API Documentation Generator
Generates OpenAPI 3.0 specification for all API endpoints
"""
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
import json


def create_api_spec():
    """Create and return the OpenAPI specification"""
    
    spec = APISpec(
        title="AnalytIQ API",
        version="1.0.0",
        openapi_version="3.0.0",
        info=dict(
            description="AnalytIQ Learning Management System API - Complete reference for all endpoints",
            contact=dict(
                name="AnalytIQ Support",
                email="support@analytiq.com"
            ),
            license=dict(
                name="MIT",
                url="https://opensource.org/licenses/MIT"
            )
        ),
        servers=[
            dict(
                url="https://analytiq-qbfr.onrender.com",
                description="Production server"
            ),
            dict(
                url="http://localhost:5001",
                description="Local development server"
            )
        ],
        tags=[
            dict(name="Authentication", description="User authentication and account management"),
            dict(name="Classes", description="Class management for professors and students"),
            dict(name="Chapters", description="Chapter and content management"),
            dict(name="Exercises", description="Exercise management and progress tracking"),
            dict(name="AI", description="AI-powered features"),
            dict(name="Health", description="System health and monitoring"),
            dict(name="CSRF", description="CSRF token management")
        ]
    )
    
    # ========================================================================
    # AUTHENTICATION ENDPOINTS
    # ========================================================================
    
    spec.path(
        path="/api/users/signup",
        operations=dict(
            post=dict(
                tags=["Authentication"],
                summary="Register a new user",
                description="Create a new user account with email and password",
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name", "email", "password"],
                                "properties": {
                                    "name": {"type": "string", "example": "John Doe"},
                                    "email": {"type": "string", "format": "email", "example": "john@example.com"},
                                    "password": {"type": "string", "format": "password", "example": "SecurePass123!"},
                                    "role": {"type": "string", "enum": ["student", "professor"], "default": "student"}
                                }
                            }
                        }
                    }
                ),
                responses={
                    "201": {
                        "description": "User created successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "user_id": {"type": "string"},
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                        "role": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {"description": "Invalid input or missing required fields"},
                    "409": {"description": "Email already registered"}
                }
            )
        )
    )
    
    spec.path(
        path="/api/users/signin",
        operations=dict(
            post=dict(
                tags=["Authentication"],
                summary="Sign in user",
                description="Authenticate user with email and password",
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["email", "password"],
                                "properties": {
                                    "email": {"type": "string", "format": "email"},
                                    "password": {"type": "string", "format": "password"}
                                }
                            }
                        }
                    }
                ),
                responses={
                    "200": {
                        "description": "Sign in successful",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "user_id": {"type": "string"},
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                        "role": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "401": {"description": "Invalid credentials"}
                }
            )
        )
    )
    
    # ========================================================================
    # CLASS ENDPOINTS
    # ========================================================================
    
    spec.path(
        path="/api/classes",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="Get user's classes (paginated)",
                description="Get all classes for the current user. Professors see their created classes, students see enrolled classes. Supports pagination.",
                parameters=[
                    {
                        "name": "user_id",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "User ID"
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer", "default": 20, "maximum": 100},
                        "description": "Number of items per page"
                    },
                    {
                        "name": "offset",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer", "default": 0, "minimum": 0},
                        "description": "Number of items to skip"
                    }
                ],
                responses={
                    "200": {
                        "description": "List of classes with pagination metadata",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "classes": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "class_id": {"type": "string"},
                                                    "name": {"type": "string"},
                                                    "description": {"type": "string"},
                                                    "created_at": {"type": "string", "format": "date-time"},
                                                    "student_count": {"type": "integer"},
                                                    "chapter_count": {"type": "integer"}
                                                }
                                            }
                                        },
                                        "pagination": {
                                            "type": "object",
                                            "properties": {
                                                "total": {"type": "integer"},
                                                "limit": {"type": "integer"},
                                                "offset": {"type": "integer"},
                                                "has_more": {"type": "boolean"},
                                                "current_page": {"type": "integer"},
                                                "total_pages": {"type": "integer"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            ),
            post=dict(
                tags=["Classes"],
                summary="Create a new class",
                description="Create a new class (professor only)",
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["user_id", "name", "class_code"],
                                "properties": {
                                    "user_id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "class_code": {"type": "string", "minLength": 3, "maxLength": 20}
                                }
                            }
                        }
                    }
                ),
                responses={
                    "201": {"description": "Class created successfully"},
                    "403": {"description": "Only professors can create classes"},
                    "409": {"description": "Class code already in use"}
                }
            )
        )
    )
    
    # ========================================================================
    # CONVERSATION ENDPOINTS
    # ========================================================================
    
    spec.path(
        path="/api/users/conversations",
        operations=dict(
            get=dict(
                tags=["AI"],
                summary="Get user conversations (paginated)",
                description="Get all conversations for a user with pagination support",
                parameters=[
                    {
                        "name": "user_id",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string"}
                    },
                    {
                        "name": "archived",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "boolean", "default": False}
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer", "default": 20, "maximum": 100}
                    },
                    {
                        "name": "offset",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer", "default": 0}
                    }
                ],
                responses={
                    "200": {
                        "description": "List of conversations with pagination",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "conversations": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "string"},
                                                    "title": {"type": "string"},
                                                    "archived": {"type": "boolean"},
                                                    "date": {"type": "string", "format": "date-time"}
                                                }
                                            }
                                        },
                                        "pagination": {
                                            "type": "object",
                                            "properties": {
                                                "total": {"type": "integer"},
                                                "limit": {"type": "integer"},
                                                "offset": {"type": "integer"},
                                                "has_more": {"type": "boolean"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            )
        )
    )
    
    # ========================================================================
    # HEALTH & CSRF ENDPOINTS
    # ========================================================================
    
    spec.path(
        path="/api/health",
        operations=dict(
            get=dict(
                tags=["Health"],
                summary="Health check",
                description="Check the health status of all system components",
                responses={
                    "200": {
                        "description": "All systems healthy",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string", "enum": ["healthy", "degraded"]},
                                        "timestamp": {"type": "string", "format": "date-time"},
                                        "services": {
                                            "type": "object",
                                            "properties": {
                                                "database": {"type": "object"},
                                                "gemini_api": {"type": "object"},
                                                "email": {"type": "object"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "503": {"description": "System degraded or unhealthy"}
                }
            )
        )
    )
    
    spec.path(
        path="/api/csrf-token",
        operations=dict(
            get=dict(
                tags=["CSRF"],
                summary="Get CSRF token",
                description="Generate and return a CSRF token for state-changing requests",
                responses={
                    "200": {
                        "description": "CSRF token generated",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "csrf_enabled": {"type": "boolean"},
                                        "csrf_token": {"type": "string"},
                                        "message": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            )
        )
    )
    
    return spec


def get_openapi_spec_json():
    """Get the OpenAPI specification as JSON string"""
    spec = create_api_spec()
    return json.dumps(spec.to_dict(), indent=2)


def get_openapi_spec_dict():
    """Get the OpenAPI specification as dictionary"""
    spec = create_api_spec()
    return spec.to_dict()
