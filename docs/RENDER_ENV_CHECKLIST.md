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
