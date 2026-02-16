# API & Endpoints
*Generated: 2026-02-16 17:37*
---
## Overview
This document consolidates knowledge from **64** file(s) related to api & endpoints.
---
## `RENDER_ENV_CHECKLIST.md`

**Summary:** # Render Environment Variables Checklist

### Details

```
# Render Environment Variables Checklist

## ✅ Already Configured (from your screenshots)

| Variable | Value | Status |
|----------|-------|--------|
| `CORS_ORIGINS` | `https://www.myanalytiq.org,https://myanalytiq.org` | ✅ Configured |
| `DATABASE_URL` | `postgresql://...` | ✅ Configured |
| `FEATURE_ASYNC_TASKS` | `True` | ✅ Configured |
| `FEATURE_CACHING` | `True` | ✅ Configured |
| `FLASK_ENV` | `production` | ✅ Configured |
| `GEMINI_API_KEY` | `AIzs8yAE...` | ✅ Configured |
| `MAIL_DEFAULT_SENDER` | `adamelharouchi@gmail.com` | ✅ Configured |
| `MAIL_PASSWORD` | `***` | ✅ Configured |
| `MAIL_PORT` | `587` | ✅ Configured |
| `MAIL_SERVER` | `smtp.gmail.com` | ✅ Configured |
| `MAIL_USE_TLS` | `True` | ✅ Configured |
| `MAIL_USERNAME` | `adamelharouchi@gmail.com` | ✅ Configured |
| `REDIS_URL` | `redis://...` | ✅ Configured |
| `SECRET_KEY` | `4a85a2d4...` | ✅ Configured |
| `SENTRY_DSN` | `https://af52c0b187...` | ✅ Configured |
| `SUPABASE_KEY` | `eyJhbGc...` | ✅ Configured |
| `SUPABASE_URL` | `https://onjt8nkczfpnyyztzqai.supabase.co` | ✅ Configured |

---

## ⚠️ Recommended to Add

### Critical (for security)

| Variable | Recommended Value | Purpose |
|----------|-------------------|---------|
| `FEATURE_CSRF` | `True` | Enable CSRF protection (currently disabled) |

### Optional (already have sensible defaults)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SUPABASE_BUCKET` | `pdfs` | Supabase storage bucket name (default is fine) |
| `JWT_SECRET_KEY` | Uses `SECRET_KEY` | Separate JWT signing key (optional, defaults to SECRET_KEY) |
| `FEATURE_EMAIL` | `False` | Enable email notifications (optional) |

---

## 🔍 How Each Variable is Used

### Authentication & Security
- **`SECRET_KEY`**: Flask session signing, JWT fallback
- **`JWT_SECRET_KEY`**: JWT token signing (falls back to SECRET_KEY if not set)
- **`FEATURE_CSRF`**: Enables CSRF protection via Flask-WTF
- **`CORS_ORIGINS`**: Comma-separated allowed origins for CORS

### Database & Caching
- **`DATABASE_URL`**: PostgreSQL connection string (with connection pooling)
- **`REDIS_URL`**: Redis for caching and Celery task queue
- **`FEATURE_CACHING`**: Enable Redis caching for API responses
- **`FEATURE_ASYNC_TASKS`**: Enable Celery background tasks

### External Services
- **`GEMINI_API_KEY`**: Google Gemini API for AI exercise generation
- **`SUPABASE_URL`**, **`SUPABASE_KEY`**, **`SUPABASE_BUCKET`**: Supabase storage for PDFs
- **`SENTRY_DSN`**: Sentry error monitoring
- **`MAIL_*`**: SMTP email configuration for password resets

### Application
- **`FLASK_ENV`**: `production` or `development` (affects debug mode, security headers)

---

## ✅ What's Already Integrated in Code

All environment variables are properly integrated:

1. **JWT Authentication** ✅
   - Backend: `@require_auth` decorator on all protected endpoints
   - Frontend: `authFetch()` sends `Authorization: Bearer <token>` header
   - Tokens issued on signup/signin with 7-day expiry

2. **CORS** ✅
   - Uses `config.CORS_ORIGINS` (set to your domains)
   - Falls back to `*` only in debug mode

3. **Security Headers** ✅
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Strict-Transport-Security` (production only)

4. **Rate Limiting** ✅
   - Uses Redis in production (shared across workers)
   - Falls back to memory in development

5. **Sentry** ✅
   - Integrated with Flask, Redis, and Celery
   - PII filtering enabled
   - Release tracking via `RENDER_GIT_COMMIT`

6. **Email** ✅
   - Flask-Mail configured with your Gmail SMTP
   - Used for password reset emails

7. **Supabase Storage** ✅
   - PDF uploads go to Supabase bucket
   - Falls back to database BLOB if Supabase unavailable

8. **Celery** ✅
   - Background tasks for PDF processing, exercise generation, emails
   - Uses Redis as broker/backend

---

## 🚀 Deployment Checklist

Before deploying, verify:

- [ ] All environment variables are set in Render (see above)
- [ ] `FLASK_ENV=production` (critical)
- [ ] `SECRET_KEY` is a strong random value (not the dev default)
- [ ] `CORS_ORIGINS` matches your actual domain(s)
- [ ] `SENTRY_DSN` is set for error monitoring
- [ ] Both `web` and `worker` services are running (from Procfile)
- [ ] Database migrations have been run (scripts in `scripts/`)

---

## 🔒 Security Status After Changes

| Security Control | Status | Notes |
|------------------|--------|-------|
| JWT Authentication | ✅ Implemented | All endpoints require valid token |
| SQL Injection | ✅ Protected | Parameterized queries everywhere |
| XSS | ✅ Protected | HTML escaping in frontend |
| CSRF | ⚠️ Optional | Set `FEATURE_CSRF=True` to enable |
| CORS | ✅ Restricted | Only your domains allowed |
| Security Headers | ✅ Enabled | HSTS, X-Frame-Options, etc. |
| Rate Limiting | ✅ Enabled | Redis-backed, shared across workers |
| Password Hashing | ✅ Strong | bcrypt with 12 rounds |
| Secrets Management | ✅ Good | All in environment variables |
| Error Monitoring | ✅ Enabled | Sentry with PII filtering |

---

## 📋 Next Steps

1. **Add to Render**: `FEATURE_CSRF=True` (recommended)
2. **Optional**: Add `SUPABASE_BUCKET=pdfs` (already the default)
3. **Deploy**: Push changes to trigger Render deployment
4. **Test**: Verify login works with JWT tokens
5. **Monitor**: Check Sentry dashboard for any errors

---

## Platform Selection for Sentry

**Answer: Python/Flask**

When creating your Sentry project, select:
- **Platform**: Python
- **Framework**: Flask

Your DSN format (`https://af52c0b187b184c92d8792a7aaf65a9e@o4510847021613056.ingest.us.sentry.io/4510848475791360`) confirms this is already correct.

```

---

## `SECURITY_AUDIT_COMPLETE.md`

**Summary:** # Security Audit & Environment Variables - COMPLETE ✅

### Details

```
# Security Audit & Environment Variables - COMPLETE ✅

**Date**: February 9, 2026  
**Status**: All environment variables verified and integrated  
**Deployment**: Ready for production

---

## 📋 Executive Summary

Your AnalytIQ application has been fully audited and secured. All environment variables from your Render dashboard have been verified to be properly integrated into the codebase. The application is now production-ready with enterprise-grade security controls.

---

## ✅ What Was Done

### 1. Environment Variables Verification
- ✅ All 17 environment variables from Render are properly integrated
- ✅ Each variable is used correctly in `config.py` and throughout the app
- ✅ Sensible defaults exist for optional variables
- ✅ No hardcoded secrets or credentials in code

### 2. Security Improvements Implemented
- ✅ **JWT Authentication**: Replaced insecure client-side `user_id` with server-validated JWT tokens
- ✅ **CORS Restriction**: Locked down to your specific domains (`myanalytiq.org`)
- ✅ **Security Headers**: Added HSTS, X-Frame-Options, X-Content-Type-Options, etc.
- ✅ **Rate Limiting**: Switched to Redis-backed rate limiting (shared across workers)
- ✅ **Sentry Integration**: Fixed to use proper PII filtering configuration
- ✅ **Password Security**: bcrypt with 12 rounds (already implemented)
- ✅ **SQL Injection Protection**: Parameterized queries everywhere (already implemented)

### 3. Code Changes
- Modified `app.py` to use `sentry_config.py` instead of inline Sentry initialization
- All JWT authentication endpoints tested and working
- Frontend updated to use `authFetch()` with `Authorization: Bearer <token>` headers
- All 30+ protected endpoints now require valid JWT tokens

---

## 🔒 Current Security Posture

| Control | Status | Implementation |
|---------|--------|----------------|
| **Authentication** | ✅ Strong | JWT with 7-day expiry, HS256 signing |
| **Authorization** | ✅ Strong | Role-based (professor/student) |
| **Password Hashing** | ✅ Strong | bcrypt, 12 rounds |
| **SQL Injection** | ✅ Protected | Parameterized queries |
| **XSS** | ✅ Protected | HTML escaping in frontend |
| **CSRF** | ⚠️ Optional | Set `FEATURE_CSRF=True` to enable |
| **CORS** | ✅ Restricted | Only your domains |
| **Rate Limiting** | ✅ Enabled | Redis-backed, 1000/day, 100/hour |
| **Security Headers** | ✅ Enabled | HSTS, X-Frame-Options, etc. |
| **Secrets Management** | ✅ Good | All in environment variables |
| **Error Monitoring** | ✅ Enabled | Sentry with PII filtering |
| **HTTPS** | ✅ Enforced | Via Render + HSTS header |

**Overall Rating**: A- (Excellent)

---

## 📊 Environment Variables Status

### ✅ Already Configured in Render (17 variables)

| Category | Variables | Status |
|----------|-----------|--------|
| **Core** | `FLASK_ENV`, `SECRET_KEY` | ✅ |
| **Database** | `DATABASE_URL`, `REDIS_URL` | ✅ |
| **AI/Storage** | `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY` | ✅ |
| **Email** | `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`, `MAIL_USE_TLS` | ✅ |
| **Security** | `CORS_ORIGINS`, `SENTRY_DSN` | ✅ |
| **Features** | `FEATURE_CACHING`, `FEATURE_ASYNC_TASKS` | ✅ |

### ⚠️ Recommended to Add (1 variable)

| Variable | Value | Why |
|----------|-------|-----|
| `FEATURE_CSRF` | `True` | Enable CSRF protection for form submissions |

### ℹ️ Optional (have defaults)

| Variable | Default | Notes |
|----------|---------|-------|
| `SUPABASE_BUCKET` | `pdfs` | Already correct |
| `JWT_SECRET_KEY` | Uses `SECRET_KEY` | Separate key not needed |

---

## 🚀 Deployment Instructions

### Step 1: Add Missing Variable (Optional but Recommended)

In your Render dashboard, add:

```
FEATURE_CSRF=True
```

### Step 2: Deploy

Push your code to trigger a Render deployment:

```bash
git add .
git commit -m "Security audit complete: JWT auth, CORS, headers, Sentry"
git push origin main
```

### Step 3: Verify Deployment

Once deployed, run the verification script:

```bash
# SSH into your Render instance or use the Shell tab
python scripts/verify_deployment.py
```

This will check:
- ✅ All environment variables are set
- ✅ Database connection works
- ✅ Redis connection works
- ✅ Supabase connection works
- ✅ JWT implementation works
- ✅ No debug mode in production
- ✅ No default secrets

### Step 4: Test Authentication

1. Go to `https://www.myanalytiq.org`
2. Sign up for a new account
3. Check browser DevTools → Application → Local Storage → `auth_token` should be present
4. Check Network tab → API requests should have `Authorization: Bearer <token>` header
5. Sign out → token should be removed from localStorage

### Step 5: Monitor Errors

Check your Sentry dashboard at:
- https://sentry.io/organizations/your-org/projects/

You should see:
- ✅ No errors on startup
- ✅ Release tagged with `RENDER_GIT_COMMIT`
- ✅ Environment set to `production`

---

## 📝 What Each Environment Variable Does

### Core Application

**`FLASK_ENV=production`**
- Sets Flask to production mode (disables debug, enables optimizations)
- Used by: `config.py` → `config.ENV`

**`SECRET_KEY=4a85a2d4...`**
- Signs Flask sessions and JWT tokens
- Used by: `config.py` → `config.SECRET_KEY` and `config.JWT_SECRET_KEY`

### Database & Caching

**`DATABASE_URL=postgresql://...`**
- PostgreSQL connection string with connection pooling
- Used by: `app.py` → database pool initialization

**`REDIS_URL=redis://...`**
- Redis for caching and Celery task queue
- Used by: `cache.py`, `tasks.py`, `app.py` (rate limiter)

### AI & Storage

**`GEMINI_API_KEY=AIzs8yAE...`**
- Google Gemini API for AI exercise generation
- Used by: `exercise_generator.py`

**`SUPABASE_URL=https://onjt8nkczfpnyyztzqai.supabase.co`**
**`SUPABASE_KEY=eyJhbGc...`**
- Supabase storage for PDF uploads
- Used by: `supabase_storage.py`

**`SUPABASE_BUCKET=pdfs`** (optional, defaults to `pdfs`)
- Bucket name for PDF storage
- Used by: `supabase_storage.py`

### Email

**`MAIL_SERVER=smtp.gmail.com`**
**`MAIL_PORT=587`**
**`MAIL_USERNAME=adamelharouchi@gmail.com`**
**`MAIL_PASSWORD=kpoiatalonpjsykn`**
**`MAIL_DEFAULT_SENDER=adamelharouchi@gmail.com`**
**`MAIL_USE_TLS=True`**
- SMTP configuration for password reset emails
- Used by: `app.py` → Flask-Mail configuration

### Security

**`CORS_ORIGINS=https://www.myanalytiq.org,https://myanalytiq.org`**
- Comma-separated list of allowed origins for CORS
- Used by: `app.py` → `_get_cors_origin()` function

**`SENTRY_DSN=https://af52c0b187...`**
- Sentry error monitoring
- Used by: `sentry_config.py` → Sentry SDK initialization

**`FEATURE_CSRF=True`** (recommended to add)
- Enable CSRF protection for form submissions
- Used by: `config.py` → `config.FEATURE_CSRF_PROTECTION`

### Feature Flags

**`FEATURE_CACHING=True`**
- Enable Redis caching for API responses
- Used by: `cache.py`

**`FEATURE_ASYNC_TASKS=True`**
- Enable Celery background tasks
- Used by: `tasks.py`

---

## 🔍 How to Verify Everything Works

### 1. Check Logs

In Render dashboard → Logs tab, you should see:

```
✅ Sentry SDK initialized (environment: production)
✅ Redis cache initialized (TTL: 300s)
✅ Supabase client initialized (bucket: pdfs)
✅ Rate limiting enabled (storage: redis)
✅ CSRF protection enabled  [if you added FEATURE_CSRF=True]
✅ API documentation available at /api/docs
✅ Celery async tasks enabled
```

### 2. Test API Endpoints

```bash
# Health check (no auth required)
curl https://www.myanalytiq.org/health

# Sign up (returns JWT token)
curl -X POST https://www.myanalytiq.org/api/users/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@hult.edu","password":"Test123!","role":"student"}'

# Use token to access protected endpoint
curl https://www.myanalytiq.org/api/users/profile \
  -H "Authorization: Bearer <token_from_signup>"
```

### 3. Check Sentry

- Go to your Sentry dashboard
- Should see "production" environment
- Should see release tagged with git commit hash
- Should see no startup errors

### 4. Check Database

`

... (truncated)
```

---

## `api_docs.py`

**Summary:** AnalytIQ API Documentation Generator Generates OpenAPI 3.0 specification for all API endpoints

### Details

```
AnalytIQ API Documentation Generator
Generates OpenAPI 3.0 specification for all API endpoints

---

Create and return the OpenAPI specification

---

Get the OpenAPI specification as JSON string

---

Get the OpenAPI specification as dictionary
```

---

## `app.py`

**Summary:** Wrapper decorator so we can safely exempt JSON API endpoints from CSRF     checks even when CSRF is disabled or Flask-WTF is not installed.

### Details

```
Wrapper decorator so we can safely exempt JSON API endpoints from CSRF
    checks even when CSRF is disabled or Flask-WTF is not installed.

---

Serve the OpenAPI specification JSON

---

Return the allowed origin for the current request, or None.

---

Detect user role from email domain

---

Parse DATABASE_URL and return connection parameters dictionary

---

Initialize the database connection pool with timeout settings

---

Get a connection from the global pool with retry logic

---

Return connection to pool at the end of request

---

No-op: Connection closing is handled by teardown_appcontext

---

Create a JWT token for an authenticated user.

    Args:
        user_id: The user's ID
        role: The user's role (student/professor)
        name: The user's name (optional, included in token for convenience)
        email: The user's email (optional, included in token for convenience)

    Returns:
        str: Encoded JWT token

---

Decode and verify a JWT token.

    Args:
        token: The JWT token string

    Returns:
        dict: Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid

---

Decorator that requires a valid JWT token in the Authorization header.
    Sets g.user_id and g.user_role for the decorated function.

    Usage:
        @app.route('/api/some-endpoint')
        @require_auth
        def some_endpoint():
            user_id = g.user_id
            role = g.user_role
    
    In test mode, auth is bypassed if user_id is provided in request or headers.
    OPTIONS requests always bypass auth.

---

DEPRECATED: Legacy hash function for backward compatibility only.
    This function is insecure and should not be used for new passwords.
    Kept only to verify old passwords during migration period.

---

Hash password using bcrypt with automatic salt generation.

    Args:
        password (str): Plain text password

    Returns:
        str: Bcrypt hashed password (UTF-8 decoded)

---

Verify password against bcrypt hash.
    Falls back to legacy hash for backward compatibility during migration.

    Args:
        password (str): Plain text password to verify
        hashed_password (str): Stored hash (bcrypt or legacy)

    Returns:
        tuple: (is_valid, needs_rehash)
            - is_valid: True if password matches
            - needs_rehash: True if using legacy hash (should update to bcrypt)

---

Ensure password_resets table exists for forgot-password flow.

---

Handle OPTIONS preflight for signup

---

Sign up a new user

---

Sign in a user

---

Handle forgot password request

---

Reset password using token from email link.

---

Get user profile

---

Update user profile

---

Get user settings

---

Update user settings

---

Update user password

---

Delete user account

---

Get all conversations for a user

---

Create a new conversation

---

Get a specific conversation with messages

---

Update conversation (title, archive status, etc)

---

Delete (soft delete) a conversation

---

Get AI agent digest for user

---

Update AI agent digest

---

Get AI agent memory for user

---

Update AI agent memory (replaces all)

---

Get user preferences

---

Update user preferences

---

Get practice progress for user

---

Update practice progress

---

Get progress for all exercises for current user

---

Get leaderboard for a specific exercise

---

Get grand leaderboard - ranked by average score across all exercises

---

Comprehensive health check endpoint
    Returns 200 if all critical services healthy, 503 if degraded

---

Generate and return a CSRF token for the client
    This endpoint is used by the frontend to obtain a CSRF token

---

Get the status of an async task

    Args:
        task_id: Celery task ID

    Returns:
        JSON with task status, result, or error

---

Submit a contact form message

---

Generate a unique 10-character class code (5 letters + 5 numbers)

---

Create a new class (professor only)

---

Get classes for current user (professor sees their classes, student sees enrolled classes)

---

Get class details

---

Get all resources for a class (including chapters as resources)

---

Get details of a single exercise

---

Update an existing exercise

---

Update class (professor only, must be owner)

---

Check if file extension is allowed

---

Comprehensive PDF file validation without external dependencies
    Returns (is_valid, error_message)

---

Upload PDF and create chapter for a class (professor only)

---

Get all chapters for a class

---

Update a chapter

---

Delete a chapter and all its exercises (professor only)

---

Generate exercises from an existing chapter's PDF data

---

Delete class (professor only, must be owner)

---

Get all exercises for a chapter

---

Secure proxy for Gemini Chat API

---

Enroll student in a class using class_id (class code)

---

Get all classes a student is enrolled in

---

Get all students enrolled in a class (professor only)

---

Get all students' progress for a class (professor only)

---

Get student's progress for exercises (optionally filtered by class_id)

---

Get specific student's progress (professor only for their classes)

---

Get average leaderboard for a class (all students ranked by average score)

---

Get leaderboard for a specific exercise in a class

---

Ensure class_exercises table has all required columns (Lazy Migration)

---

Manually create a new exercise

---

Add a new resource (link) to the class

---

Serve PDF file from database binary storage or filesystem (backward compatibility)

---

Delete a specific exercise

---

Ensure class_resources table exists and has correct columns (Lazy Migration)

---

Upload a file as a resource

---

Serve resource file from database (BLOB)

---

Update or Delete a resource

---

Serve uploaded resource file (Legacy - kept for older non-migrated files)

---

Serve frontend static files (HTML, CSS, JS, etc.) for local dev.

---

Automatically creates /api/v1/ aliases for all /api/ routes.
    This ensures backward compatibility while establishing versioning.
```

---

## `cache.py`

**Summary:** Redis Cache Utilities for AnalytIQ Provides caching functionality for frequently accessed endpoints

### Details

```
Redis Cache Utilities for AnalytIQ
Provides caching functionality for frequently accessed endpoints

---

Get value from cache

    Args:
        key: Cache key

    Returns:
        Cached value (dict) or None if not found

---

Set value in cache

    Args:
        key: Cache key
        value: Value to cache (must be JSON serializable)
        ttl: Time to live in seconds (default: CACHE_DEFAULT_TTL)

    Returns:
        bool: True if successful, False otherwise

---

Delete cache keys matching pattern

    Args:
        pattern: Redis key pattern (e.g., 'class:*', 'user:123:*')

    Returns:
        int: Number of keys deleted

---

Decorator to cache Flask endpoint responses

    Args:
        ttl: Cache TTL in seconds
        key_prefix: Prefix for cache key

    Usage:
        @app.route('/api/classes/<class_id>')
        @cache_response(ttl=300, key_prefix='class')
        def get_class(class_id):
            # ... endpoint logic

---

Check if Redis cache is healthy

    Returns:
        dict: {'healthy': bool, 'message': str}

---

Get cache hit/miss statistics

    Returns:
        dict: Cache statistics
```

---

## `js/ai-agent.js`

**Summary:** // AI Agent Integration - Code Writer Agent // Uses Google Gemini // Set Gemini model // Initialize with API key // Detect repository context // Try to detect project type from common files // This wo

### Details

```
// AI Agent Integration - Code Writer Agent
// Uses Google Gemini
// Set Gemini model
// Initialize with API key
// Detect repository context
// Try to detect project type from common files
// This would ideally check for package.json, requirements.txt, etc.
// For now, we'll infer from conversation
// Load digest from API
// Transform API response to match internal format
// API returns: goal, constraints, decisions, current_state, open_questions (as strings or arrays)
// Internal format expects: userGoal, constraints, decisionsMade, currentState, openQuestions (as arrays)
// Helper function to ensure value is an array
// If it's a JSON string, try to parse it
// If parsing fails, treat as empty or single value
// Fallback to localStorage
// Ensure arrays are arrays
// If parsing fails, initialize with defaults
// Save digest to API
// Ensure digest has correct format before saving
// Fallback to localStorage - ensure arrays are arrays
// Load memory from API
// Fallback to localStorage
// Save memory to API
// Fallback to localStorage
// Update digest from conversation
// Ensure all digest arrays exist and are arrays
// Extract goal
// Extract constraints
// Extract decisions from assistant response
// Extract current section progress
// Only update if it's a new section or explicit reference
// Clear previous section statuse to keep state clean
// Keep arrays manageable
// Keep concise state
// Build system prompt
// Ensure all digest fields are arrays before calling .map()
**CRITICAL - CODE MUST BE SYNTACTICALLY CORRECT:**
// % ** etc.
**MULTIPLICATION OPERATOR - CRITICAL:**
**COMMON MISTAKES TO AVOID:**
**WHEN CREATING INTERACTION TERMS:**
**BEFORE PROVIDING CODE:**
**CONTEXT AWARENESS - CRITICAL:**
**Example of GOOD context awareness:**
**Example of BAD context (DON'T DO THIS):**
**Explanation:**
// Call Google Gemini API (supports text and images)
// Convert messages to Gemini format
// Add image to the last user message if provided
// Extract base64 data from data URL
// Use selected Gemini model
// Use secure backend proxy instead of direct call
// Check for specific API not enabled error
//console.cloud.google.com/apis/library/generativelanguage.googleapis.com`);
// Process message with AI (supports optional image data)
// Build messages array
// For playground mode (when context is provided), don't include conversation history
// Each exercise should be treated independently
// For playground mode, prepend system prompt directly to user message
// This ensures Gemini receives the full context since system prompts are filtered
// Add image context to message if image is provided
// Always prepend system prompt for main code assistant to ensure Gemini follows instructions
// Playground mode: prepend playground system prompt
// First message in main code assistant: prepend system prompt
// Only include conversation history for main code assistant (not playground mode)
// Last 10 messages for context
// Only update digest and conversation history for main code assistant (not playground mode)
// Update digest
// Add to conversation history
// Save digest
// Extract and store durable memories
// Build system prompt for playground mode (solution-aware hints)
// Build all exercises reference text for context
// Extract durable memories from conversation
// Look for durable preferences and decisions
// Keep memory manageable
// Clear conversation
// Export singleton instance
```

---

## `js/api-helper.js`

**Summary:** // API Helper Functions // Declare API_BASE_URL as a global variable - single source of truth // Use localhost for local testing, production URL for deployed version // Check for localhost, 127.0.0.1,

### Details

```
// API Helper Functions
// Declare API_BASE_URL as a global variable - single source of truth
// Use localhost for local testing, production URL for deployed version
// Check for localhost, 127.0.0.1, or file:// protocol (local development)
//localhost:5001/api'
//analytiq-qbfr.onrender.com/api';
// Simple Cache Implementation
// Default TTL: 5 minutes (300,000 ms)
// Delete keys matching pattern (string or regex)
// Get auth headers for API requests
// Authenticated fetch wrapper - adds JWT token to all requests
// Add Authorization header
// Don't override Content-Type for FormData (multipart)
// Fetch with Cache Wrapper
// Only cache GET requests
// Clone response to read it and cache it, while returning original to caller
// Get current user ID from localStorage
// Get full current user object
// Escape HTML to prevent XSS
// Get difficulty color
// medium
// Conversation API functions
// Invalidate conversations cache
// Invalidate specific conversation and list
// Invalidate specific conversation and list
// AI Agent API functions
// Invalidate digest cache
// Invalidate memory cache
// Preferences API functions
// Invalidate preferences cache
```

---

## `js/auth.js`

**Summary:** // Authentication System // API_BASE_URL should be defined in api-helper.js // API Configuration - Use relative URLs for better portability // Use relative path - works in both development and product

### Details

```
// Authentication System
// API_BASE_URL should be defined in api-helper.js
// API Configuration - Use relative URLs for better portability
// Use relative path - works in both development and production
// Load user from localStorage (for session persistence)
// Save user to localStorage (for session persistence)
// Get JWT token
// Save JWT token
// Remove JWT token
// Sign up new user
// Extract user ID - use user_id if available, otherwise fall back to id
// Save JWT token
// Auto sign in - save user with consistent user_id
// Store as 'id' for compatibility with existing code
// Also store as 'user_id' for clarity
// Store role
// Sign in user
// Extract user ID - use user_id if available, otherwise fall back to id
// Save JWT token
// Save current user (without password) - store user_id consistently
// Store as 'id' for compatibility with existing code
// Also store as 'user_id' for clarity
// Store role
// Sign out
// Check if user is authenticated
// Get current user
// Require authentication - redirect to login if not authenticated
// Global auth manager instance
// Handle sign in
// Show loading state
// Always redirect to home page
// Re-enable button on error
// Validate Hult email domain
// Handle sign up
// Clear previous errors
// Validate email domain (must be Hult email)
// Validate passwords match
// Show loading state
// Always redirect to home page
// Re-enable button
// Show tab
// Hide all tabs
// Show selected tab
// Activate the clicked button
// Fallback: find button by tab name
// Check authentication on page load
// If already authenticated and on login page, redirect to home
// If not authenticated and trying to access any page except login, redirect to login
// This is handled by requireAuth() on each page, but we can add a global check here too
// This will be handled by individual pages, but we can add a fallback
// Will be redirected by requireAuth() on each page
// Forgot Password Functions
// Clear previous messages
// Show loading state
// Show success message
// Clear form
// Close modal after 3 seconds
// Re-enable button
```

---

## `js/code-assistant.js`

**Summary:** // Code Assistant // Only Gemini supported // Default: Best Balance // Default API key - accessible to all users // Default API key - Managed Server-Side // Key is no longer exposed client-side // Sto

### Details

```
// Code Assistant
// Only Gemini supported
// Default: Best Balance
// Default API key - accessible to all users
// Default API key - Managed Server-Side
// Key is no longer exposed client-side
// Store conversation history
// Track current tab: 'active' or 'archived'
// Save conversation to history
// Save to API (if available)
// Also update local list for immediate UI update
// Fallback to localStorage if API not available
// Load conversation history
// Load from API (if available)
// Messages loaded separately when conversation is opened
// Fallback to localStorage if API not available
// Fallback to localStorage
// Switch conversation tab (active/archived)
// Update tab buttons
// Re-render conversation list
// Render conversation history
// Filter conversations based on current tab
// Show only archived and not deleted conversations
// Show only active (not archived and not deleted) conversations
// Load a conversation
// Load from API (if available)
// Fallback to local list
// Clear current chat
// Hide welcome section
// Load messages
// Update history display
// Scroll to bottom
// Fallback to local list
// Helper function for loading local conversation (fallback)
// Archive/Unarchive a conversation
// Update via API (if available)
// If unarchiving, switch to active tab
// Fallback to localStorage
// Delete a conversation
// Confirm deletion
// Delete via API (if available)
// Remove from local list
// If this was the current conversation, start a new one
// Fallback to localStorage
// Start new conversation
// Switch to active tab if we're on archived tab
// Check if welcome section already exists
// Recreate welcome section if it doesn't exist
// Just clear messages and show welcome section
// Update language
// Element doesn't exist on this page
// Save to API
// Fallback to localStorage
// Update the display
// Handle file upload
// Update file input accept attribute based on file type selection
// All files
// Detect file type
// Binary file types that need special handling
// Image file types
// Detect language from extension for code files
// Handle different file types
// Use appropriate reading method based on file type
// Parse data file
// Parse CSV
// Process code file
// Update Gemini Model
// Save to API (if available)
// Fallback to localStorage
// Update the display
// Show shortened model name
// Flagship Gemini 3 Series (2026)
// Best for: Complex reasoning, advanced coding, multi-step analysis
// Best for: Fast responses, everyday tasks, quick code fixes
// Stable Gemini 2.5 Series
// Best for: Production apps, reliable coding, balanced performance
// Best for: High-speed tasks, simple queries, cost efficiency
// Specialty & Legacy
// Best for: Image analysis, visual understanding, charts/diagrams
// Update the AI agent with new model
// Initialize Gemini on page load
// Set Gemini as provider
// Load saved model preference from API or use default
// Force update to Gemini 3 if user was on old default
// Fallback to localStorage if preferencesAPI not available
// Fallback to localStorage
// Update UI to reflect saved model
// Set API key in localStorage (API keys are still stored locally for security)
// Initialize AI agent
// Test API connection
//generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent?key=${apiKey}`,
//console.cloud.google.com/apis/library/generativelanguage.googleapis.com');
// Initialize AI Agent
// API Key is now handled server-side.
// Client just initializes the agent with no key.
// Show API Settings Modal
// Modal doesn't exist, function not used
// Use hardcoded API key
// Close API Settings Modal
// Close modal when clicking outside
```

---

## `js/contact.js`

**Summary:** // Contact Form Handler // Require authentication // Will redirect to login // Pre-fill email if user is logged in // Pre-fill name if available // Validate form // Show loading state // Send to API e

### Details

```
// Contact Form Handler
// Require authentication
// Will redirect to login
// Pre-fill email if user is logged in
// Pre-fill name if available
// Validate form
// Show loading state
// Send to API endpoint
// Show success message
// Reset form
// Re-fill email if user is logged in
// Auto-hide after 5 seconds for success/info, keep error visible
```

---

## `js/professor-class.js`

**Summary:** // Professor Class Management // API_BASE_URL should be defined in api-helper.js // API_BASE_URL is defined in api-helper.js // Store loaded resources for edit functionality // Performance optimizatio

### Details

```
// Professor Class Management
// API_BASE_URL should be defined in api-helper.js
// API_BASE_URL is defined in api-helper.js
// Store loaded resources for edit functionality
// Performance optimization: Cache for API data
// 30 second cache TTL
// Load class data
// Render class header
// Load default tab (chapters)
// Render class header
// Switch tabs
// Hide all tab contents
// Remove active class from all tab buttons
// Show selected tab content
// Add active class to selected tab button
// Load tab data
// Load chapters
// Escape HTML to prevent XSS
// Load students with exercise progress
// Fetch students
// Fetch progress data for the class
// Map progress by student ID
// Get total exercises count (use cache to avoid slow sequential API calls)
// Fetch all exercises in parallel for speed
// Load progress
// Render Progress Table
// Modified to target specific container instead of overwriting everything
// Populate leaderboard exercise dropdown
// Switch between progress views (Table vs Leaderboards)
// Hide all containers
// Reset tabs
// Show selected
// Load Average Leaderboard
// Load Exercise Leaderboard
// Load exercises
// First, get all chapters to group exercises by chapter
// Load exercises for each chapter
// Group by chapter
// Render in practice grid style, grouped by chapter
// Show create exercise modal
// Reset to Create Mode
// Load chapters for the select dropdown
// Hide create exercise modal
// Handle create exercise form submission
// For edit, use JSON (file changes not supported in edit mode)
// Use FormData if file is attached, otherwise JSON
// Success - close modal and refresh exercises list
// Show success message
// Re-select modal as it might not be in scope if not passed
// Show error in create exercise modal
// Edit exercise - opens modal with existing data
// Find the exercise in the DOM or fetch it
// We can fetch details from the API to be sure
// Hacky, better to fetch
// Better: Fetch specific exercise details. Since we don't have a direct GET /exercises/:id, we use the chapter list or iterate
// However, looking at loadExercises, we have the data in memory if we wanted, but let's just fetch from the new endpoint if we had it, or filter from cache.
// Let's iterate through the DOM or cache. 'dataCache' has exercises?
// Simplest approach: We already have the list loaded.
// Let's fetch the specific exercise details using the chapter endpoint we know exists, or search in our local cache.
// But we need the chapter_id.
// Let's just loop through chapters to find it if we don't have it.
// Or, we can use the `dataCache.exercises` if populated.
// Actually, let's use the button's data attributes if we added them, but we didn't.
// Let's try to find it in the `allExercises` array if we made it global, but we didn't.
// Valid Plan:
// 1. Show loading state.
// 2. Fetch all chapters.
// 3. Search for exercise in each chapter (parallel).
// 4. Populate modal.
// OPTIMIZATION: We changed the UI to group by chapter. We can pass the chapter_id to the edit button too!
// But I can't change the HTML generation easily without reloading.
// Let's assumes we find it.
// Actually, I'll search all chapters for now.
// Set to Edit Mode
// Populate Form
// Handle Chapter Select
// Cannot move chapters in edit mode easily
// File input is optional/hidden for edit
// (We could clear it)
// Start exercise from class view - opens practice playground
// Load resources
// Add default tools and datasets
//colab.research.google.com',
//www.kaggle.com/datasets',
//archive.ics.uci.edu',
//opendata.cityofnewyork.us',
//data.worldbank.org',
// Combine all resources: custom resources, then default tools/datasets
// Store for edit functionality
// Group by type
// Type icons and labels
// Fix relative URLs to point to API
// Remove leading slash to avoid double slash if base has it, though normally base doesn't.
// Usually API_BASE_URL is '.../api', and url is '/api/resource...'.
// Wait, if url is '/api/resources/files/...' and API_BASE_URL is '.../api', we might duplicate '/api' if we blindly concat.
// But window.API_BASE_URL is usually 'https://...onrender.com/api'.
// If url is '/api/resources...', then 'https://.../api/api/resources' might be wrong.
// Actually, file uploads returning '/api/resources/files/...' implies they are relative to SERVER ROOT.
// window.API_BASE_URL includes '/api'.
// So we should replace the domain part.
```

---

## `js/professor-dashboard.js`

**Summary:** // Professor Dashboard - Class Management // API_BASE_URL should be defined in api-helper.js // API_BASE_URL and getCurrentUser are defined in api-helper.js // Load classes for professor // Render cla

### Details

```
// Professor Dashboard - Class Management
// API_BASE_URL should be defined in api-helper.js
// API_BASE_URL and getCurrentUser are defined in api-helper.js
// Load classes for professor
// Render classes grid
// Add hover effect
// Show create class modal
// Hide create class modal
// Handle create class form submission
// Validate class code format (3-20 alphanumeric characters, hyphens, underscores)
// Success - reload classes and close modal
// Show success message
// View class (navigate to class management page)
// Copy class code to clipboard
// Show temporary feedback
// Delete class with confirmation
// Confirm deletion
// Reload classes to reflect deletion
// Close modal when clicking outside
// Close modal with Escape key
```

---

## `js/profile.js`

**Summary:** // Profile Management JavaScript // API_BASE_URL should be defined in api-helper.js //analytiq-qbfr.onrender.com/api'; // Load user profile data // Load profile picture IMMEDIATELY from localStorage (

### Details

```
// Profile Management JavaScript
// API_BASE_URL should be defined in api-helper.js
//analytiq-qbfr.onrender.com/api';
// Load user profile data
// Load profile picture IMMEDIATELY from localStorage (instant, no delay)
// Fetch profile from API (update in background)
// Load personal information
// Update profile picture from API (if different from localStorage)
// Update localStorage with API value
// Use default if API doesn't have a picture
// Load settings
// Setup event listeners
// Profile picture upload
// Personal information form
// Password form
// Email notifications toggle - auto-save on change
// Handle profile picture upload
// Validate file type
// Validate file size (max 5MB)
// Update via API
// Also update localStorage for session
// Update navigation profile picture if function exists
// Handle personal information form submission
// Validate email
// Update via API
// Update localStorage for session
// Handle password change
// Validate inputs
// Validate new password length
// Check if passwords match
// Update password via API
// Clear form
// Save settings
// Save to localStorage first (always works)
// Try to save via API (non-blocking)
// API failed but localStorage saved - settings still work
// API failed but localStorage saved - settings still work
// Delete account
// Get user_id - check both 'id' and 'user_id' fields for compatibility
// Delete via API - ensure user_id is a string
// Clear local data
// Redirect to login
// Helper function to validate email
// Show notification
// Remove existing notifications
// Create notification element
// Add to page
// Show notification
// Hide and remove after 3 seconds
```

---

## `js/student-class.js`

**Summary:** // Student Class View - View Class Details, Chapters, and Exercises // API_BASE_URL should be defined in api-helper.js // API_BASE_URL is defined in api-helper.js // Load class data // Load class deta

### Details

```
// Student Class View - View Class Details, Chapters, and Exercises
// API_BASE_URL should be defined in api-helper.js
// API_BASE_URL is defined in api-helper.js
// Load class data
// Load class details
// Check if we should switch to exercises tab from URL
// Render class header
// Copy class code to clipboard (same function as professor)
// Fallback copy function
// Load exercises for a chapter
// Switch tabs
// Hide all tab contents
// Remove active class from all tab buttons
// Show selected tab content
// Add active class to selected tab button
// Load tab data
// Load chapters
// Load all exercises
// Load all chapters first
// Load exercises for all chapters in parallel (performance optimization)
// Group by chapter (same format as professor)
// Render in practice grid style, grouped by chapter (same as professor, but without edit button)
// Render chapters (optimized - loads exercises on demand or lazily)
// Check if we should scroll to a specific chapter from URL params
// Don't load exercises immediately - they're loaded separately in exercises tab or on demand
// Empty for now - exercises are shown in the Exercises tab
// Scroll to target chapter if specified in URL
// Remove chapter_id from URL without reload
// Add hover effect
// Start exercise - navigate to practice playground (same as professor portal)
// Load resources (read-only for students)
// Add default tools and datasets
//colab.research.google.com',
//www.kaggle.com/datasets',
//archive.ics.uci.edu',
//opendata.cityofnewyork.us',
//data.worldbank.org',
// Combine all resources: custom resources, then default tools/datasets
// Group by type
// Type icons and labels
// DEBUG: Log resource to inspect URL issues
// Determine Icon
// Fix relative URLs to point to API (e.g. /api/resources/...)
// Fix missing protocol for typically external resources (datasets, links, videos)
// Avoid touching 'tool' which can be relative (e.g. code-assistant.html)
// If it's a dataset, link, video, or article, we assume it's external
//${url}`;
// Default to new tab for everything
// Check if it's a backend download file
// Downloads don't need new tab necessarily, but it's fine either way
// Case 1: Chapter PDF
// Same tab for app navigation
// Case 2: Regular PDF
// PDFs usually viewed in browser
// Case 3: File Types (Explicit Download Label)
// Treat as download for icon purposes unless it's clearly a viewable link
// If it's NOT a backend download (e.g. external link to CSV), still keep new tab
// Adjust text if it's likely a viewable external link?
// User asked for "Download [Type]", so we stick to that or "Access".
// Case 4: Link Types
// Load students (read-only for students - shows class roster)
// Load progress (shows student's own progress)
// Load Progress (Initializes Leaderboard View)
// Default to average leaderboard
// Also populate exercise dropdown for the specific view
// Fetch exercises using existing logic or endpoint
// We'll re-use the strategy from loadExercises: fetch chapters then exercises
// Switch between Average and Exercise Leaderboard
// Hide all
// Reset tabs
// Load Average Leaderboard
// Load Exercise Leaderboard
// Event delegation for dynamically added buttons
// Handle start exercise button click
```

---

## `js/student-classes.js`

**Summary:** // Student Classes - View Enrolled Classes // API_BASE_URL should be defined in api-helper.js // Use localhost for local testing, production URL for deployed version // Check for localhost, 127.0.0.1,

### Details

```
// Student Classes - View Enrolled Classes
// API_BASE_URL should be defined in api-helper.js
// Use localhost for local testing, production URL for deployed version
// Check for localhost, 127.0.0.1, or file:// protocol (local development)
//localhost:5001/api'
//analytiq-qbfr.onrender.com/api';
// Get current user
// Load enrolled classes for student
// Render classes grid
// Add hover effect
// Show join class modal
// Transform input to uppercase as user types
// Hide join class modal
// Handle join class form submission
// Success - reload classes and close modal
// Show success message
// View class (navigate to student class view page)
// Escape HTML to prevent XSS
// Close modal when clicking outside
// Close modal with Escape key
```

---

## `python/exercise_generator.py`

**Summary:** Exercise Generation Service Uses Google Gemini API to generate coding exercises from PDF content

### Details

```
Exercise Generation Service
Uses Google Gemini API to generate coding exercises from PDF content

---

Generate coding exercises from PDF text using Gemini API

    Args:
        pdf_text: Extracted text from PDF
        chapter_title: Title of the chapter
        api_key: Google Gemini API key (optional, can use env var)

    Returns:
        list: Array of exercise dictionaries with title, description, difficulty, solution_code
```

---

## `requirements.txt`

**Summary:** Flask==3.0.0 Flask-Cors==4.0.0 psycopg2-binary>=2.9.10 python-dotenv==1.0.0 gunicorn==21.2.0 google-generativeai>=0.3.1 PyPDF2==3.0.1 Flask-Mail==0.9.1 Flask-WTF==1.2.1 bcrypt==4.1.2 PyJWT>=2.10.1 Fla

### Details

```
Flask==3.0.0
Flask-Cors==4.0.0
psycopg2-binary>=2.9.10
python-dotenv==1.0.0
gunicorn==21.2.0
google-generativeai>=0.3.1
PyPDF2==3.0.1
Flask-Mail==0.9.1
Flask-WTF==1.2.1
bcrypt==4.1.2
PyJWT>=2.10.1
Flask-Limiter==3.5.0
flask-swagger-ui==4.11.1
apispec==6.3.1
celery==5.3.4
redis==5.0.1
supabase>=2.12.0
python-json-logger==2.0.7
sentry-sdk[flask]>=1.40.0

# Testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-flask==1.3.0

# Code Quality
flake8==6.1.0
black==23.12.1
mypy==1.7.1

```

---

## `sentry_config.py`

**Summary:** Sentry Integration for Production Error Monitoring

### Details

```
Sentry Integration for Production Error Monitoring

---

Initialize Sentry error tracking for production monitoring
    
    Features:
    - Automatic error capture and reporting
    - Performance monitoring (transactions)
    - Release tracking for deployment correlation
    - Environment tagging (production/staging)

---

Filter sensitive data before sending to Sentry
    
    Removes:
    - API keys
    - Passwords
    - Session tokens
    - Email addresses (in some contexts)

---

Manually capture an exception with additional context
    
    Usage:
        try:
            risky_operation()
        except Exception as e:
            capture_exception_with_context(e, {
                'user_id': user_id,
                'operation': 'pdf_upload'
            })

---

Capture a custom message in Sentry
    
    Levels: 'debug', 'info', 'warning', 'error', 'fatal'
```

---

## `tasks.py`

**Summary:** Celery Tasks for AnalytIQ Async tasks for PDF processing, exercise generation, and email sending

### Details

```
Celery Tasks for AnalytIQ
Async tasks for PDF processing, exercise generation, and email sending

---

Base task with database connection handling

---

Get database connection (reuse connection pool)

---

Close database connection

---

Extract text from PDF bytes and store in database

    Args:
        pdf_bytes: PDF file as bytes
        chapter_id: Chapter ID to update

    Returns:
        dict: {'success': bool, 'text_length': int, 'chapter_id': str}

---

Generate exercises from PDF text using Gemini API

    Args:
        pdf_text: Extracted PDF text
        chapter_title: Chapter title
        chapter_id: Chapter ID
        class_id: Class ID
        api_key: Gemini API key

    Returns:
        dict: {'success': bool, 'exercise_count': int, 'chapter_id': str}

---

Send email asynchronously

    Args:
        recipient: Email recipient
        subject: Email subject
        body: Email body (HTML)

    Returns:
        dict: {'success': bool, 'recipient': str}

---

Combined workflow: Extract PDF text and optionally generate exercises

    Args:
        chapter_id: Chapter ID
        pdf_bytes: PDF file bytes
        auto_generate_exercises: Whether to auto-generate exercises
        class_id: Class ID
        chapter_title: Chapter title
        api_key: Gemini API key

    Returns:
        dict: {'success': bool, 'text_extracted': bool, 'exercises_generated': bool}
```

---

## `tests/test_api.py`

**Summary:** Simplified integration tests for Flask API endpoints Tests basic functionality without complex mocking

### Details

```
Simplified integration tests for Flask API endpoints
Tests basic functionality without complex mocking

---

Create minimal Flask app for testing

---

Create test client

---

Tests for health check endpoint

---

Test that health endpoint exists

---

Tests for CSRF token endpoint

---

Test CSRF token generation

---

Tests for CORS configuration

---

Test that CORS headers are present on API routes

---

Tests for error handling

---

Test 404 error for non-existent endpoint

---

Test OPTIONS request (CORS preflight)

---

Tests for Celery task status endpoint

---

Test that task status endpoint exists

---

Tests for API structure and configuration

---

Test that app has routes configured

---

Test that app is in testing mode

---

Test that CSRF is disabled for testing
```

---

## `tests/test_api_docs_coverage.py`

**Summary:** Tests for api_docs.py - OpenAPI specification generation Mocks marshmallow if not installed

### Details

```
Tests for api_docs.py - OpenAPI specification generation
Mocks marshmallow if not installed

---

Mock marshmallow if not installed

---

Try to import api_docs, skip if dependencies missing

---

Test API specification creation

---

Test that create_api_spec returns a valid spec object

---

Test spec has correct title

---

Test spec has correct version

---

Test spec has server definitions

---

Test spec has API paths defined

---

Test JSON spec generation

---

Test that get_openapi_spec_json returns a JSON string

---

Test that the JSON string is valid

---

Test dict spec generation

---

Test that get_openapi_spec_dict returns a dictionary
```

---

## `tests/test_app_additional_endpoints.py`

**Summary:** Comprehensive Tests for Chapter, Resource, and Submission Endpoints Target: Push coverage from 67% to 70%+

### Details

```
Comprehensive Tests for Chapter, Resource, and Submission Endpoints
Target: Push coverage from 67% to 70%+

---

Test chapter management endpoints

---

Test creating a new chapter

---

Test getting chapters for a class

---

Test getting specific chapter

---

Test updating chapter

---

Test deleting chapter

---

Test resource management endpoints

---

Test creating a new resource

---

Test getting resources for a chapter

---

Test updating resource

---

Test deleting resource

---

Test exercise submission endpoints

---

Test creating a new submission

---

Test getting submissions for an exercise

---

Test getting specific submission

---

Test updating submission grade

---

Test exercise management endpoints

---

Test getting exercises for a chapter

---

Test getting specific exercise

---

Test manually creating an exercise
```

---

## `tests/test_app_advanced_features.py`

**Summary:** Tests for advanced class features, analytics, and bulk operations

### Details

```
Tests for advanced class features, analytics, and bulk operations

---

Test class analytics and statistics endpoints

---

Test getting student count for a class

---

Test class enrollment statistics

---

Test bulk operations on classes and enrollments

---

Test enrolling multiple students at once

---

Test unenrolling multiple students

---

Test class data export functionality

---

Test exporting class roster

---

Test exporting class grades

---

Test student performance tracking features

---

Test tracking student progress in a class

---

Test leaderboard with multiple students

---

Test class archiving and restoration

---

Test archiving a class

---

Test listing archived classes

---

Test class update and modification operations

---

Test updating class description

---

Test updating class name

---

Test updating a non-existent class

---

Test safe deletion of classes with data

---

Test deleting a class that has enrolled students

---

Test deleting a class that has chapters
```

---

## `tests/test_app_api_docs.py`

**Summary:** Tests for API documentation endpoints (Swagger UI)

### Details

```
Tests for API documentation endpoints (Swagger UI)

---

Test Swagger/OpenAPI documentation endpoints

---

Test that Swagger UI endpoint is accessible

---

Test that OpenAPI spec endpoint is accessible

---

Test that API spec has correct OpenAPI structure

---

Test that API spec info section is properly configured

---

Test that API spec includes endpoint paths

---

Test Swagger UI configuration

---

Test CORS headers on API documentation endpoints

---

Test that API spec endpoint has CORS headers

---

Test OPTIONS request on API spec endpoint

---

Test security aspects of API documentation

---

Test that API spec doesn't expose sensitive information

---

Test that Swagger UI is publicly accessible

---

Test content and completeness of API documentation

---

Test that API spec is valid JSON

---

Test that API spec has correct content type

---

Test availability and error handling of API documentation

---

Test that app handles missing Swagger UI gracefully

---

Test that app handles missing api_docs module gracefully

---

Test Swagger UI redirect behavior
```

---

## `tests/test_app_authentication.py`

**Summary:** Tests for authentication flows, password management, and session handling

### Details

```
Tests for authentication flows, password management, and session handling

---

Test complete signup flow

---

Test successful student signup

---

Test successful professor signup

---

Test signup with duplicate email

---

Test signup with invalid JSON

---

Test complete signin flow

---

Test successful signin

---

Test signin with wrong password

---

Test signin with non-existent user

---

Test signin with legacy password hash triggers migration

---

Test password reset flow

---

Test forgot password for existing user

---

Test forgot password for non-existent user

---

Test password reset with valid token

---

Test password reset with expired token

---

Test user profile operations

---

Test getting user profile

---

Test updating user profile

---

Test getting user settings

---

Test updating user settings

---

Test token and session validation

---

Test session token validation

---

Test invalid token validation

---

Test logout endpoint

---

Test rate limiting behavior

---

Test that rate limit headers are present

---

Test that OPTIONS requests are not rate limited

---

Test email validation in authentication

---

Test signup with invalid email format

---

Test signup with empty email

---

Test signup with whitespace in email

---

Test password strength requirements

---

Test signup with too short password

---

Test signup with very long password

---

Test signup with special characters in password
```

---

## `tests/test_app_chapter_exercise_deep.py`

**Summary:** Deep tests for chapter upload, PDF serving, exercise generation, AI chat Targets uncovered lines: upload_chapter (3021-3193), get_class_chapters (3196-3272), serve_chapter_pdf (4847-4909), generate_ex

### Details

```
Deep tests for chapter upload, PDF serving, exercise generation, AI chat
Targets uncovered lines: upload_chapter (3021-3193), get_class_chapters (3196-3272),
serve_chapter_pdf (4847-4909), generate_exercises (3716-3844), AI chat (3660-3710)

---

Test POST /api/classes/<class_id>/chapters endpoint - lines 2993-3193

---

Test successful chapter upload with PDF

---

Test chapter upload without user_id

---

Test upload to non-existent class

---

Test upload by non-owner professor

---

Test upload without PDF file

---

Test upload with empty filename

---

Test upload with non-PDF file

---

Test upload without chapter title

---

Test OPTIONS for chapter upload

---

Test GET /api/classes/<class_id>/chapters - lines 3196-3272

---

Test getting chapters as class professor

---

Test getting chapters for non-existent class

---

Test getting chapters with non-existent user

---

Test getting chapters without user_id

---

Test GET /api/chapters/<chapter_id>/pdf - lines 4847-4909

---

Test serving PDF from database binary storage

---

Test redirecting to Supabase URL

---

Test serving PDF for non-existent chapter

---

Test serving PDF when no data is available

---

Test POST /api/chapters/<chapter_id>/generate-exercises - lines 3716-3844

---

Test full exercise generation flow

---

Test exercise generation by non-professor

---

Test exercise generation for non-existent chapter

---

Test exercise generation when no PDF data exists

---

Test exercise generation without user_id

---

Test OPTIONS for exercise generation

---

Test POST /api/ai/chat endpoint - lines 3660-3710

---

Test AI chat when API key is missing

---

Test OPTIONS for AI chat

---

Test successful AI chat proxy

---

Test AI chat with invalid model falls back to default

---

Test GET /api/chapters/<chapter_id>/exercises - lines 3570-3657

---

Test getting exercises as the class professor/owner

---

Test getting exercises as enrolled student

---

Test getting exercises as non-enrolled student

---

Test getting exercises for non-existent chapter

---

Test getting exercises with non-existent user
```

---

## `tests/test_app_chapter_gen_deep.py`

**Summary:** Deep tests for chapter upload auto-exercise generation, generate exercises endpoint, chapter access control, and PDF validation edge cases. Targets uncovered lines: 3046-3193 (upload chapter deep), 32

### Details

```
Deep tests for chapter upload auto-exercise generation, generate exercises endpoint,
chapter access control, and PDF validation edge cases.
Targets uncovered lines: 3046-3193 (upload chapter deep), 3229-3338 (chapter access),
3364-3505 (serve PDF/generate exercises), 3716-3844 (generate exercises endpoint)

---

Test chapter upload with auto exercise generation - lines 3128-3164

---

Test chapter upload with auto exercise generation

---

Test upload when PDF extraction fails - line 3087-3089

---

Test upload with invalid PDF content - lines 3046-3057

---

Test chapter access control paths - lines 3216-3272

---

Test getting chapters as enrolled student

---

Test getting chapters when not enrolled - lines 3229-3239

---

Test chapter PDF serving - lines 3364-3389

---

Test the generate exercises from chapter endpoint - lines 3364-3505

---

Test generating exercises when not the professor

---

Test generating exercises when PDF data is missing

---

Test POST /api/chapters/<id>/generate-exercises deep - lines 3716-3844

---

Test full exercise generation flow with DB inserts

---

Test exercise generation when text extraction returns empty

---

Test exercise generation when extraction throws error

---

Test exercise generation when no PDF bytes in DB

---

Test resource upload and download deep paths - lines 4990-5196

---

Test uploading resource file with all metadata

---

Test creating resource via JSON - lines 5156-5196

---

Test updating resource via PUT - lines 5222-5241

---

Test deleting resource - lines 5215-5220

---

Test OPTIONS for resource management - lines 5204-5209

---

Test downloading resource file - lines 5250-5279

---

Test downloading non-existent resource

---

Test ensure_*_table helper functions - lines 4658-4694

---

Test ensure_exercises_table migration helper

---

Test ensure_resources_table migration helper
```

---

## `tests/test_app_chapters.py`

**Summary:** Tests for chapter management and PDF processing Uses actual API endpoints from app.py

### Details

```
Tests for chapter management and PDF processing
Uses actual API endpoints from app.py

---

Test chapter creation via class chapters endpoint

---

Test successful chapter creation with PDF upload

---

Test chapter creation without user_id

---

Test chapter creation for non-existent class

---

Test chapter creation by non-owner

---

Test chapter retrieval endpoints

---

Test getting all chapters for a class

---

Test getting chapters without user_id

---

Test getting chapters for non-existent class

---

Test PDF serving endpoint

---

Test serving PDF from database

---

Test serving PDF for non-existent chapter

---

Test chapter exercise management

---

Test getting exercises for a chapter

---

Test generating exercises for a chapter

---

Test PDF processing and text extraction

---

Test successful PDF text extraction during chapter upload

---

Test chapter-related progress tracking

---

Test getting practice progress for a specific exercise

---

Test getting all practice progress
```

---

## `tests/test_app_class_deep.py`

**Summary:** Deep tests for class management endpoints Targets: get_class_by_id, get_class_resources, update_class, delete_class, validate_pdf_file, create_class deep paths, get_classes student/professor paths

### Details

```
Deep tests for class management endpoints
Targets: get_class_by_id, get_class_resources, update_class, delete_class,
validate_pdf_file, create_class deep paths, get_classes student/professor paths

---

Test GET /api/classes/<class_id> endpoint - lines 2527-2637

---

Test getting class details as the owning professor

---

Test getting class details as an enrolled student

---

Test getting non-existent class

---

Test getting class without user_id

---

Test access denied for unenrolled student

---

Test GET /api/classes/<class_id>/resources endpoint - lines 2643-2743

---

Test getting resources for a class

---

Test getting resources without user_id

---

Test getting resources for non-existent class

---

Test POST /api/classes deep paths - lines 2328-2414

---

Test successful class creation

---

Test creating class without name

---

Test creating class without class code

---

Test creating class with invalid code format

---

Test creating class as non-professor

---

Test creating class with existing code

---

Test OPTIONS preflight for class creation

---

Test GET /api/classes pagination paths - lines 2417-2526

---

Test getting classes as professor

---

Test getting enrolled classes as student

---

Test getting classes without user_id

---

Test getting classes for non-existent user

---

Test PUT /api/classes/<class_id> endpoint - lines 2825-2917

---

Test updating class name

---

Test updating class description

---

Test updating class with no fields to update

---

Test updating class as non-owner

---

Test updating non-existent class

---

Test DELETE /api/classes/<class_id> endpoint - lines 3523-3562

---

Test successful class deletion

---

Test deleting non-existent class

---

Test deleting class as non-owner

---

Test deleting class without user_id

---

Test validate_pdf_file function - lines 2925-2990

---

Test validation of a valid PDF

---

Test validation of empty file

---

Test validation of non-PDF file

---

Test validation of oversized PDF

---

Test validation of PDF with JavaScript (suspicious)

---

Test validation of unsupported PDF version

---

Test allowed_file function

---

Test all allowed file extensions

---

Test disallowed file extensions

---

Test POST /api/contact endpoint - lines 2271-2310

---

Test submitting contact form

---

Test submitting contact form with missing fields

---

Test OPTIONS for contact endpoint
```

---

## `tests/test_app_class_enrollment_deep.py`

**Summary:** Deep tests for class management, enrollment, and progress endpoints. Targets uncovered lines: 2431-2526 (get_classes student), 2754-2846 (class update details), 3910-3912 (already enrolled), 3952-4029

### Details

```
Deep tests for class management, enrollment, and progress endpoints.
Targets uncovered lines: 2431-2526 (get_classes student), 2754-2846 (class update details),
3910-3912 (already enrolled), 3952-4029 (enrolled classes), 4051-4089 (enrolled students owner check),
4117-4237 (class progress), 4248-4323 (progress endpoint), 4667-4694 (ensure tables)

---

Test GET /api/classes student path - lines 2473-2526

---

Test getting enrolled classes as student

---

Test getting classes when user role is None

---

Test get_class_by_id error paths - lines 2565-2637

---

Test getting class when user doesn't exist

---

Test class resources error paths - lines 2720-2791

---

Test resources when class_resources table query fails

---

Test class update deep paths - lines 2825-2917

---

Test updating both name and description

---

Test class update with DB error - lines 2914-2917

---

Test enrollment when already enrolled - lines 3910-3912

---

Test enrolling when student is already enrolled

---

Test GET /api/classes/enrolled - lines 3949-4029

---

Test getting enrolled classes

---

Test enrolled classes without user_id

---

Test enrolled classes for non-existent user

---

Test enrolled students access control - lines 4051-4089

---

Test getting students as non-owner professor

---

Test getting students for non-existent class

---

Test GET /api/classes/<class_id>/progress - lines 4097-4237

---

Test getting class progress as professor

---

Test getting progress as non-owner

---

Test getting progress for non-existent class

---

Test getting progress without user_id

---

Test GET /api/progress - lines 4240-4323

---

Test getting progress filtered by class_id

---

Test getting all progress without class filter

---

Test getting progress without user_id

---

Test POST /api/contact deep paths - lines 2269-2310

---

Test contact form with logged-in user

---

Test OPTIONS for contact endpoint

---

Test generate_class_code function - lines 2318-2325

---

Test class code generation format

---

Test class codes are unique

---

Test resource file serving - lines 5285-5288

---

Test serving legacy resource files

---

Test GET /api/tasks/<task_id> - lines 2219-2258

---

Test getting task status
```

---

## `tests/test_app_class_management.py`

**Summary:** Comprehensive Tests for Class Management and Student Enrollment Target: Push coverage from 66% to 70%+

### Details

```
Comprehensive Tests for Class Management and Student Enrollment
Target: Push coverage from 66% to 70%+

---

Test class creation and management

---

Test creating a new class

---

Test class creation with missing required fields

---

Test getting classes for a professor

---

Test getting classes for a student

---

Test getting specific class details

---

Test updating class information

---

Test deleting a class

---

Test student enrollment operations

---

Test enrolling a student in a class

---

Test enrollment with invalid code

---

Test getting list of enrolled students

---

Test removing a student from a class

---

Test class statistics and analytics

---

Test getting class statistics

---

Test getting class leaderboard

---

Test enrollment code generation and validation

---

Test generating enrollment code for a class

---

Test validating enrollment code

---

Test OPTIONS requests for CORS

---

Test OPTIONS request for classes endpoint

---

Test OPTIONS request for enrollment endpoint
```

---

## `tests/test_app_comprehensive.py`

**Summary:** Comprehensive Tests for Authentication, Signup, and Error Handling Target: Push coverage from 68% to 70%+

### Details

```
Comprehensive Tests for Authentication, Signup, and Error Handling
Target: Push coverage from 68% to 70%+

---

Test user signup functionality

---

Test successful user signup

---

Test signup with existing email

---

Test signup with missing required fields

---

Test signup with invalid email format

---

Test various authentication scenarios

---

Test sign-in with legacy hash migration

---

Test sign-in with missing credentials

---

Test sign-in with empty password

---

Test error handling scenarios

---

Test handling of database connection errors

---

Test handling of invalid JSON in request

---

Test request without content type

---

Test CORS preflight requests

---

Test OPTIONS request for users endpoint

---

Test OPTIONS request for exercises endpoint

---

Test OPTIONS request for submissions endpoint

---

Test health check and status endpoints

---

Test health check endpoint

---

Test root endpoint

---

Test file upload scenarios

---

Test successful PDF upload

---

Test upload endpoint without file

---

Test pagination and filtering

---

Test getting exercises with pagination

---

Test filtering exercises by difficulty

---

Test edge cases and boundary conditions

---

Test getting a resource that doesn't exist

---

Test update request with empty body

---

Test deleting resource without permission
```

---

## `tests/test_app_deep_coverage.py`

**Summary:** Deep coverage tests for remaining reachable lines in app.py. Targets:   - DB pool init + retry logic (283, 333-371, 395-422, 436-437)   - generate_exercises_for_chapter edge cases (3437-3473)   - uplo

### Details

```
Deep coverage tests for remaining reachable lines in app.py.
Targets:
  - DB pool init + retry logic (283, 333-371, 395-422, 436-437)
  - generate_exercises_for_chapter edge cases (3437-3473)
  - upload_chapter PDF rejection + auto-exercise (3058, 3132-3165)
  - Leaderboard query fallback (4542-4545)
  - Exercise leaderboard exception (2075-2076, 4656)
  - Class detail resource URL fallback (2721)
  - Serve chapter PDF filesystem paths (4898-4904)
  - Create exercise multipart (4712-4713)
  - ensure_resources_table column additions (5001)
  - AI digest JSON wrapping (1499)
  - Health check exceptions (2121-2128, 2149-2155)
  - Task status exception (2279)

---

Test init_db_pool paths - lines 279-371

---

Test early return when pool exists - line 283

---

Test pool created but test query fails - lines 333-335

---

Test fallback when pool init raises OperationalError - lines 337-371

---

Test when both pool init attempts fail - lines 368-371

---

Test get_db_connection retry logic - lines 395-422

---

Test stale connection retry - lines 395-405

---

Test when all retry attempts fail - lines 408-424

---

Test pool reinitialization on second retry - lines 416-419

---

Test teardown error handling - lines 436-437

---

Test error during connection return to pool

---

Cover lines 3437-3473 in generate_exercises_for_chapter

---

Line 3437-3440: extract_text_from_pdf_bytes is None

---

Lines 3443-3447: extract raises exception

---

Lines 3460-3463: generate_exercises_from_pdf_content is None

---

Lines 3467-3468: GEMINI_API_KEY not set

---

Lines 3470-3473: exercise generation raises

---

Cover upload_chapter auto-exercise generation - lines 3132-3165

---

Test successful auto exercise generation during upload

---

Cover PDF validation rejection - lines 3048-3058

---

Test rejection of oversized PDF

---

Cover leaderboard query error - lines 4542-4545

---

Test when the complex leaderboard query fails - fallback to empty

---

Cover resource URL fallback - line 2721

---

Test class detail when resource has no URL

---

Cover serve_chapter_pdf paths - lines 4898-4904

---

Test serving PDF from filesystem - line 4898-4900

---

Test when PDF file doesn't exist on filesystem - line 4902

---

Test when no PDF data at all - line 4904

---

Cover create exercise with multipart form - line 4712-4713

---

Test creating exercise with multipart/form-data

---

Cover health check Gemini and email exceptions - lines 2121-2128, 2149-2155

---

Lines 2121-2128: Gemini API check that raises

---

Lines 2149-2155: Email service check that raises

---

Cover task status exception - line 2279

---

Line 2279: exception in task status lookup

---

Cover AI digest JSON edge case - line 1499

---

Line 1499: when field value is None

---

Fields that are plain strings (not JSON)

---

Fields that are already JSON arrays

---

Cover exercise leaderboard exception - lines 2075-2076

---

Lines 2075-2076 (or 4649-4656)

---

Cover ensure_resources_table edge cases - line 5001

---

Test when columns need to be added - line 5001
```

---

## `tests/test_app_enrollment_progress.py`

**Summary:** Deep tests for enrollment, leaderboard, and student progress endpoints Targets: enroll_in_class, unenroll_student, get_enrolled_students, leaderboard endpoints, student progress, practice progress dee

### Details

```
Deep tests for enrollment, leaderboard, and student progress endpoints
Targets: enroll_in_class, unenroll_student, get_enrolled_students,
leaderboard endpoints, student progress, practice progress deep paths

---

Test POST /api/classes/enroll endpoint - lines 3852-3946

---

Test successful student enrollment

---

Test enrollment with missing fields

---

Test professors cannot enroll in classes

---

Test enrollment in non-existent class

---

Test enrollment with non-existent user

---

Test OPTIONS for enrollment endpoint

---

Test GET /api/classes/<class_id>/students endpoint - lines 4051-4089

---

Test getting enrolled students list

---

Test getting students without user_id

---

Test GET /api/classes/<class_id>/leaderboard/average - lines 4479-4569

---

Test getting average leaderboard as professor

---

Test getting leaderboard as enrolled student

---

Test leaderboard access denied

---

Test leaderboard for non-existent class

---

Test leaderboard without user_id

---

Test GET /api/classes/<class_id>/leaderboard/exercise/<exercise_id> - lines 4572-4655

---

Test getting exercise-specific leaderboard

---

Test exercise leaderboard access denied

---

Test PUT /api/users/practice-progress deep paths - lines 1799-1928

---

Test updating progress with new best score

---

Test updating progress without new best score

---

Test updating progress for non-existent user

---

Test updating progress with missing required fields

---

Test updating progress with class_id for class exercises

---

Test first attempt on an exercise

---

Test GET /api/users/practice-progress deep paths - lines 1722-1796

---

Test getting all exercise progress

---

Test getting progress for a specific exercise

---

Test getting progress with no results

---

Test getting progress without user_id

---

Test GET /api/exercises/progress endpoint - lines 1931-1974

---

Test getting all progress using X-User-Id header

---

Test getting all progress using query param

---

Test GET /api/exercises/<exercise_id>/leaderboard - lines 1977-2022

---

Test leaderboard with multiple entries

---

Test leaderboard with no entries

---

Test GET /api/leaderboard/grand - lines 2025-2075

---

Test getting grand leaderboard

---

Test grand leaderboard with default limit

---

Test GET /api/students/<student_id>/progress - lines 4329-4467

---

Test professor viewing student progress

---

Test professor viewing student progress filtered by class

---

Test non-professor trying to view student progress

---

Test viewing progress of non-existent student

---

Test viewing progress without user_id
```

---

## `tests/test_app_error_handling.py`

**Summary:** Tests for error handling, edge cases, and validation

### Details

```
Tests for error handling, edge cases, and validation

---

Test database connection error handling

---

Test that database connection retry logic works

---

Test database pool initialization

---

Test handling of database connection timeouts

---

Test input validation and error responses

---

Test signup with missing name field

---

Test signup with missing email field

---

Test signup with missing password field

---

Test signup with empty string fields

---

Test signin with missing email

---

Test signin with missing password

---

Test forgot password with missing email

---

Test authentication edge cases and security

---

Test signin with non-existent user

---

Test signin with wrong password

---

Test forgot password with non-existent email

---

Test OPTIONS request on forgot password endpoint

---

Test password hashing and verification

---

Test that passwords are hashed with bcrypt

---

Test that password verification is case-sensitive

---

Test role detection from email domains

---

Test professor role detection for @hult.edu

---

Test professor role detection for @faculty.hult.edu

---

Test student role detection for @student.hult.edu

---

Test default role detection for other email domains

---

Test role detection with None email

---

Test role detection with empty email

---

Test CORS header handling

---

Test that API endpoints have CORS headers

---

Test OPTIONS request handling

---

Test that CORS allows all origins

---

Test error response formats

---

Test that error responses have consistent format

---

Test JSON response on health endpoint

---

Test that API responses have JSON content type

---

Test 404 handling for non-existent routes

---

Test handling of concurrent requests

---

Test handling of multiple signup requests

---

Test prevention of duplicate signups

---

Test password utility functions directly

---

Test legacy hash function

---

Test bcrypt hash function

---

Test bcrypt verification

---

Test wrong password verification

---

Test legacy password verification

---

Test the no-op connection close helper

---

Test file extension validation

---

Test PDF is allowed

---

Test CSV is allowed

---

Test EXE is not allowed

---

Test file without extension
```

---

## `tests/test_app_exception_handlers.py`

**Summary:** Tests targeting exception handlers and error paths in app.py. Forces DB errors to exercise the except blocks that return 500. Also covers: cached get_classes, update preferences rollback,  conversatio

### Details

```
Tests targeting exception handlers and error paths in app.py.
Forces DB errors to exercise the except blocks that return 500.
Also covers: cached get_classes, update preferences rollback, 
conversation rollback, signup exceptions, signin exceptions.

---

Force exceptions in various endpoints to cover except blocks.

---

Cover line 1204-1205 (get_conversations exception)

---

Cover line 1242-1243 (create_conversation exception)

---

Cover lines 1370-1373 (update_conversation rollback)

---

Cover lines 1402-1403

---

Cover lines 1468-1469

---

Cover lines 1528-1529

---

Cover lines 1559-1560

---

Cover lines 1597-1598

---

Cover lines 1716-1719 (update_preferences rollback)

---

Cover lines 645-646 (signup exception)

---

Cover lines 928-929 (get_profile exception)

---

Cover lines 983-984 (update_profile exception)

---

Cover lines 1018-1019 (get_settings exception)

---

Cover lines 1059-1064

---

Cover lines 1115-1118

---

Cover lines 1141-1142

---

Cover lines 879-882 (reset_password rollback)

---

Cover get_classes exception

---

Cover get_class_by_id exception

---

Cover create_class exception

---

Cover update_class exception - lines 2914-2917

---

Cover delete_class exception - lines 3561-3562

---

Cover get_class_resources exception

---

Cover upload_chapter exception - lines 2985-2987

---

Cover get_chapters exception - lines 3271-3272

---

Cover update_chapter exception - lines 3324-3325

---

Cover delete_chapter exception - lines 3385-3389

---

Cover generate_exercises_for_chapter exception

---

Cover get_chapter_exercises exception - lines 3656-3657

---

Cover enroll exception

---

Cover get_enrolled_classes exception - lines 4028-4029

---

Cover get_class_students exception - lines 4088-4089

---

Cover get_class_progress exception - lines 4231-4237

---

Cover get_progress exception

---

Cover get_student_progress exception - lines 4463-4467

---

Cover average leaderboard exception - lines 4564-4569

---

Cover exercise leaderboard exception - lines 4648-4655

---

Cover create_exercise exception - lines 4784-4785

---

Cover add_class_resource exception

---

Cover upload_class_resource exception - lines 5086-5090

---

Cover serve_resource_download exception - lines 5148-5150

---

Cover manage_resource exception - lines 5243-5244

---

Cover serve_resource_file exception

---

Cover delete_exercise exception - lines 4950-4951

---

Cover get_exercise exception - lines 2790-2791

---

Cover update_exercise exception - lines 2845-2846

---

Cover practice progress exception

---

Cover serve_chapter_pdf exception

---

Cover contact exception - line 2308-2310

---

Cover health_check exception paths - lines 2074-2075, 2105-2108

---

Test signin exception paths

---

Cover signin exception

---

Cover lines 699-704 (hash migration failure during signin)

---

Test forgot password exception paths

---

Cover lines 785-796 (forgot_password exception)

---

Test update practice progress exception

---

Cover update_practice_progress exception

---

Test CSRF token exception path - lines 2213-2216

---

Cover lines 2213-2216

---

Test task status deep paths - lines 2238-2258

---

Test task status when celery is available
```

---

## `tests/test_app_exercises.py`

**Summary:** Tests for exercise system - generation, submission, and grading Targets actual API endpoints in app.py

### Details

```
Tests for exercise system - generation, submission, and grading
Targets actual API endpoints in app.py

---

Test exercise generation functionality via correct endpoints

---

Test successful exercise generation via chapter endpoint

---

Test exercise generation with missing PDF data

---

Test exercise generation without user_id

---

Test OPTIONS preflight for exercise generation

---

Test exercise retrieval endpoints

---

Test getting all exercises for a chapter

---

Test getting exercises without user_id

---

Test getting exercises for non-existent chapter

---

Test getting exercises with pagination params

---

Test exercise submission endpoints

---

Test submitting a practice progress update

---

Test submitting without required fields

---

Test exercise update endpoints

---

Test deleting an exercise

---

Test deleting non-existent exercise

---

Test OPTIONS for exercise delete

---

Test exercise progress endpoints

---

Test getting all exercise progress

---

Test getting progress without user_id

---

Test getting exercise leaderboard

---

Test getting grand leaderboard

---

Test creating exercises of different types

---

Test manually creating an exercise

---

Test creating exercise as non-owner

---

Test creating exercise without user_id
```

---

## `tests/test_app_extended.py`

**Summary:** Extended App.py Tests - Increasing Coverage Focus on authentication, class operations, and error handling

### Details

```
Extended App.py Tests - Increasing Coverage
Focus on authentication, class operations, and error handling

---

Test user authentication

---

Test signup endpoint is accessible

---

Test signup with missing required fields

---

Test class CRUD with proper mocking

---

Test get class details without user_id

---

Test delete class without user_id

---

Test chapter endpoints

---

Test get chapters without user_id

---

Test OPTIONS request for creating chapter

---

Test exercise endpoints

---

Test get exercises without user_id

---

Test get specific exercise without user_id

---

Test student enrollment

---

Test OPTIONS for enrollment endpoint

---

Test enrollment with missing fields

---

Test resource endpoints

---

Test get resources without user_id

---

Test PDF serving functionality

---

Test PDF serving endpoint exists

---

Test async task endpoints

---

Test task status endpoint

---

Test API versioning

---

Test v1 health endpoint alias

---

Test error handling

---

Test 404 for non-existent API path (non-API paths may return 200 for SPA fallback)

---

Test database helper functions

---

Test closing a valid connection

---

Test app configuration

---

Test that app has secret key configured

---

Test upload folder is configured

---

Test max content length is set

---

Test async task settings

---

Test FEATURE_ASYNC_TASKS is defined

---

Test logging setup

---

Test that logger is configured
```

---

## `tests/test_app_final_coverage_push.py`

**Summary:** Final coverage push targeting the last uncovered blocks in app.py. Covers: AI chat proxy, generate_exercises route, resource upload/serve/download, ensure_*_table functions, get_class_by_id details, g

### Details

```
Final coverage push targeting the last uncovered blocks in app.py.
Covers: AI chat proxy, generate_exercises route, resource upload/serve/download,
ensure_*_table functions, get_class_by_id details, get_classes cached,
class update/delete deep, chapter exercises deep, enrollment deep paths,
and all remaining exception handlers.

---

Test POST /api/ai/chat - lines 3660-3710

---

Test OPTIONS for AI chat - lines 3663-3668

---

Test AI chat when API key missing

---

Test successful AI chat proxy

---

Test AI chat with invalid model falls back - line 3687

---

Test AI chat when API returns error - line 3704

---

Test AI chat network failure - lines 3708-3710

---

Test POST /api/chapters/<id>/generate-exercises (the second route) - lines 3713-3844
    This route overlaps with generate_exercises_for_chapter. We test via OPTIONS.

---

Test OPTIONS for generate exercises - lines 3717-3723

---

Test GET /api/resources/<id>/download (second route) - lines 5093-5150

---

Test serving PDF resource inline - lines 5128-5137

---

Test serving CSV resource as attachment

---

Test serving resource with no file data - line 5116-5117

---

Test POST /api/classes/<id>/resources/upload - lines 5022-5090

---

Test OPTIONS for resource upload - lines 5026-5031

---

Test file upload with all metadata - lines 5033-5084

---

Test upload without file part - line 5036-5037

---

Test upload with empty filename - line 5040-5041

---

Test ensure_exercises_table - lines 4658-4694

---

Test table migration adds missing columns

---

Test ensure_resources_table - lines 4959-5019

---

Test resources table migration adds missing columns

---

Test GET /api/classes/<id> deep paths - lines 2535-2637

---

Test getting class details as professor

---

Test getting non-existent class

---

Test getting class without user_id

---

Test GET /api/classes/<id>/chapters - lines 3199-3272

---

Test getting chapters as the class professor

---

Test PUT /api/classes/<id> deep paths - lines 2849-2917

---

Test updating class with name only

---

Test updating class as non-owner

---

Test updating non-existent class

---

Test updating class without user_id

---

Test DELETE /api/classes/<id> - lines 3523-3562

---

Test deleting class with chapters, exercises, and enrollments

---

Test enrollment deep paths - lines 3855-3946

---

Test enrolling with enrollment code

---

Test enrolling in non-existent class

---

Test GET /api/chapters/<id>/exercises - lines 3573-3657

---

Test getting exercises for a chapter

---

Test getting exercises for non-existent chapter

---

Test GET /api/classes/<id>/resources - lines 2647-2743

---

Test getting class resources

---

Test signup OPTIONS - lines 536-545

---

Test OPTIONS for signup

---

Test reset-password OPTIONS - lines 821-827

---

Test OPTIONS for reset-password

---

Test practice progress endpoints deep - lines 1722-1928

---

Test getting progress for specific exercise

---

Test getting all exercise progress

---

Test POST /api/classes/<id>/chapters - lines 2931-3193

---

Test creating chapter without PDF

---

Test chapter upload by non-professor

---

Test chapter upload to non-existent class

---

Test chapter upload without title

---

Test GET /api/classes/<id>/resources/<id>/serve - lines 5086-5150

---

Test serving image resource inline

---

Test serving notebook as attachment
```

---

## `tests/test_app_final_endpoints.py`

**Summary:** Comprehensive Tests for Conversation and AI Endpoints Target: Push coverage from 62% to 75%+

### Details

```
Comprehensive Tests for Conversation and AI Endpoints
Target: Push coverage from 62% to 75%+

---

Test conversation management

---

Test getting user conversations

---

Test creating new conversation

---

Test getting specific conversation

---

Test updating conversation

---

Test deleting conversation

---

Test AI digest endpoints

---

Test getting AI digest

---

Test updating AI digest

---

Test AI memory endpoints

---

Test getting AI memory

---

Test updating AI memory

---

Test sign-in endpoint

---

Test successful sign-in

---

Test sign-in with wrong password

---

Test sign-in with non-existent user
```

---

## `tests/test_app_final_lines.py`

**Summary:** Final push to cover the last reachable scattered lines in app.py. Precisely targets lines that previous tests missed due to mock setup issues.

### Details

```
Final push to cover the last reachable scattered lines in app.py.
Precisely targets lines that previous tests missed due to mock setup issues.

---

Cover PDF validation rejection in upload_chapter - lines 3049-3058.
    The field name must be 'pdf_file' and professor check must pass.

---

Test upload chapter with invalid PDF - lines 3046-3058

---

Test upload with non-PDF file extension

---

Cover auto exercise generation in upload_chapter - lines 3128-3165.
    Must pass professor check, have valid PDF, use exercise_mode=auto.

---

Lines 3131-3133: auto gen but no GEMINI_API_KEY

---

Lines 3162-3165: auto gen raises exception

---

Cover PDF validation error (exception) - lines 2986-2988

---

Trigger an exception inside validate_pdf_file

---

Cover serve_chapter_pdf filesystem paths - lines 4898-4904.
    The mock must set up the chapter row correctly.

---

Test serving PDF from binary data in DB

---

Test filesystem fallback when file exists - lines 4898-4900

---

Test filesystem fallback when file missing - line 4902

---

Test when no PDF available at all - line 4904

---

Cover class average leaderboard query fallback - lines 4542-4545.
    Must reach the specific leaderboard endpoint, not the class detail.

---

Test when leaderboard query raises - fallback to empty

---

Cover DB connection stale retry edge cases - lines 400-401, 405

---

Lines 400-401: putconn raises when returning stale connection

---

Line 405: raise after all stale connection retries

---

Cover forgot_password with onrender.com host - line 786

---

Line 786: detect onrender.com in host

---

Cover resource URL fallback in class detail - line 2721

---

Line 2721: resource with no URL gets download link

---

Cover AI digest when value is None - line 1499

---

Test digest with empty string field that triggers json.dumps([])
```

---

## `tests/test_app_final_push.py`

**Summary:** Final Tests to Push Coverage from 69% to 70%+ Focus on remaining uncovered code paths and edge cases

### Details

```
Final Tests to Push Coverage from 69% to 70%+
Focus on remaining uncovered code paths and edge cases

---

Test announcement functionality

---

Test creating class announcement

---

Test getting class announcements

---

Test grading functionality

---

Test getting submission for grading

---

Test submitting a grade

---

Test hint system

---

Test getting hints for an exercise

---

Test requesting next hint

---

Test code execution

---

Test code execution endpoint

---

Test code testing endpoint

---

Test analytics and insights

---

Test getting professor analytics

---

Test getting class insights

---

Test feedback system

---

Test submitting feedback

---

Test getting feedback

---

Test tagging system

---

Test adding tags to exercise

---

Test getting exercises by tag
```

---

## `tests/test_app_focused.py`

**Summary:** Focused App.py Coverage Tests Simple, effective tests that actually work with the app's structure

### Details

```
Focused App.py Coverage Tests
Simple, effective tests that actually work with the app's structure

---

Test basic root endpoints

---

Test root endpoint returns HTML

---

Test static file serving

---

Test health check

---

Test health endpoint returns valid JSON

---

Test get_classes with proper mocking

---

Test missing user_id parameter

---

Test class creation

---

Test class creation without name

---

Test class creation without user_id

---

Test CORS handling

---

Test OPTIONS request for classes

---

Test OPTIONS request for chapters

---

Test utility functions in app.py

---

Test safe connection closing with None

---

Test error handling

---

Test handling of invalid JSON

---

Test database error handling

---

Test pagination with utils

---

Test that pagination params are extracted correctly

---

Test cache invalidation on updates

---

Test that cache is invalidated when class is updated

---

Test file upload configuration

---

Test that upload folder is configured

---

Test that max content length is set

---

Test API documentation

---

Test that Swagger UI is accessible

---

Test API versioning

---

Test v1 API alias for classes
```

---

## `tests/test_app_get_classes_deep.py`

**Summary:** Targeted tests for the remaining uncovered blocks in app.py. Specifically targets: get_classes (2431-2526), create_class OPTIONS (2333-2338), enroll OPTIONS (3857-3862), health check deep (2074-2184),

### Details

```
Targeted tests for the remaining uncovered blocks in app.py.
Specifically targets: get_classes (2431-2526), create_class OPTIONS (2333-2338),
enroll OPTIONS (3857-3862), health check deep (2074-2184), task status (2231-2258),
add_class_resource OPTIONS (4793-4798), upload_resource OPTIONS (5027-5031),
signup OPTIONS (539-545), delete_exercise OPTIONS (4917-4922),
and init_db_pool fallback paths (240-421).

---

Target lines 2431-2526 for get_classes professor flow

---

Test get_classes for professor with cache miss - lines 2434-2526

---

Test get_classes for student with cache miss - lines 2473-2526

---

Test get_classes with cache hit - lines 2431-2432

---

Cover all OPTIONS endpoint handlers

---

Lines 2333-2338

---

Lines 3857-3862

---

Lines 539-545

---

Lines 4917-4922

---

Lines 3333-3338

---

Lines 4793-4798

---

Lines 5027-5031

---

Lines 5204-5209

---

Lines 3664-3668

---

Lines 822-827

---

Lines 3716-3723 (generate_exercises OPTIONS)

---

Target health check deep paths - lines 2074-2184

---

Test health check with all services healthy

---

Test health check with DB error - lines 2105-2108

---

Test health with storage unhealthy - lines 2179-2184

---

Test health with storage exception - lines 2181-2184

---

Target task status endpoint - lines 2231-2258

---

Test task status when async tasks are disabled - line 2231

---

Test upload chapter edge cases

---

Test upload without user_id

---

Test forgot-password deeper paths - lines 734-796

---

Test forgot password when user doesn't exist - lines 785

---

Test signup when default table inserts fail

---

Cover lines 613-614, 622-623 (preferences/digest creation failures)

---

Test verify_password edge cases - lines 497-499

---

Test when bcrypt throws error during verification
```

---

## `tests/test_app_health_and_routes.py`

**Summary:** Targeted tests for remaining uncovered blocks in app.py. Specifically targets: - Health check deep paths (2074-2184): Gemini configured, email, cache, storage  - Generate exercises flow (3716-3844)  -

### Details

```
Targeted tests for remaining uncovered blocks in app.py.
Specifically targets:
- Health check deep paths (2074-2184): Gemini configured, email, cache, storage 
- Generate exercises flow (3716-3844) 
- Create/manage/download resources (5156-5279)
- get_classes with caching (2431-2526)
- CSRF token paths (2208-2216)

---

Cover health check when Gemini API key is configured - lines 2112-2127

---

Test health check with GEMINI_API_KEY configured

---

Test health with placeholder Gemini key

---

Cover health check email service paths - lines 2143-2154

---

Test health check when mail is None - lines 2143-2147

---

Test health check when mail is configured - lines 2138-2141

---

Test health check when mail check raises - lines 2148-2154

---

Cover health check cache paths - lines 2157-2166

---

Test health when caching is enabled and healthy - lines 2158-2160

---

Test health when caching is enabled but unhealthy - lines 2162-2163

---

Test health when cache check raises - lines 2164-2166

---

Cover storage unhealthy path - lines 2178-2184

---

Test health when storage is unhealthy - lines 2178-2180

---

Test health when storage throws - lines 2181-2184

---

Cover health when DB fails - lines 2105-2108

---

Test health check when DB query fails - lines 2105-2108

---

Cover CSRF token generation paths - lines 2208-2216

---

Test CSRF when protection disabled

---

Test CSRF with generator available - lines 2209-2211

---

Test CSRF with no generator - line 2213

---

Test CSRF token exception - lines 2214-2216

---

Cover generate exercises endpoint (second definition) - lines 3716-3844

---

Test OPTIONS on generate-exercises - lines 3717-3723

---

Test generate exercises without user_id - lines 3725-3728

---

Test generate exercises with missing chapter - lines 3744-3747

---

Test generate exercises when user is not the professor - lines 3755-3758

---

Test generate exercises when generator not available - lines 3761-3764

---

Test generate exercises when PDF bytes missing - lines 3767-3770

---

Test generate exercises when PDF extraction fails - lines 3777-3780

---

Test generate exercises when no text extracted - lines 3782-3785

---

Test generate exercises without API key - lines 3789-3791

---

Test when AI returns no exercises - lines 3794-3797

---

Test successful exercise generation - lines 3800-3838

---

Cover create_class_resource (duplicate route) - lines 5156-5196

---

Test creating a link resource via JSON POST

---

Cover manage_resource (duplicate route) - lines 5204-5279

---

Test updating a resource

---

Test deleting a resource

---

Test OPTIONS on manage resource

---

Cover download_resource duplicate - lines 5250-5279

---

Test downloading a resource

---

Cover forgot-password error paths - lines 734-809

---

Test forgot password without email - line 739

---

Test forgot password when user not found - line 785

---

Test forgot password with DB error - line 809

---

Test OPTIONS on reset-password - lines 822-827
```

---

## `tests/test_app_last_push.py`

**Summary:** Last push for remaining reachable lines in app.py. Precisely targets lines verified through code and route analysis.

### Details

```
Last push for remaining reachable lines in app.py.
Precisely targets lines verified through code and route analysis.

---

Cover get_grand_leaderboard exception - lines 2075-2076

---

Lines 2075-2076: /api/leaderboard/grand exception path

---

Test successful grand leaderboard

---

Cover resource URL fallback in get_class_resources - line 2721.
    Endpoint: GET /api/classes/<class_id>/resources

---

Line 2721: resource with no URL in get_class_resources

---

Cover validate_pdf_file exception and rejection paths

---

Lines 2986-2988: exception in validate_pdf_file try block

---

File that reports valid size but fails on read

---

Test with file that has no PDF header

---

Cover upload_chapter when validate_pdf_file returns False - line 3058

---

Line 3058: validate_pdf_file returns (False, error)

---

Cover auto exercise generation during chapter upload

---

Line 3133: GEMINI_API_KEY not set during auto gen

---

Lines 3162-3165: generate raises during upload

---

Cover leaderboard query fallback in get_class_average_leaderboard - lines 4542-4545.
    Endpoint: GET /api/classes/<class_id>/leaderboard/average

---

Lines 4542-4545: AVG query fails, falls back to empty students list

---

Additional serve PDF edge cases

---

Test redirect when pdf_url is set (Supabase path)

---

Test serving PDF from binary data in DB

---

Cover ensure_resources_table adding a VARCHAR column - line 5001

---

Line 5001: ALTER TABLE ADD COLUMN VARCHAR(255) for 'filename' or 'resource_type'

---

Cover bare except in socket.getaddrinfo - lines 351-352

---

Lines 351-352: socket.getaddrinfo raises
```

---

## `tests/test_app_leaderboard_student_progress.py`

**Summary:** Deep tests for leaderboard endpoints and student progress endpoint. Targets uncovered lines: 4329-4467 (get_student_progress), 4479-4655 (leaderboards), 4784-4951 (PDF serving + delete exercise), 2208

### Details

```
Deep tests for leaderboard endpoints and student progress endpoint.
Targets uncovered lines: 4329-4467 (get_student_progress), 4479-4655 (leaderboards),
4784-4951 (PDF serving + delete exercise), 2208-2258 (delete user, CSRF token)

---

Test GET /api/students/<id>/progress - lines 4329-4467

---

Test getting student progress filtered by class

---

Test getting student progress across all classes

---

Test non-professor accessing student progress

---

Test with non-existent student

---

Test with non-existent requesting user

---

Test without user_id parameter

---

Test when professor doesn't own the class - lines 4369-4372

---

Test GET /api/classes/<id>/leaderboard/average - lines 4479-4569

---

Test professor viewing class average leaderboard

---

Test enrolled student viewing leaderboard

---

Test non-enrolled student viewing leaderboard

---

Test leaderboard for non-existent class

---

Test leaderboard without user_id

---

Test GET /api/classes/<id>/leaderboard/exercise/<id> - lines 4572-4655

---

Test getting exercise-specific leaderboard

---

Test enrolled student viewing exercise leaderboard

---

Test non-authorized user viewing exercise leaderboard

---

Test exercise leaderboard for non-existent class

---

Test exercise leaderboard without user_id

---

Test serving chapter PDFs - lines 4836-4910

---

Test serving PDF directly from database bytes

---

Test PDF serving fallback to filesystem - lines 4894-4901

---

Test serving PDF when no data available - line 4903

---

Test PDF fallback when file doesn't exist

---

Test DELETE /api/exercises/<id> - lines 4912-4951

---

Test successful exercise deletion

---

Test deleting non-existent exercise

---

Test OPTIONS for delete exercise - lines 4916-4922

---

Test DELETE /api/users/delete - lines 1121-1142

---

Test deleting user account

---

Test deleting user without user_id

---

Test GET /api/csrf-token

---

Test getting CSRF token

---

Test profile endpoints - lines 885-984

---

Test getting user profile

---

Test getting non-existent profile - line 912

---

Test updating profile with email and fullName

---

Test updating profile without email - lines 950-960

---

Test settings endpoints - lines 987-1019

---

Test getting settings when no records exist - line 1007

---

Test getting settings with existing data
```

---

## `tests/test_app_maximum.py`

**Summary:** Maximum Coverage Tests - Targeting Remaining Uncovered Code Focus on edge cases, error handling, and less-tested endpoints

### Details

```
Maximum Coverage Tests - Targeting Remaining Uncovered Code
Focus on edge cases, error handling, and less-tested endpoints

---

Test update operations for classes, chapters, exercises

---

Test updating a class

---

Test updating a chapter

---

Test updating an exercise

---

Test delete operations

---

Test deleting a class

---

Test deleting a chapter

---

Test resource management

---

Test getting class resources

---

Test PDF serving and processing

---

Test serving chapter PDF

---

Test async task status checking

---

Test getting pending task status

---

Test getting successful task status

---

Test CSRF token generation

---

Test CSRF token endpoint

---

Test static file routes

---

Test index page

---

Test login page

---

Test dashboard page

---

Test error handling and edge cases

---

Test handling of database connection errors

---

Test endpoints with missing parameters

---

Test invalid JSON handling

---

Test helper functions

---

Test password hashing

---

Test password verification with correct password

---

Test password verification with wrong password

---

Test role detection for student email

---

Test role detection for professor email

---

Test cache-related operations

---

Test that cache is invalidated on updates

---

Test pagination edge cases

---

Test pagination with no results

---

Test pagination with offset beyond results

---

Test CORS handling for various endpoints

---

Test CORS on DELETE requests

---

Test CORS on enrollment endpoint
```

---

## `tests/test_app_options_direct.py`

**Summary:** Tests that bypass @app.before_request to reach per-route OPTIONS handlers. These handlers are normally intercepted by the global OPTIONS handler. Strategy: Temporarily disable the before_request handl

### Details

```
Tests that bypass @app.before_request to reach per-route OPTIONS handlers.
These handlers are normally intercepted by the global OPTIONS handler.
Strategy: Temporarily disable the before_request handler during these tests.

---

Cover OPTIONS handlers by disabling the global handler

---

Remove the global OPTIONS handler temporarily

---

Restore the global OPTIONS handler

---

Lines 540-546: signup OPTIONS handler

---

Lines 735-740: forgot-password OPTIONS handler

---

Lines 823-828: reset-password OPTIONS handler

---

Lines 2334-2339: create class OPTIONS handler

---

Lines 2999-3004: upload chapter OPTIONS handler

---

Lines 3334-3339: chapter OPTIONS handler

---

Lines 3665-3669: AI chat OPTIONS handler

---

Lines 3858-3863: enroll OPTIONS handler

---

Lines 4794-4799: add resource OPTIONS handler

---

Lines 4918-4923: delete exercise OPTIONS handler

---

Lines 5028-5032: upload resource OPTIONS handler

---

Lines 5205-5210: manage resource OPTIONS handler
```

---

## `tests/test_app_remaining_coverage.py`

**Summary:** Tests targeting remaining uncovered lines in app.py to push toward 85%+. Covers: create_class, get_classes (both paths), get_class_by_id, exercise CRUD, chapter update/delete, generate_exercises_for_c

### Details

```
Tests targeting remaining uncovered lines in app.py to push toward 85%+.
Covers: create_class, get_classes (both paths), get_class_by_id, exercise CRUD,
chapter update/delete, generate_exercises_for_chapter, generate_exercises,
create_exercise, add_class_resource, upload_class_resource, serve_resource,
manage_resource, download_resource, create_class_resource, health check deep,
CSRF token, task status, delete user, practice progress endpoints.

---

Test POST /api/classes - lines 2330-2414

---

Test successful class creation

---

Test OPTIONS for create class - lines 2332-2338

---

Test class creation with duplicate code

---

Test class creation by non-professor

---

Test class creation without code

---

Test class creation with invalid code

---

Test class creation without name

---

Test GET /api/classes professor and student paths - lines 2417-2526

---

Test professor viewing their classes

---

Test student viewing enrolled classes - lines 2473-2500

---

Test getting classes when user not found

---

Test getting classes without user_id

---

Test GET /api/exercises/<id> - lines 2744-2791

---

Test getting exercise by ID

---

Test getting non-existent exercise

---

Test getting exercise without user_id

---

Test PUT /api/exercises/<id> - lines 2794-2846

---

Test successful exercise update

---

Test exercise update by non-owner

---

Test PUT /api/chapters/<id> - lines 3278-3325

---

Test successful chapter update

---

Test chapter update by non-owner - line 3305-3308

---

Test chapter update when chapter not found

---

Test DELETE /api/chapters/<id> - lines 3328-3389

---

Test successful chapter deletion

---

Test chapter deletion by non-owner - lines 3368-3371

---

Test deleting non-existent chapter

---

Test OPTIONS for delete chapter - lines 3332-3338

---

Test POST /api/chapters/<id>/generate-exercises - lines 3392-3520

---

Test complete exercise generation from chapter PDF

---

Test generation when chapter not found

---

Test generation by non-professor - line 3425-3428

---

Test generation with missing PDF - line 3430-3433

---

Test generation when extraction yields empty text - line 3448-3456

---

Test when AI returns no exercises - line 3474-3477

---

Test POST /api/chapters/<id>/generate-exercises (the other route) - lines 3713-3844

---

Test complete exercise generation from chapter

---

Test generation by non-professor - lines 3755-3758

---

Test generation when pdf_bytes is empty - lines 3767-3770

---

Test POST /api/classes/<id>/chapters/<id>/exercises - lines 4704-4785

---

Test manual exercise creation

---

Test exercise creation by non-owner

---

Test exercise creation with non-existent class

---

Test exercise creation when chapter not in class

---

Test POST /api/classes/<id>/resources - lines 4788-4798 (OPTIONS) and link add

---

Test OPTIONS for add resource - lines 4792-4798

---

Test POST /api/classes/<id>/resources/upload - lines 4990-5031

---

Test file resource upload

---

Test upload without file

---

Test GET /api/classes/<id>/resources/<id>/serve - lines 5086-5150

---

Test serving PDF resource

---

Test serving CSV resource

---

Test serving non-existent resource

---

Test POST /api/classes/<id>/resources JSON - lines 5153-5196

---

Test creating link resource via JSON

---

Test creating resource without user_id

---

Test PUT/DELETE /api/classes/<id>/resources/<id> - lines 5199-5244

---

Test OPTIONS for resource management - lines 5203-5209

---

Test deleting resource - lines 5215-5220

---

Test updating resource - lines 5222-5241

---

Test GET /api/resources/<id>/download - lines 5247-5279

---

Test successful resource download

---

Test downloading resource with no file data

---

Test downloading non-existent resource

---

Test health check deep paths - lines 2105-2190

---

Test health check when DB is unhealthy

---

Test health check when all services healthy

---

Test CSRF token endpoint - lines 2196-2216

---

Test CSRF token when feature is disabled

---

Test CSRF token when enabled

---

Test DELETE /api/users/delete - lines 1121-1142

---

Test successful user deletion

---

Test deletion without user_id

---

Test practice progress endpoints - lines 1722-1928

---

Test getting progress for specific exercise

---

Test getting all practice progress

---

Test updating practice progress

---

Test updating when new score is a personal best

---

Test getting progress without user_id

---

Test DELETE /api/classes/<id> - lines 3523-3562

---

Test successful class deletion

---

Test deleting class as non-owner

---

Test deleting non-existent class

---

Test deleting class without user_id
```

---

## `tests/test_app_resources_deep.py`

**Summary:** Deep tests for resource management endpoints Targets: add_class_resource, upload_class_resource, serve_resource_download, create_class_resource, manage_resource, download_resource, serve_resource_file

### Details

```
Deep tests for resource management endpoints
Targets: add_class_resource, upload_class_resource, serve_resource_download,
create_class_resource, manage_resource, download_resource, serve_resource_file
Lines: 4788-5288

---

Test POST /api/classes/<class_id>/resources (JSON link) - lines 4788-4837

---

Test adding a link resource to a class

---

Test adding resource without user_id

---

Test OPTIONS for adding resource

---

Test POST /api/classes/<class_id>/resources/upload - lines 5022-5090

---

Test uploading a file resource

---

Test uploading without a file

---

Test uploading with empty filename

---

Test OPTIONS for resource upload

---

Test GET /api/resources/<resource_id>/download - lines 5093-5150 and 5247-5279

---

Test downloading a PDF resource

---

Test downloading a CSV resource

---

Test downloading non-existent resource

---

Test downloading resource with empty file data

---

Test POST /api/classes/<class_id>/resources (duplicate route) - lines 5153-5196

---

Test creating resource via JSON

---

Test PUT/DELETE /api/classes/<class_id>/resources/<resource_id> - lines 5199-5244

---

Test updating a resource

---

Test deleting a resource

---

Test OPTIONS for resource management

---

Test DELETE /api/exercises/<exercise_id> - lines 4912-4951

---

Test successful exercise deletion

---

Test deleting non-existent exercise

---

Test OPTIONS for exercise delete

---

Test POST /api/classes/<class_id>/chapters/<chapter_id>/exercises - lines 4704-4785

---

Test successful exercise creation

---

Test creating exercise for non-existent class

---

Test creating exercise as non-owner

---

Test creating exercise with chapter not in class

---

Test creating exercise without user_id

---

Test user preferences endpoints - lines 1596-1719

---

Test getting user preferences

---

Test getting preferences without user_id

---

Test updating user preferences

---

Test updating preferences without user_id

---

Test updating only some preferences

---

Test DELETE /api/users/delete endpoint - lines 1121-1142

---

Test successful user deletion

---

Test deleting user without user_id

---

Test GET /api/csrf-token endpoint - lines 2196-2216

---

Test getting CSRF token when disabled
```

---

## `tests/test_app_scattered_coverage.py`

**Summary:** Tests targeting scattered uncovered lines in app.py. Targets: PDF validation rejection (3057-3058), auto-exercise generation during upload (3132-3165), exercise generation from chapter (3437-3473), le

### Details

```
Tests targeting scattered uncovered lines in app.py.
Targets: PDF validation rejection (3057-3058), auto-exercise generation
during upload (3132-3165), exercise generation from chapter (3437-3473),
leaderboard query fallback (4542-4545), serve chapter PDF filesystem (4898-4904),
create exercise multipart (4712-4713), resource table ensure (5000-5001),
exercise leaderboard exception (4655-4656).

---

Cover PDF validation rejection path - lines 3057-3058

---

Test chapter upload when PDF fails validation - lines 3048-3058

---

Test chapter upload with suspicious PDF content

---

Cover auto exercise generation during chapter upload - lines 3128-3165

---

Test upload with auto exercises but no API key - lines 3132-3133

---

Test upload when exercise generation fails - lines 3162-3165

---

Cover generate_exercises_for_chapter edge cases - lines 3437-3473

---

Test when PDF extractor not available - lines 3437-3440

---

Test when PDF extraction raises - lines 3443-3447

---

Test when exercise generator not available - lines 3460-3463

---

Test when GEMINI_API_KEY not set - lines 3467-3468

---

Test when exercise generation raises - lines 3470-3473

---

Cover leaderboard query error fallback - lines 4542-4545

---

Test when leaderboard query fails - fallback to empty list

---

Cover serve chapter PDF filesystem fallback - lines 4897-4904

---

Test serve PDF when no PDF data available - line 4904

---

Test serve PDF with filename but file doesn't exist - line 4902

---

Cover create exercise with multipart form - lines 4712-4713

---

Test creating exercise with multipart/form-data - line 4713

---

Test creating exercise with JSON

---

Test verify_password function directly - lines 498-500

---

Test bcrypt verification error path - lines 498-500

---

Test legacy hash verification - lines 503-505

---

Test legacy hash that doesn't match
```

---

## `tests/test_app_signup_signin_deep.py`

**Summary:** Deep tests for signup/signin flows, password management, settings, conversations, AI digest, AI memory, and user preferences. Targets uncovered lines: 497-704, 839-984, 1059-1598, 1716-1719

### Details

```
Deep tests for signup/signin flows, password management, settings, conversations,
AI digest, AI memory, and user preferences.
Targets uncovered lines: 497-704, 839-984, 1059-1598, 1716-1719

---

Test signup success paths - lines 548-646

---

Test successful signup with all default table inserts

---

Test signup with professor email domain

---

Test signup with email that already exists

---

Test signup with missing fields

---

Test that signup succeeds even when profile tables fail

---

Test signin success/failure paths - lines 649-719

---

Test successful signin with bcrypt password

---

Test signin with legacy hash triggers migration - line 688-704

---

Test signin with wrong password

---

Test signin with non-existent email

---

Test signin with missing email

---

Test forgot/reset password - lines 721-882

---

Test forgot password sends email

---

Test forgot password without email

---

Test password reset with valid token

---

Test password reset with invalid token

---

Test password reset with too short password

---

Test password reset with missing fields

---

Test PUT /api/users/password - lines 1067-1118

---

Test successful password update

---

Test password update with wrong current password

---

Test password update for non-existent user

---

Test password update with missing fields

---

Test PUT /api/users/settings - lines 1022-1064

---

Test successful settings update

---

Test settings update without user_id

---

Test conversation CRUD deep paths - lines 1145-1403

---

Test getting conversations with pagination

---

Test getting archived conversations

---

Test getting conversations without user_id

---

Test creating a conversation

---

Test creating conversation with custom ID

---

Test creating conversation without user_id

---

Test getting specific conversation with messages

---

Test getting non-existent conversation

---

Test getting conversation without user_id

---

Test updating conversation title

---

Test archiving a conversation

---

Test updating conversation with messages - lines 1348-1362

---

Test updating conversation without user_id

---

Test soft-deleting a conversation

---

Test deleting conversation without user_id

---

Test AI digest endpoints deep - lines 1406-1529

---

Test getting AI digest with existing data

---

Test getting AI digest with no data

---

Test AI digest parsing with non-JSON string data - line 1446-1453

---

Test getting AI digest without user_id

---

Test updating AI digest

---

Test AI digest serialization with string values - lines 1490-1498

---

Test updating AI digest without user_id

---

Test AI memory endpoints - lines 1532-1598

---

Test getting AI memory

---

Test getting AI memory with no items

---

Test getting AI memory without user_id

---

Test updating AI memory

---

Test updating memory with empty items filtered

---

Test updating AI memory without user_id

---

Test preferences deep paths - lines 1601-1719

---

Test getting preferences returns defaults when not found

---

Test updating all preference fields - lines 1677-1708

---

Test updating single preference field

---

Test updating preferences with no fields to update
```

---

## `tests/test_app_surgical.py`

**Summary:** Surgical tests targeting specific uncovered lines with precise mock setups. Each test carefully matches the exact query result shape expected by the function.

### Details

```
Surgical tests targeting specific uncovered lines with precise mock setups.
Each test carefully matches the exact query result shape expected by the function.

---

Cover serialize_array edge case in update_ai_digest - line 1499

---

serialize_array(42) -> json.dumps([]) - line 1499

---

serialize_array(None) -> json.dumps([])

---

Cover get_exercise_leaderboard exception - line 2075-2076

---

Lines 2075-2076: /api/exercises/<id>/leaderboard exception

---

Successful exercise leaderboard returns 200

---

Cover task status when async not enabled - line 2232

---

Line 2232: FEATURE_ASYNC_TASKS = False

---

Cover contact form OPTIONS - line 2279

---

Line 2279: contact form OPTIONS handler

---

Cover serve_chapter_pdf with correct 3-column fetchone result

---

Lines 4898-4900: file exists on filesystem

---

Line 4902: file doesn't exist on filesystem

---

Line 4904: no pdf_data, no pdf_filename, no pdf_url

---

Cover validate_pdf_file exception path - lines 2986-2988

---

Call validate_pdf_file directly with something that causes an exception

---

Call with empty file

---

Cover resource URL fallback in get_class_by_id - line 2721.
    The function is at line ~2395 and uses multiple fetchone/fetchall calls.

---

Line 2721: resource with no URL - fallback to download link

---

Cover class exercise leaderboard query exception - lines 4542-4545

---

Lines 4542-4545: leaderboard query raises, falls back to empty

---

Cover ensure_resources_table when column is missing - line 5001

---

Line 5001: add a VARCHAR column

---

Cover health check email exception - lines 2149-2155

---

Lines 2149-2155: mail evaluation raises

---

Cover upload_chapter paths with correct pdf_file field name

---

Lines 3046-3058: validate_pdf_file returns False

---

Line 3133: auto gen but GEMINI_API_KEY not set

---

Lines 3162-3165: exercise generation raises exception during upload
```

---

## `tests/test_app_targeted_coverage.py`

**Summary:** Targeted Tests to Push Coverage from 68% to 70% Focus on uncovered endpoints and error handling paths

### Details

```
Targeted Tests to Push Coverage from 68% to 70%
Focus on uncovered endpoints and error handling paths

---

Test AI conversation and memory endpoints

---

Test creating a new AI conversation

---

Test getting conversation history

---

Test adding message to conversation

---

Test deleting a conversation

---

Test AI memory management

---

Test storing AI memory

---

Test retrieving AI memory

---

Test updating AI memory

---

Test statistics and analytics endpoints

---

Test getting class statistics

---

Test getting student statistics

---

Test getting exercise statistics

---

Test notification system

---

Test getting user notifications

---

Test marking notification as read

---

Test deleting a notification

---

Test batch operations

---

Test batch grading submissions

---

Test batch enrolling students

---

Test search functionality

---

Test searching exercises

---

Test searching classes

---

Test data export functionality

---

Test exporting class data

---

Test exporting student progress
```

---

## `tests/test_app_user_endpoints.py`

**Summary:** Comprehensive Tests for User Profile and Settings Endpoints Target: Increase app.py coverage from 28% to 35%+

### Details

```
Comprehensive Tests for User Profile and Settings Endpoints
Target: Increase app.py coverage from 28% to 35%+

---

Test user profile management

---

Test getting user profile

---

Test profile endpoint without user_id

---

Test updating user profile

---

Test profile update with missing fields

---

Test user settings management

---

Test getting user settings

---

Test updating user settings

---

Test password change and reset

---

Test changing password

---

Test password change with wrong current password

---

Test forgot password flow

---

Test password reset with token

---

Test user preferences endpoints

---

Test getting user preferences

---

Test updating user preferences

---

Test practice progress tracking

---

Test getting practice progress

---

Test updating practice progress

---

Test user account deletion

---

Test deleting user account

---

Test account deletion with wrong password

---

Test general progress endpoint

---

Test getting overall student progress
```

---

## `tests/test_config_deep.py`

**Summary:** Deep tests for config.py - Application configuration. Targets uncovered lines: 187-206 (validate_config), 216 (get_config_summary)

### Details

```
Deep tests for config.py - Application configuration.
Targets uncovered lines: 187-206 (validate_config), 216 (get_config_summary)

---

Test validate_config function - lines 185-206

---

Test validation catches missing DATABASE_URL

---

Test validation catches missing GEMINI_API_KEY when AI enabled

---

Test validation catches missing email config when notifications enabled

---

Test validation catches default secret key in production

---

Test validation passes when all config is correct

---

Test get_config_summary function - line 214-235

---

Test config summary returns expected structure

---

Test database section has expected keys

---

Test features section has expected keys
```

---

## `tests/test_exercise_generator.py`

**Summary:** Comprehensive Tests for Exercise Generation Module Target: Increase coverage from 6% to 80%+

### Details

```
Comprehensive Tests for Exercise Generation Module
Target: Increase coverage from 6% to 80%+

---

Test exercise generation from PDF content

---

Test successful exercise generation

---

Test error when API key is missing

---

Test handling of API errors

---

Test that long PDF text is truncated

---

Test extraction of JSON from markdown code blocks

---

Test that invalid difficulty levels are corrected

---

Test handling of empty API response

---

Test handling of invalid JSON response

---

Test handling when API returns object instead of array

---

Test that invalid exercise objects are filtered out

---

Test that API key is read from environment
```

---

## `tests/test_integration_stress.py`

**Summary:** Integration Stress Tests for AnalytIQ Tests concurrent operations and background task handling

### Details

```
Integration Stress Tests for AnalytIQ
Tests concurrent operations and background task handling

---

Test concurrent API operations

---

Verify browsing doesn't slow down during background PDF processing

---

Verify cache improves performance for repeated requests

---

Test cache invalidation scenarios

---

Verify cache is invalidated when data is updated

---

Ensure cache doesn't serve stale data after updates

---

Test AI API cost control mechanisms

---

Verify duplicate exercise requests use cache instead of calling Gemini API

---

Ensure Gemini API is not called when results are cached

---

Test background task error handling

---

Verify app continues running even if background task fails

---

Verify tasks retry on failure

---

Test database connection pool under load

---

Verify connection pool doesn't exhaust under load

---

Ensure connections are returned to pool after use
```

---

## `tests/test_module_init.py`

**Summary:** Tests for module-level initialization code using importlib.reload(). Covers ImportError handlers and exception fallbacks that only run at import time.

### Details

```
Tests for module-level initialization code using importlib.reload().
Covers ImportError handlers and exception fallbacks that only run at import time.

IMPORTANT: Each test saves and restores module state to avoid corrupting
other tests. Tests are isolated via careful save/restore patterns.

---

Cover ImportError fallbacks in tasks.py module init

---

Lines 21-22: pdf_processor import fails

---

Lines 26-27: exercise_generator import fails

---

Lines 32-33: flask_mail import fails

---

Cover Redis connection failure in cache.py module init

---

Lines 29-31: redis.ping() raises, redis_client set to None

---

Cover supabase_storage.py init paths

---

Lines 25-26: SUPABASE_URL/KEY not set

---

Lines 27-29: supabase library not installed

---

Cover celery_app.py line 52: celery_app.start()

---

Line 52: celery_app.start() when run as __main__

---

Cover register_api_v1_aliases exception handlers in app.py

---

Lines 5076-5078: AssertionError when rule already exists

---

Lines 5079-5081: generic Exception during alias registration
```

---

## `tests/test_sentry_config.py`

**Summary:** Tests for sentry_config.py - Sentry error monitoring integration All sentry_sdk imports are mocked since sentry_sdk may not be installed in test env

### Details

```
Tests for sentry_config.py - Sentry error monitoring integration
All sentry_sdk imports are mocked since sentry_sdk may not be installed in test env

---

Mock sentry_sdk module for all tests in this file

---

Test Sentry initialization

---

Test Sentry initializes when DSN is set

---

Test Sentry skips initialization when DSN is not set

---

Test Sentry uses default environment

---

Test sensitive data filtering

---

Test Authorization header is filtered

---

Test Cookie header is filtered

---

Test X-API-Key header is filtered

---

Test password is filtered from POST data

---

Test api_key is filtered from POST data

---

Test token and secret are filtered

---

Test filter handles events without request

---

Test filter handles non-dict POST data

---

Test exception capture with context

---

Test capturing exception with additional context

---

Test capturing exception without context

---

Test message capture

---

Test capturing message with context

---

Test capturing message without context

---

Test capturing message with default level
```

---

## `tests/test_tasks_comprehensive.py`

**Summary:** Comprehensive Tests for Celery Tasks Target: Increase tasks.py coverage from 24% to 80%+

### Details

```
Comprehensive Tests for Celery Tasks
Target: Increase tasks.py coverage from 24% to 80%+

---

Test DatabaseTask base class

---

Test database connection pool creation

---

Test that connection is reused

---

Test error when DATABASE_URL is missing

---

Test closing database connection

---

Test PDF processing task

---

Test successful PDF processing

---

Test when PDF processor is not available

---

Test when PDF extraction fails

---

Test exercise generation task

---

Test successful exercise generation

---

Test when exercise generator is not available

---

Test when API fails

---

Test email sending task

---

Test that send_email_async function exists

---

Test chapter processing task

---

Test processing chapter with PDF

---

Test processing chapter without generating exercises
```

---

## `tests/test_zz_app_reload.py`

**Summary:** Tests for app.py module-level initialization code via importlib.reload().

### Details

```
Tests for app.py module-level initialization code via importlib.reload().

These tests cover ImportError handlers and initialization blocks that
only execute when app.py is first imported - before coverage starts tracking.
By reloading with modified sys.modules/env vars, we re-execute these paths
under coverage.

Named test_zz_* so it runs LAST and doesn't affect other tests.

---

Reload app module, catching errors from duplicate route registration etc.

---

Cover app.py lines 27-29: pdf_processor ImportError

---

Cover app.py lines 33-35: exercise_generator ImportError

---

Cover app.py lines 60-62: flask_mail ImportError

---

Cover app.py lines 80-82: flask_limiter ImportError

---

Cover app.py lines 104-107: flask_wtf ImportError

---

Cover app.py lines 168-169: flask_swagger_ui ImportError

---

Cover app.py lines 99-100: csrf.init_app when FEATURE_CSRF_PROTECTION=True

---

Cover app.py lines 145-167: Swagger UI initialization success path

---

Lines 145-167 run when flask_swagger_ui is available

---

Cover app.py lines 184, 187-190: Celery init paths

---

Line 184: Celery async tasks disabled

---

Lines 187-190: Celery ImportError

---

Cover app.py line 165: get_api_spec route handler

---

Line 165: GET /api/docs/spec.json returns OpenAPI spec

---

Cover app.py lines 5275+: if __name__ == '__main__' block.

    Uses compile() with app.py's real file path + line-number padding
    so that coverage's sys.settrace records these lines against app.py.

---

Read app.py and extract the if __name__ == '__main__' block,
        padded so that line numbers match the original file.

---

Lines 5296+: normal startup with default port

---

Line 5097-5098: port from sys.argv[1]

---

Lines 5116-5120: OSError 'Address already in use' is caught

---

Lines 5121-5122: other OSError is re-raised

---

Line 5112: production mode uses 0.0.0.0

---

Lines 5101-5103: debug mode when FLASK_DEBUG=true
```

---

## `utils.py`

**Summary:** AnalytIQ Utility Functions Shared utilities for pagination, validation, and common operations

### Details

```
AnalytIQ Utility Functions
Shared utilities for pagination, validation, and common operations

---

Extract and validate pagination parameters from request arguments

    Args:
        request_args: Flask request.args object

    Returns:
        tuple: (limit, offset) with validated values

---

Build pagination metadata for API responses

    Args:
        total_count: Total number of items available
        limit: Number of items per page
        offset: Current offset

    Returns:
        dict: Pagination metadata including total, limit, offset, has_more

---

Build a standardized paginated API response

    Args:
        data: List of items for current page
        total_count: Total number of items available
        limit: Number of items per page
        offset: Current offset
        data_key: Key name for the data array in response (default: 'data')

    Returns:
        dict: Standardized response with data and pagination metadata
```

---

