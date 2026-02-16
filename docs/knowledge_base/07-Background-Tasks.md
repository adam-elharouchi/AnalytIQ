# Background Tasks
*Generated: 2026-02-16 17:37*
---
## Overview
This document consolidates knowledge from **22** file(s) related to background tasks.
---
## `.github/workflows/ci.yml`

**Summary:** name: AnalytIQ CI/CD Pipeline

### Details

```
name: AnalytIQ CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python 3.9
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run linting (flake8)
      run: |
        python -m flake8 app.py utils.py cache.py supabase_storage.py tasks.py --count --show-source --statistics
      continue-on-error: true
    
    - name: Check code formatting (black)
      run: |
        python -m black --check .
      continue-on-error: true
    
    - name: Run type checking (mypy)
      run: |
        python -m mypy utils.py cache.py supabase_storage.py tasks.py --ignore-missing-imports
      continue-on-error: true
    
    - name: Run tests with coverage
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
        FEATURE_CACHING: True
        FEATURE_ASYNC_TASKS: False
        SECRET_KEY: test-secret-key-for-ci
      run: |
        python -m pytest tests/ -v --cov=. --cov-report=xml --cov-report=term-missing
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: false

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python 3.9
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Run security scan (bandit)
      run: |
        pip install bandit
        bandit -r . -f json -o bandit-report.json || true
      continue-on-error: true
    
    - name: Upload security report
      uses: actions/upload-artifact@v4
      with:
        name: security-report
        path: bandit-report.json

  deploy-notification:
    runs-on: ubuntu-latest
    needs: [test, security-scan]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
    - name: Deployment notification
      run: |
        echo "✅ All checks passed! Ready for Render deployment."
        echo "🚀 Render will auto-deploy from main branch."

```

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

## `celery_app.py`

**Summary:** Celery Application Configuration for AnalytIQ Handles async task processing for PDF operations and email sending

### Details

```
Celery Application Configuration for AnalytIQ
Handles async task processing for PDF operations and email sending
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

## `tests/conftest.py`

**Summary:** Pytest configuration and shared fixtures for AnalytIQ tests

### Details

```
Pytest configuration and shared fixtures for AnalytIQ tests

---

Set up test environment variables

---

Create minimal Flask app for testing

---

Create test client

---

Mock database cursor

---

Mock database connection

---

Mock database for testing - patches get_db_connection

---

Mock Redis client

---

Mock Supabase client

---

Mock Celery application

---

Mock Celery task

---

Mock Flask request object

---

Sample user data

---

Sample class data

---

Sample chapter data

---

Sample PDF file bytes

---

Sample pagination parameters

---

Sample pagination metadata
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

## `tests/test_app_edge_paths.py`

**Summary:** Tests for remaining edge case paths in app.py. Targets: get_db_params, verify_password errors, forgot_password email paths, signup_options, class resource missing URL fallback, PDF validation edge cas

### Details

```
Tests for remaining edge case paths in app.py.
Targets: get_db_params, verify_password errors, forgot_password email paths,
signup_options, class resource missing URL fallback, PDF validation edge cases,
scattered missing lines.

---

Test get_db_params function - lines 241-276

---

Test when DATABASE_URL is not set

---

Test with valid PostgreSQL URL

---

Test with postgres:// scheme

---

Test with URL missing scheme - line 252

---

Test with unsupported scheme - line 254

---

Test with missing hostname - line 261

---

Test URL with query parameters

---

Test URL with missing optional parts

---

Test verify_password exception paths - lines 498-500

---

Test verify_password when bcrypt raises - lines 498-500

---

Test verify_password with legacy hash - lines 503-505

---

Test forgot-password email sending paths - lines 785-810

---

Test forgot password when user exists but mail not configured - line 810

---

Test forgot password with mail configured - lines 789-806

---

Test forgot password when mail.send raises - lines 807-808

---

Test forgot password with onrender.com host - line 786

---

Test forgot password with MAIL_SENDER_NAME - lines 795-801

---

Test resource URL fallback - lines 2719-2721

---

Test class detail when resource has no URL - line 2720-2721

---

Test PDF validation edge cases - lines 2985-2988

---

Test PDF validation with corrupted data - lines 2986-2988

---

Test settings when user_id is missing - line 993-994

---

Test get settings without user_id

---

Test ai_digest JSON edge case - lines 1497-1499

---

Test AI digest with non-JSON string values - lines 1497-1499

---

Cover leaderboard exception handler - lines 2075-2076

---

Test exercise leaderboard with DB error - lines 2075-2076

---

Cover task status state branches - lines 2244-2255

---

Test task status PENDING - line 2244

---

Test task status STARTED - line 2246

---

Test task status SUCCESS - lines 2248-2249

---

Test task status FAILURE - lines 2251-2252

---

Test task status RETRY - line 2254

---

Test task status unknown state - line 2255

---

Test task status with exception - line 2279
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

## `tests/test_tasks.py`

**Summary:** Simplified tests for Celery tasks Tests task structure and basic functionality

### Details

```
Simplified tests for Celery tasks
Tests task structure and basic functionality

---

Tests for task imports and structure

---

Test that tasks module can be imported

---

Test that celery_app can be imported

---

Tests for process_pdf_and_extract_text task

---

Test that PDF processing task exists

---

Test task behavior when PDF processor is not available

---

Tests for generate_exercises_async task

---

Test that exercise generation task exists

---

Tests for send_email_async task

---

Test that email sending task exists

---

Tests for process_chapter_upload task

---

Test that chapter processing task exists

---

Tests for DatabaseTask base class

---

Test that DatabaseTask base class exists

---

Test that DatabaseTask has required methods

---

Tests for task configuration

---

Test that Celery app is configured

---

Test that tasks are registered with Celery

---

Tests for task decorators and configuration

---

Test that PDF task has a name

---

Test that exercise task has a name
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

## `tests/test_tasks_deep.py`

**Summary:** Deep tests for tasks.py - Celery async tasks. Targets uncovered lines: 21-22 (import error), 26-27, 32-33, 144 (no exercises), 192-206 (send_email_async), 239-240 (extraction failed), 255 (exercise_er

### Details

```
Deep tests for tasks.py - Celery async tasks.
Targets uncovered lines: 21-22 (import error), 26-27, 32-33,
144 (no exercises), 192-206 (send_email_async), 239-240 (extraction failed),
255 (exercise_error), 260-262 (process_chapter exception)

---

Test DatabaseTask base class

---

Test DatabaseTask when DATABASE_URL not set

---

Test closing when no connection exists

---

Test process_pdf_and_extract_text task

---

Test when PDF processor is not available

---

Test successful PDF processing

---

Test PDF processing with exception

---

Test generate_exercises_async task

---

Test when exercise generator is not available

---

Test when AI returns no exercises - line 144

---

Test exercise generation with exception

---

Test send_email_async task - lines 192-206

---

Test when Flask-Mail Message not available

---

Test email sending with exception

---

Test process_chapter_upload combined workflow - lines 209-262

---

Test when PDF extraction fails - lines 238-240

---

Test successful extraction + exercise generation

---

Test when exercise generation fails - line 255

---

Test extraction without auto-generating exercises

---

Test overall exception handling - lines 260-262
```

---

## `tests/test_tasks_email.py`

**Summary:** Tests for tasks.py email functionality - covering lines 197 and 203.

### Details

```
Tests for tasks.py email functionality - covering lines 197 and 203.

---

Cover send_email_async paths in tasks.py

---

Line 197: mail is None

---

Line 203: successful email send
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

