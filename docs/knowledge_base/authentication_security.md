# Authentication & Security

This document outlines the security architecture, authentication flows, and protective measures implemented in AnalytIQ.

## 🔐 Authentication System

### JWT Implementation
AnalytIQ uses **JSON Web Tokens (JWT)** for stateless authentication.
- **Token Generation**: Created upon login/signup (`create_jwt_token` in `app.py`).
- **Storage**: Stored in browser `localStorage` as `auth_token`.
- **Transmission**: Sent in the `Authorization` header: `Bearer <token>`.
- **Expiration**: Tokens are valid for **7 days** (`JWT_ACCESS_TOKEN_EXPIRES_HOURS` in config).
- **Signing**: HMAC SHA-256 (HS256) using `SECRET_KEY`.

### User Roles
Roles are determined at signup based on the email domain:
1.  **Professor**: Emails ending in `@hult.edu` or `@faculty.hult.edu`.
2.  **Student**: All other emails (defaults to student).

### Protected Endpoints
Routes are protected using the `@require_auth` decorator in `app.py`.
```python
@app.route('/api/protected-resource')
@require_auth
def protected_resource():
    current_user_id = g.user_id
    current_role = g.user_role
    # ... logic ...
```

---

## 🛡️ Security Measures

### 1. Cross-Origin Resource Sharing (CORS)
- **Policy**: Restricted to specific domains defined in `CORS_ORIGINS`.
- **Production**: `https://www.myanalytiq.org`, `https://myanalytiq.org`.
- **Development**: Allows `*` or `file://` if `FLASK_ENV=development`.

### 2. Rate Limiting
- **Implementation**: `Flask-Limiter` with **Redis** backend.
- **Limits**:
    - Global: `1000 per day`, `100 per hour`.
    - Specific endpoints (e.g., signup): `5 per hour`.
- **Fallback**: Uses memory storage if Redis is unavailable (dev mode).

### 3. Password Security
- **Algorithm**: **bcrypt**
- **Configuration**: 12 rounds of salting.
- **Legacy Support**: Fallback to legacy hash check for older accounts with auto-migration to bcrypt upon successful login.

### 4. Data Protection
- **SQL Injection**: Prevented using parameterized queries (`psycopg2`).
- **XSS**: Jinja2 auto-escaping enabled for templates.
- **CSRF**: `Flask-WTF` CSRF protection enabled for forms (optional feature flag `FEATURE_CSRF`).

### 5. Error Monitoring (Sentry)
- **PII Filtering**: Sensitive data (passwords, tokens) is filtered out before sending events to Sentry.
- **Environment Tagging**: Events are tagged with `production` or `development`.

---

## ⚙️ Security Configuration

| Environment Variable | Description |
| :--- | :--- |
| `SECRET_KEY` | Signs session cookies and JWT tokens. |
| `CORS_ORIGINS` | Comma-separated list of allowed origins. |
| `SENTRY_DSN` | Sentry project DSN for error tracking. |
| `FEATURE_CSRF` | Enable/Disable CSRF protection (`True`/`False`). |
