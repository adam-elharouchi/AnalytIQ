# AnalytIQ Security Reference

Last updated: 2026-02-18

---

## 1. Authentication

- **Mechanism:** JWT Bearer tokens, algorithm HS256 (`config.JWT_ALGORITHM`).
- **Expiry:** 168 hours (7 days) by default; overridden via `JWT_EXPIRY_HOURS` env var.
- **Secret:** `JWT_SECRET_KEY` env var (falls back to `SECRET_KEY`; must not use the dev
  default in production — `validate_config()` enforces this).
- **Token payload:** `user_id`, `role`, `iat`, `exp`; optionally `name` and `email`.
- **Transport:** `Authorization: Bearer <token>` header only; no cookies.

## 2. Authorization

- **`@require_auth`** (`auth_helpers.py`): extracts and verifies the Bearer token, sets
  `g.user_id` and `g.user_role`. Returns 401 on missing or expired tokens.
- **`@require_role(*roles)`** (`auth_helpers.py`): must be stacked after `@require_auth`;
  returns 403 when `g.user_role` is not in the allowed set.
- **TESTING bypass guard:** the bypass is gated on both `app.config["TESTING"] == True`
  AND `config.ENV != "production"`, so it cannot fire in a production process.
- **OPTIONS passthrough:** OPTIONS requests skip auth to support CORS preflight.

## 3. Password Policy

- **Minimum length:** 8 characters (`config.MIN_PASSWORD_LENGTH`).
- **Maximum length:** 72 characters (`config.MAX_PASSWORD_LENGTH`) — bcrypt hard limit.
- Enforced at **signup** (`POST /api/users/signup`) and **reset-password**
  (`POST /api/users/reset-password`).
- **Hashing:** bcrypt, 12 rounds (`config.BCRYPT_LOG_ROUNDS`), automatic salt.
- **Legacy hash migration:** on signin, if the stored hash is not a bcrypt hash (`$2b$`
  prefix), the legacy integer-XOR hash is verified and the password is transparently
  rehashed to bcrypt; `hash_password_legacy()` is kept only for this migration path.
- **Reset tokens:** `secrets.token_urlsafe(32)`, stored in `password_resets` table,
  expire in 1 hour, deleted after use.

## 4. Rate Limiting

Flask-Limiter (Redis storage in production, in-memory in development).

| Endpoint                          | Limit                          |
|-----------------------------------|--------------------------------|
| `POST /api/users/signup`          | 5 per hour                     |
| `POST /api/users/signin`          | 10 per minute                  |
| `POST /api/users/forgot-password` | 3 per hour                     |
| `POST /api/users/reset-password`  | 5 per hour                     |
| `POST /api/ai/chat`               | 20/min + 100/hr (per-user key) |
| All other endpoints (production)  | 200/day + 50/hr (default)      |
| All other endpoints (development) | 50 000/day + 2 000/hr          |

Default limits overridden via `RATE_LIMIT_DAY` / `RATE_LIMIT_HOUR` env vars.

## 5. Input Validation

- **`validate_fields(data, rules)`** (`auth_helpers.py`): checks presence and max-length for any field list.
- **`validate_email(email)`** (`auth_helpers.py`): RFC 5321 regex + 254-char cap.
- Field length limits (from `config.py`):

  | Field                   | Limit        |
  |-------------------------|--------------|
  | Email                   | 254 chars    |
  | Name                    | 100 chars    |
  | Class name              | 200 chars    |
  | Class description       | 2 000 chars  |
  | Chapter title           | 300 chars    |
  | Exercise title          | 300 chars    |
  | Exercise description    | 5 000 chars  |
  | Solution code           | 20 000 chars |
  | AI chat message         | 50 000 chars |
  | AI conversation history | 100 messages |

## 6. Security Headers

Applied by `after_request()` in `app.py` to all `/api/*` responses:

| Header                      | Value                                              |
|-----------------------------|----------------------------------------------------|
| `X-Content-Type-Options`    | `nosniff`                                          |
| `X-Frame-Options`           | `DENY`                                             |
| `Referrer-Policy`           | `strict-origin-when-cross-origin`                  |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (non-debug)  |
| `Cache-Control`             | `no-store, no-cache, must-revalidate, max-age=0`   |

**Content-Security-Policy** is currently in **report-only mode** on all responses.
Directive: `default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com unpkg.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'`

## 7. File Upload Security

- **`MAX_CONTENT_LENGTH`:** 500 MB (Flask hard reject before handler runs).
- **PDF-specific limit:** 50 MB (`config.MAX_PDF_SIZE_MB`).
- **Allowed extensions:** `pdf, csv, xlsx, xls, json, txt, ipynb, docx` (`config.ALLOWED_EXTENSIONS`).
- **PDF header check:** first 1 024 bytes must contain `%PDF` magic bytes.
- **Suspicious pattern scan:** first 10 KB scanned for `/JavaScript`, `/JS`, `/Launch`, `/EmbeddedFile`.

## 8. CSRF

- `WTF_CSRF_ENABLED` defaults to `False` (`FEATURE_CSRF=False` env var).
- All API routes carry `@csrf_exempt`.
- **Rationale:** stateless JWT Bearer auth — `Authorization` header is not sent by cross-origin forms.
- **TODO:** re-enable if session-cookie auth is ever introduced.

## 9. FERPA Audit Log

- Module: `audit.py`; table: `audit_log` (auto-created on first use).
- Schema: `id, user_id, action, resource_type, resource_id, ip_address, details (JSONB), created_at`.
- Indexed on `user_id` and `created_at DESC`.
- Audit row and business operation share the same transaction (atomic).
- `audit()` never raises; failures logged as warnings.

**13 audited action codes:** `CREATE_USER`, `RESET_PASSWORD`, `UPDATE_PROFILE`, `UPDATE_PASSWORD`,
`DELETE_USER`, `CREATE_CLASS`, `DELETE_CLASS`, `ENROLL_CLASS`, `CREATE_CHAPTER`, `DELETE_CHAPTER`,
`CREATE_EXERCISE`, `DELETE_EXERCISE`, `EXERCISE_SUBMISSION`

## 10. CI Security Scan

- **Tool:** Bandit (`bandit -r . -f json`), separate `security-scan` job on every push/PR.
- Report uploaded as GitHub Actions artifact `security-report/bandit-report.json`.
- Currently `continue-on-error: true` — failures do not block merge.

## 11. Known Limitations / TODO

- CSP is report-only; switch to enforcement after reviewing violations.
- Bandit `continue-on-error: true` should be removed so failures block CI.
- `FEATURE_CSRF` defaults to `False`; revisit if cookie-based flows are added.
- Delete `hash_password_legacy()` once confirmed zero users with non-`$2b$` hashes.
- `CORS_ORIGINS` defaults to `*`; set to `https://www.myanalytiq.org` in production.
