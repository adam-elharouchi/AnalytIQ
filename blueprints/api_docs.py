"""
AnalytIQ API Documentation Generator
Generates OpenAPI 3.0 specification for all API endpoints.
"""

import json

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

# ---------------------------------------------------------------------------
# Shared response/schema fragments
# ---------------------------------------------------------------------------
_PAGINATION = {
    "type": "object",
    "properties": {
        "total": {"type": "integer"},
        "limit": {"type": "integer"},
        "offset": {"type": "integer"},
        "has_more": {"type": "boolean"},
        "current_page": {"type": "integer"},
        "total_pages": {"type": "integer"},
    },
}

_CLASS_OBJ = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "class_code": {"type": "string"},
        "professor_id": {"type": "string"},
        "student_count": {"type": "integer"},
        "chapter_count": {"type": "integer"},
        "created_at": {"type": "string", "format": "date-time"},
    },
}

_CHAPTER_OBJ = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "class_id": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "pdf_filename": {"type": "string"},
        "created_at": {"type": "string", "format": "date-time"},
    },
}

_EXERCISE_OBJ = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "chapter_id": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
        "starter_code": {"type": "string"},
        "solution": {"type": "string"},
        "created_at": {"type": "string", "format": "date-time"},
    },
}

_USER_OBJ = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "role": {"type": "string", "enum": ["student", "professor"]},
    },
}

_CONVERSATION_OBJ = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "archived": {"type": "boolean"},
        "created_at": {"type": "string", "format": "date-time"},
        "messages": {"type": "array", "items": {"type": "object"}},
    },
}

_401 = {"description": "Missing or invalid Bearer token"}
_403 = {"description": "Forbidden — insufficient role or ownership"}
_404 = {"description": "Resource not found"}
_400 = {"description": "Invalid request body or missing required fields"}
_500 = {"description": "Internal server error"}

_BEARER_SECURITY = [{"BearerAuth": []}]


def create_api_spec() -> APISpec:
    """Build and return the full OpenAPI 3.0 specification."""

    spec = APISpec(
        title="AnalytIQ API",
        version="1.0.0",
        openapi_version="3.0.0",
        info=dict(
            description=(
                "AnalytIQ Learning Management System API. "
                "All protected routes require an `Authorization: Bearer <token>` header. "
                "Tokens are obtained from `/api/users/signin`."
            ),
            contact=dict(name="AnalytIQ Support", email="support@myanalytiq.org"),
        ),
        servers=[
            dict(url="https://myanalytiq.org", description="Production"),
            dict(url="http://localhost:5000", description="Local dev"),
        ],
        tags=[
            dict(name="Auth", description="Signup, signin, password reset"),
            dict(name="Users", description="Profile, settings, conversations"),
            dict(name="Classes", description="Class CRUD, enrollment, resources, leaderboards"),
            dict(
                name="Chapters",
                description="Chapter upload (pdf/txt/csv/ipynb/docx), exercise generation",
            ),
            dict(name="Exercises", description="Exercise CRUD, submission, progress"),
            dict(name="AI", description="Gemini chat proxy"),
            dict(name="Health", description="Health check, task status, contact"),
        ],
        plugins=[MarshmallowPlugin()],
    )

    spec.components.security_scheme(
        "BearerAuth", {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    )

    # =========================================================================
    # AUTH
    # =========================================================================

    spec.path(
        path="/api/users/signup",
        operations=dict(
            post=dict(
                tags=["Auth"],
                summary="Register a new user",
                description="Register a new user. All email addresses are accepted; role defaults to student. Password: 8–72 chars.",
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name", "email", "password"],
                                "properties": {
                                    "name": {"type": "string", "example": "Ada Lovelace"},
                                    "email": {
                                        "type": "string",
                                        "format": "email",
                                        "example": "ada@example.com",
                                    },
                                    "password": {
                                        "type": "string",
                                        "format": "password",
                                        "minLength": 8,
                                        "maxLength": 72,
                                    },
                                },
                            }
                        }
                    },
                ),
                responses={
                    "201": {
                        "description": "User created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"token": {"type": "string"}, "user": _USER_OBJ},
                                }
                            }
                        },
                    },
                    "400": _400,
                },
            )
        ),
    )

    spec.path(
        path="/api/users/signin",
        operations=dict(
            post=dict(
                tags=["Auth"],
                summary="Sign in",
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["email", "password"],
                                "properties": {
                                    "email": {"type": "string", "format": "email"},
                                    "password": {"type": "string", "format": "password"},
                                },
                            }
                        }
                    },
                ),
                responses={
                    "200": {
                        "description": "Sign-in successful",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"token": {"type": "string"}, "user": _USER_OBJ},
                                }
                            }
                        },
                    },
                    "401": {"description": "Invalid credentials"},
                },
            )
        ),
    )

    spec.path(
        path="/api/users/forgot-password",
        operations=dict(
            post=dict(
                tags=["Auth"],
                summary="Request password reset email",
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["email"],
                                "properties": {"email": {"type": "string", "format": "email"}},
                            }
                        }
                    },
                ),
                responses={
                    "200": {"description": "Reset email sent (silently ignored if unknown email)"},
                    "400": _400,
                },
            )
        ),
    )

    spec.path(
        path="/api/users/reset-password",
        operations=dict(
            post=dict(
                tags=["Auth"],
                summary="Reset password with token",
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["token", "new_password"],
                                "properties": {
                                    "token": {"type": "string"},
                                    "new_password": {
                                        "type": "string",
                                        "format": "password",
                                        "minLength": 8,
                                        "maxLength": 72,
                                    },
                                },
                            }
                        }
                    },
                ),
                responses={"200": {"description": "Password reset"}, "400": _400, "401": _401},
            )
        ),
    )

    # =========================================================================
    # USERS
    # =========================================================================

    spec.path(
        path="/api/users/profile",
        operations=dict(
            get=dict(
                tags=["Users"],
                summary="Get own profile",
                security=_BEARER_SECURITY,
                responses={
                    "200": {
                        "description": "User profile",
                        "content": {"application/json": {"schema": _USER_OBJ}},
                    },
                    "401": _401,
                },
            ),
            put=dict(
                tags=["Users"],
                summary="Update own profile",
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {"type": "object", "properties": {"name": {"type": "string"}}}
                        }
                    },
                ),
                responses={"200": {"description": "Updated profile"}, "400": _400, "401": _401},
            ),
        ),
    )

    spec.path(
        path="/api/users/settings",
        operations=dict(
            get=dict(
                tags=["Users"],
                summary="Get user settings",
                security=_BEARER_SECURITY,
                responses={"200": {"description": "Settings object"}, "401": _401},
            ),
            put=dict(
                tags=["Users"],
                summary="Update user settings",
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True, content={"application/json": {"schema": {"type": "object"}}}
                ),
                responses={"200": {"description": "Updated settings"}, "401": _401},
            ),
        ),
    )

    spec.path(
        path="/api/users/password",
        operations=dict(
            put=dict(
                tags=["Users"],
                summary="Change password (authenticated)",
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["current_password", "new_password"],
                                "properties": {
                                    "current_password": {"type": "string", "format": "password"},
                                    "new_password": {
                                        "type": "string",
                                        "format": "password",
                                        "minLength": 8,
                                        "maxLength": 72,
                                    },
                                },
                            }
                        }
                    },
                ),
                responses={"200": {"description": "Password changed"}, "400": _400, "401": _401},
            )
        ),
    )

    spec.path(
        path="/api/users/delete",
        operations=dict(
            delete=dict(
                tags=["Users"],
                summary="Delete own account",
                security=_BEARER_SECURITY,
                responses={"200": {"description": "Account deleted"}, "401": _401},
            )
        ),
    )

    spec.path(
        path="/api/users/preferences",
        operations=dict(
            get=dict(
                tags=["Users"],
                summary="Get UI preferences",
                security=_BEARER_SECURITY,
                responses={"200": {"description": "Preferences"}, "401": _401},
            ),
            put=dict(
                tags=["Users"],
                summary="Save UI preferences",
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True, content={"application/json": {"schema": {"type": "object"}}}
                ),
                responses={"200": {"description": "Saved"}, "401": _401},
            ),
        ),
    )

    spec.path(
        path="/api/users/practice-progress",
        operations=dict(
            get=dict(
                tags=["Users"],
                summary="Get practice progress",
                security=_BEARER_SECURITY,
                responses={"200": {"description": "Progress records"}, "401": _401},
            ),
            put=dict(
                tags=["Users"],
                summary="Save practice progress",
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True, content={"application/json": {"schema": {"type": "object"}}}
                ),
                responses={"200": {"description": "Saved"}, "401": _401},
            ),
        ),
    )

    spec.path(
        path="/api/users/ai-digest",
        operations=dict(
            get=dict(
                tags=["Users"],
                summary="Get AI digest",
                security=_BEARER_SECURITY,
                responses={"200": {"description": "Digest"}, "401": _401},
            ),
            put=dict(
                tags=["Users"],
                summary="Update AI digest",
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True, content={"application/json": {"schema": {"type": "object"}}}
                ),
                responses={"200": {"description": "Updated"}, "401": _401},
            ),
        ),
    )

    spec.path(
        path="/api/users/ai-memory",
        operations=dict(
            get=dict(
                tags=["Users"],
                summary="Get AI memory",
                security=_BEARER_SECURITY,
                responses={"200": {"description": "Memory"}, "401": _401},
            ),
            put=dict(
                tags=["Users"],
                summary="Update AI memory",
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True, content={"application/json": {"schema": {"type": "object"}}}
                ),
                responses={"200": {"description": "Updated"}, "401": _401},
            ),
        ),
    )

    spec.path(
        path="/api/users/conversations",
        operations=dict(
            get=dict(
                tags=["Users"],
                summary="List conversations (paginated)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "archived",
                        "in": "query",
                        "schema": {"type": "boolean", "default": False},
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 20, "maximum": 100},
                    },
                    {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}},
                ],
                responses={
                    "200": {
                        "description": "Conversations",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "conversations": {
                                            "type": "array",
                                            "items": _CONVERSATION_OBJ,
                                        },
                                        "pagination": _PAGINATION,
                                    },
                                }
                            }
                        },
                    },
                    "401": _401,
                },
            ),
            post=dict(
                tags=["Users"],
                summary="Create conversation",
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["title"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "messages": {"type": "array", "items": {"type": "object"}},
                                },
                            }
                        }
                    },
                ),
                responses={"201": {"description": "Created"}, "400": _400, "401": _401},
            ),
        ),
    )

    spec.path(
        path="/api/users/conversations/{conversation_id}",
        operations=dict(
            get=dict(
                tags=["Users"],
                summary="Get conversation with messages",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "conversation_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {
                        "description": "Conversation",
                        "content": {"application/json": {"schema": _CONVERSATION_OBJ}},
                    },
                    "401": _401,
                    "404": _404,
                },
            ),
            put=dict(
                tags=["Users"],
                summary="Update conversation (title / archive / messages)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "conversation_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "archived": {"type": "boolean"},
                                    "messages": {"type": "array", "items": {"type": "object"}},
                                },
                            }
                        }
                    },
                ),
                responses={"200": {"description": "Updated"}, "401": _401, "404": _404},
            ),
            delete=dict(
                tags=["Users"],
                summary="Delete conversation",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "conversation_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={"200": {"description": "Deleted"}, "401": _401, "404": _404},
            ),
        ),
    )

    spec.path(
        path="/api/users/conversations/{conversation_id}/messages",
        operations=dict(
            post=dict(
                tags=["Users"],
                summary="Append message to conversation",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "conversation_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["role", "content"],
                                "properties": {
                                    "role": {"type": "string", "enum": ["user", "assistant"]},
                                    "content": {"type": "string"},
                                },
                            }
                        }
                    },
                ),
                responses={
                    "201": {"description": "Appended"},
                    "400": _400,
                    "401": _401,
                    "404": _404,
                },
            )
        ),
    )

    # =========================================================================
    # CLASSES
    # =========================================================================

    spec.path(
        path="/api/classes",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="List classes for current user",
                security=_BEARER_SECURITY,
                description="Professors see their own classes; students see enrolled classes.",
                parameters=[
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 20, "maximum": 100},
                    },
                    {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}},
                ],
                responses={
                    "200": {
                        "description": "Classes",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "classes": {"type": "array", "items": _CLASS_OBJ},
                                        "pagination": _PAGINATION,
                                    },
                                }
                            }
                        },
                    },
                    "401": _401,
                },
            ),
            post=dict(
                tags=["Classes"],
                summary="Create class (professor only)",
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name", "class_code"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "class_code": {
                                        "type": "string",
                                        "minLength": 3,
                                        "maxLength": 20,
                                    },
                                },
                            }
                        }
                    },
                ),
                responses={
                    "201": {"description": "Created"},
                    "400": _400,
                    "401": _401,
                    "403": _403,
                    "409": {"description": "Class code already in use"},
                },
            ),
        ),
    )

    spec.path(
        path="/api/classes/{class_id}",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="Get class details",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {
                        "description": "Class",
                        "content": {"application/json": {"schema": _CLASS_OBJ}},
                    },
                    "401": _401,
                    "404": _404,
                },
            ),
            put=dict(
                tags=["Classes"],
                summary="Update class (professor/owner)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                            }
                        }
                    },
                ),
                responses={
                    "200": {"description": "Updated"},
                    "401": _401,
                    "403": _403,
                    "404": _404,
                },
            ),
            delete=dict(
                tags=["Classes"],
                summary="Delete class (professor/owner)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {"description": "Deleted"},
                    "401": _401,
                    "403": _403,
                    "404": _404,
                },
            ),
        ),
    )

    spec.path(
        path="/api/classes/enroll",
        operations=dict(
            post=dict(
                tags=["Classes"],
                summary="Enroll in a class via class code",
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["class_code"],
                                "properties": {"class_code": {"type": "string"}},
                            }
                        }
                    },
                ),
                responses={
                    "200": {"description": "Enrolled"},
                    "400": _400,
                    "401": _401,
                    "404": _404,
                    "409": {"description": "Already enrolled"},
                },
            )
        ),
    )

    spec.path(
        path="/api/classes/enrolled",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="List enrolled classes (student)",
                security=_BEARER_SECURITY,
                responses={"200": {"description": "Enrolled classes"}, "401": _401},
            )
        ),
    )

    spec.path(
        path="/api/classes/{class_id}/students",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="List enrolled students (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {"description": "Student list"},
                    "401": _401,
                    "403": _403,
                    "404": _404,
                },
            )
        ),
    )

    spec.path(
        path="/api/classes/{class_id}/progress",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="Class-wide exercise progress",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={"200": {"description": "Aggregate progress"}, "401": _401, "404": _404},
            )
        ),
    )

    spec.path(
        path="/api/progress",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="Own progress across all classes",
                security=_BEARER_SECURITY,
                responses={"200": {"description": "Progress records"}, "401": _401},
            )
        ),
    )

    spec.path(
        path="/api/students/{student_id}/progress",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="Student progress (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "student_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={"200": {"description": "Progress"}, "401": _401, "403": _403},
            )
        ),
    )

    spec.path(
        path="/api/classes/{class_id}/leaderboard/average",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="Class average score leaderboard",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={"200": {"description": "Leaderboard rows"}, "401": _401, "404": _404},
            )
        ),
    )

    spec.path(
        path="/api/classes/{class_id}/leaderboard/exercise/{exercise_id}",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="Per-exercise leaderboard within a class",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "exercise_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                responses={"200": {"description": "Leaderboard"}, "401": _401, "404": _404},
            )
        ),
    )

    spec.path(
        path="/api/classes/{class_id}/resources",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="List class resources",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={"200": {"description": "Resources"}, "401": _401, "404": _404},
            ),
            post=dict(
                tags=["Classes"],
                summary="Add a link resource (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["title", "url"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "url": {"type": "string", "format": "uri"},
                                    "description": {"type": "string"},
                                },
                            }
                        }
                    },
                ),
                responses={"201": {"description": "Added"}, "400": _400, "401": _401, "403": _403},
            ),
        ),
    )

    spec.path(
        path="/api/classes/{class_id}/resources/upload",
        operations=dict(
            post=dict(
                tags=["Classes"],
                summary="Upload a file resource (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                requestBody=dict(
                    required=True,
                    content={
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "file": {"type": "string", "format": "binary"},
                                    "title": {"type": "string"},
                                },
                            }
                        }
                    },
                ),
                responses={
                    "201": {"description": "Uploaded"},
                    "400": _400,
                    "401": _401,
                    "403": _403,
                },
            )
        ),
    )

    spec.path(
        path="/api/resources/{resource_id}/download",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="Download a resource file",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "resource_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={"200": {"description": "File stream"}, "401": _401, "404": _404},
            )
        ),
    )

    spec.path(
        path="/api/classes/{class_id}/resources/{resource_id}",
        operations=dict(
            put=dict(
                tags=["Classes"],
                summary="Update resource metadata (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "resource_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                requestBody=dict(
                    required=True, content={"application/json": {"schema": {"type": "object"}}}
                ),
                responses={
                    "200": {"description": "Updated"},
                    "401": _401,
                    "403": _403,
                    "404": _404,
                },
            ),
            delete=dict(
                tags=["Classes"],
                summary="Delete resource (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "resource_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                responses={
                    "200": {"description": "Deleted"},
                    "401": _401,
                    "403": _403,
                    "404": _404,
                },
            ),
        ),
    )

    spec.path(
        path="/api/resources/files/{filename}",
        operations=dict(
            get=dict(
                tags=["Classes"],
                summary="Serve a stored resource file",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "filename",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={"200": {"description": "File bytes"}, "401": _401, "404": _404},
            )
        ),
    )

    # =========================================================================
    # CHAPTERS
    # =========================================================================

    spec.path(
        path="/api/chapters/upload-url",
        operations=dict(
            get=dict(
                tags=["Chapters"],
                summary="Get Supabase presigned upload URL",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "filename",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {
                        "description": "Presigned URL",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "upload_url": {"type": "string"},
                                        "storage_path": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "401": _401,
                },
            )
        ),
    )

    spec.path(
        path="/api/classes/{class_id}/chapters",
        operations=dict(
            post=dict(
                tags=["Chapters"],
                summary="Upload a chapter file",
                description="Field: `pdf_file`. Accepted: .pdf, .txt, .csv, .ipynb, .docx. Max 50 MB.",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                requestBody=dict(
                    required=True,
                    content={
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "required": ["pdf_file", "title"],
                                "properties": {
                                    "pdf_file": {"type": "string", "format": "binary"},
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "exercise_mode": {"type": "string", "enum": ["auto", "manual"]},
                                },
                            }
                        }
                    },
                ),
                responses={
                    "201": {"description": "Chapter created"},
                    "400": _400,
                    "401": _401,
                    "403": _403,
                },
            ),
            get=dict(
                tags=["Chapters"],
                summary="List chapters in a class",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {
                        "description": "Chapters",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "chapters": {"type": "array", "items": _CHAPTER_OBJ}
                                    },
                                }
                            }
                        },
                    },
                    "401": _401,
                    "404": _404,
                },
            ),
        ),
    )

    spec.path(
        path="/api/chapters/{chapter_id}",
        operations=dict(
            put=dict(
                tags=["Chapters"],
                summary="Update chapter metadata (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "chapter_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                            }
                        }
                    },
                ),
                responses={
                    "200": {"description": "Updated"},
                    "401": _401,
                    "403": _403,
                    "404": _404,
                },
            ),
            delete=dict(
                tags=["Chapters"],
                summary="Delete chapter (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "chapter_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {"description": "Deleted"},
                    "401": _401,
                    "403": _403,
                    "404": _404,
                },
            ),
        ),
    )

    spec.path(
        path="/api/chapters/{chapter_id}/generate-exercises",
        operations=dict(
            post=dict(
                tags=["Chapters"],
                summary="Trigger AI exercise generation",
                description="Calls Gemini to produce exercises from extracted chapter text. Returns 202 if Celery async is enabled.",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "chapter_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {
                        "description": "Exercises generated",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "exercises": {"type": "array", "items": _EXERCISE_OBJ}
                                    },
                                }
                            }
                        },
                    },
                    "202": {"description": "Generation queued (async)"},
                    "400": {"description": "No extractable text content"},
                    "401": _401,
                    "403": _403,
                    "404": _404,
                },
            )
        ),
    )

    spec.path(
        path="/api/chapters/{chapter_id}/exercises",
        operations=dict(
            get=dict(
                tags=["Chapters"],
                summary="List exercises for a chapter",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "chapter_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {
                        "description": "Exercises",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "exercises": {"type": "array", "items": _EXERCISE_OBJ}
                                    },
                                }
                            }
                        },
                    },
                    "401": _401,
                    "404": _404,
                },
            )
        ),
    )

    spec.path(
        path="/api/classes/{class_id}/chapters/{chapter_id}/exercises",
        operations=dict(
            post=dict(
                tags=["Chapters"],
                summary="Create a manual exercise for a chapter (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "class_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "chapter_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["title", "description"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "difficulty": {
                                        "type": "string",
                                        "enum": ["easy", "medium", "hard"],
                                    },
                                    "starter_code": {"type": "string"},
                                    "solution": {"type": "string"},
                                },
                            }
                        }
                    },
                ),
                responses={
                    "201": {"description": "Exercise created"},
                    "400": _400,
                    "401": _401,
                    "403": _403,
                },
            )
        ),
    )

    spec.path(
        path="/api/chapters/{chapter_id}/pdf",
        operations=dict(
            get=dict(
                tags=["Chapters"],
                summary="Get chapter file download URL",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "chapter_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {"description": "Download URL or file stream"},
                    "401": _401,
                    "404": _404,
                },
            )
        ),
    )

    # =========================================================================
    # EXERCISES
    # =========================================================================

    spec.path(
        path="/api/exercises/progress",
        operations=dict(
            get=dict(
                tags=["Exercises"],
                summary="Own exercise submission progress",
                security=_BEARER_SECURITY,
                responses={"200": {"description": "Progress records"}, "401": _401},
            )
        ),
    )

    spec.path(
        path="/api/exercises/{exercise_id}",
        operations=dict(
            get=dict(
                tags=["Exercises"],
                summary="Get exercise details",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "exercise_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {
                        "description": "Exercise",
                        "content": {"application/json": {"schema": _EXERCISE_OBJ}},
                    },
                    "401": _401,
                    "404": _404,
                },
            ),
            put=dict(
                tags=["Exercises"],
                summary="Update exercise (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "exercise_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                requestBody=dict(
                    required=True, content={"application/json": {"schema": {"type": "object"}}}
                ),
                responses={
                    "200": {"description": "Updated"},
                    "401": _401,
                    "403": _403,
                    "404": _404,
                },
            ),
            delete=dict(
                tags=["Exercises"],
                summary="Delete exercise (professor only)",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "exercise_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {"description": "Deleted"},
                    "401": _401,
                    "403": _403,
                    "404": _404,
                },
            ),
        ),
    )

    spec.path(
        path="/api/exercises/{exercise_id}/leaderboard",
        operations=dict(
            get=dict(
                tags=["Exercises"],
                summary="Leaderboard for a specific exercise",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "exercise_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 10, "maximum": 100},
                    },
                ],
                responses={"200": {"description": "Leaderboard"}, "401": _401, "404": _404},
            )
        ),
    )

    spec.path(
        path="/api/leaderboard/grand",
        operations=dict(
            get=dict(
                tags=["Exercises"],
                summary="Grand leaderboard across all exercises",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 10, "maximum": 100},
                    }
                ],
                responses={"200": {"description": "Grand leaderboard"}, "401": _401},
            )
        ),
    )

    # =========================================================================
    # AI
    # =========================================================================

    spec.path(
        path="/api/ai/chat",
        operations=dict(
            post=dict(
                tags=["AI"],
                summary="Gemini chat proxy",
                description=(
                    "Proxies to Google Gemini API. "
                    "Max payload: 50 KB. Max messages in `contents`: 100. "
                    "Rate limit: 20 req/min + 100 req/hr per user."
                ),
                security=_BEARER_SECURITY,
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["contents"],
                                "properties": {
                                    "contents": {
                                        "type": "array",
                                        "maxItems": 100,
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "role": {
                                                    "type": "string",
                                                    "enum": ["user", "model"],
                                                },
                                                "parts": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {"text": {"type": "string"}},
                                                    },
                                                },
                                            },
                                        },
                                    },
                                    "model": {"type": "string", "default": "gemini-3.5-flash"},
                                    "system_instruction": {"type": "string"},
                                },
                            }
                        }
                    },
                ),
                responses={
                    "200": {
                        "description": "Gemini response (passes through upstream response structure)"
                    },
                    "400": {"description": "Empty contents or missing field"},
                    "401": _401,
                    "413": {"description": "Payload exceeds 50 KB"},
                    "429": {"description": "Per-user rate limit exceeded"},
                    "503": {"description": "Gemini API unavailable"},
                },
            )
        ),
    )

    # =========================================================================
    # HEALTH & MISC
    # =========================================================================

    spec.path(
        path="/api/health",
        operations=dict(
            get=dict(
                tags=["Health"],
                summary="Health check (public, cached 30s)",
                responses={
                    "200": {
                        "description": "Healthy",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {
                                            "type": "string",
                                            "enum": ["healthy", "degraded"],
                                        },
                                        "timestamp": {"type": "string", "format": "date-time"},
                                        "services": {"type": "object"},
                                    },
                                }
                            }
                        },
                    },
                    "503": {"description": "One or more critical services unavailable"},
                },
            )
        ),
    )

    spec.path(
        path="/api/health/detail",
        operations=dict(
            get=dict(
                tags=["Health"],
                summary="Detailed health check (auth required)",
                security=_BEARER_SECURITY,
                responses={"200": {"description": "Component details"}, "401": _401},
            )
        ),
    )

    spec.path(
        path="/api/csrf-token",
        operations=dict(
            get=dict(
                tags=["Health"],
                summary="Get CSRF token",
                description="Only relevant when FEATURE_CSRF_PROTECTION=true.",
                responses={
                    "200": {
                        "description": "CSRF token",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "csrf_enabled": {"type": "boolean"},
                                        "csrf_token": {"type": "string"},
                                    },
                                }
                            }
                        },
                    }
                },
            )
        ),
    )

    spec.path(
        path="/api/tasks/{task_id}",
        operations=dict(
            get=dict(
                tags=["Health"],
                summary="Poll Celery async task status",
                security=_BEARER_SECURITY,
                parameters=[
                    {
                        "name": "task_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                responses={
                    "200": {
                        "description": "Task status",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "task_id": {"type": "string"},
                                        "status": {
                                            "type": "string",
                                            "enum": ["PENDING", "STARTED", "SUCCESS", "FAILURE"],
                                        },
                                        "result": {"type": "object"},
                                    },
                                }
                            }
                        },
                    },
                    "401": _401,
                },
            )
        ),
    )

    spec.path(
        path="/api/contact",
        operations=dict(
            post=dict(
                tags=["Health"],
                summary="Submit contact form (public)",
                requestBody=dict(
                    required=True,
                    content={
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name", "email", "message"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"},
                                    "message": {"type": "string"},
                                },
                            }
                        }
                    },
                ),
                responses={
                    "200": {"description": "Sent"},
                    "400": _400,
                    "429": {"description": "Rate limited"},
                },
            )
        ),
    )

    return spec


def get_openapi_spec_json() -> str:
    """Return the OpenAPI specification as a JSON string."""
    return json.dumps(create_api_spec().to_dict(), indent=2)


def get_openapi_spec_dict() -> dict:
    """Return the OpenAPI specification as a dict."""
    return create_api_spec().to_dict()
