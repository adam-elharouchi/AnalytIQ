# SSO & Tenant Authentication

## Overview

AnalytIQ supports per-tenant Single Sign-On (SSO) via OAuth2/OpenID Connect (OIDC). Each tenant can configure their own identity provider (Google Workspace, Microsoft Azure AD / Entra ID, or any generic OIDC-compliant IdP). SSO is gated by the `FEATURE_SSO` environment variable and is disabled by default.

SAML 2.0 is intentionally deferred — it requires `libxmlsec1` native system libraries that are not available on Render's default Python buildpack.

---

## Role Model

```
superadmin
    └── full platform control

tenant_admin
    └── same capabilities as superadmin, but scoped to their tenant only

professor   (separate track — teaching, not administration)
    └── manages classes, chapters, exercises within their classes

student
    └── accesses content within enrolled classes
```

`tenant_admin` and `professor` are **parallel roles**, not a hierarchy. A `tenant_admin` is an administrative role — they can manage users, approve accounts, configure SSO, and oversee everything inside their tenant. They are not a professor and do not teach classes unless they are also explicitly enrolled.

| Role | Scope | Capabilities | How assigned |
|------|-------|-------------|--------------|
| `superadmin` | Platform-wide | All admin actions across all tenants | Auto from `@myanalytiq.org` email at signup (requires manual approval) |
| `tenant_admin` | Single tenant (`tenant_id`) | All admin actions within their tenant: manage users, approve accounts, configure SSO, manage classes/content | Explicitly by superadmin via `PATCH /api/superadmin/users/<id>/role` + `tenant_id` |
| `professor` | Platform-wide | Create and manage their own classes, chapters, exercises | Assigned manually by superadmin or tenant_admin |
| `student` | Platform-wide | Access enrolled class content, submit exercises | Default for all non-`@myanalytiq.org` email domains |

### Key distinctions

- `tenant_admin` is **not** a professor. They hold an administrative seat, not a teaching seat.
- `superadmin` has **cross-tenant** authority (e.g. can manage any tenant's SSO, impersonate any user).
- `tenant_admin` has **within-tenant** authority only. They cannot see or modify other tenants' data.
- A user can only hold one role. A `tenant_admin` who also teaches should be given `superadmin` or a separate professor account under the same tenant.

`tenant_admin` is never auto-assigned from an email domain. A superadmin promotes an existing user and must supply a `tenant_id` to scope them.

---

## New Files

| File | Purpose |
|------|---------|
| `migrations/004_sso_and_tenant_admin.sql` | Creates `tenant_sso_providers` table; adds SSO identity columns to `users` |
| `repositories/sso_repository.py` | All SQL for provider CRUD and user identity linking |
| `blueprints/sso.py` | Full SSO blueprint — public login flow + admin management routes |
| `blueprints/tenant_admin.py` | Tenant-scoped admin API (users, classes, approvals, audit, analytics) |
| `templates/tenant-admin-dashboard.html` | Tenant admin dashboard — mirrors superadmin layout, tenant-scoped |
| `static/js/tenant-admin.js` | `TenantAdminDashboard` JS class |

---

## Database Schema

### `tenant_sso_providers`

```sql
CREATE TABLE tenant_sso_providers (
    provider_id             VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id               VARCHAR(255) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    provider_name           VARCHAR(100) NOT NULL,
    provider_type           VARCHAR(20)  NOT NULL,   -- 'google' | 'microsoft' | 'oidc'
    client_id               TEXT         NOT NULL,
    client_secret           TEXT         NOT NULL,   -- Fernet-encrypted
    discovery_url           TEXT         NOT NULL,   -- OIDC .well-known endpoint
    allowed_domains         TEXT[],                  -- optional email domain allowlist
    role_mapping_attribute  VARCHAR(100),            -- which OIDC claim carries role value
    role_mapping            JSONB        DEFAULT '{}', -- e.g. {"Staff":"professor","Students":"student"}
    default_role            VARCHAR(50)  DEFAULT 'student',
    is_enabled              BOOLEAN      DEFAULT true,
    created_by              VARCHAR(255) REFERENCES users(user_id) ON DELETE SET NULL,
    created_at              TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
```

### `users` table extensions (migration 004)

```sql
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS sso_provider_id VARCHAR(255)
        REFERENCES tenant_sso_providers(provider_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS sso_subject TEXT;

-- Unique: one user per (provider, subject), NULLs excluded
CREATE UNIQUE INDEX IF NOT EXISTS uq_sso_user_identity
    ON users (sso_provider_id, sso_subject)
    WHERE sso_provider_id IS NOT NULL;
```

Users created via SSO have `password_hash = NULL`. They can only sign in via SSO unless an admin manually sets a password.

---

## API Endpoints

### Public (no auth required)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/sso/providers` | Returns enabled providers for login page buttons |
| `GET` | `/api/sso/init/<provider_id>` | Returns `{"auth_url": "..."}` — frontend redirects browser here |
| `GET` | `/api/sso/callback/<provider_id>` | IdP redirects here with `?code=&state=`; issues JWT, redirects to login page |

Rate limit on `/api/sso/init`: 30/minute.

### Admin (`tenant_admin` or `superadmin` required)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/sso/admin/providers` | List providers for caller's tenant (superadmin can pass `?tenant_id=`) |
| `POST` | `/api/sso/admin/providers` | Create a new provider config |
| `PUT` | `/api/sso/admin/providers/<id>` | Update provider (partial update) |
| `DELETE` | `/api/sso/admin/providers/<id>` | Remove provider |

`tenant_admin` users are automatically scoped to their own `tenant_id` — they cannot manage other tenants' providers. `superadmin` can manage any tenant.

---

## OIDC Login Flow

```
Browser                     Frontend (auth.js)          Backend (sso.py)              IdP
  │                               │                           │                         │
  │── click SSO button ──────────>│                           │                         │
  │                               │── GET /api/sso/providers ─>│                         │
  │                               │<─ [{provider_id, ...}] ───│                         │
  │                               │── GET /api/sso/init/<id> ─>│                         │
  │                               │                           │── generate state ────────│
  │                               │                           │── store state in Redis   │
  │                               │<─ {auth_url} ─────────────│                         │
  │<── window.location.href ──────│                           │                         │
  │─────────────────────────────────────────── GET auth_url ──────────────────────────>│
  │<──────────────────────────── redirect to /api/sso/callback/<id>?code=&state= ──────│
  │                               │                           │                         │
  │────────────────────────────── GET /api/sso/callback/<id> ─>│                         │
  │                               │                           │── verify state (Redis)   │
  │                               │                           │── exchange code → tokens │
  │                               │                           │── fetch userinfo         │
  │                               │                           │── upsert user in DB      │
  │                               │                           │── issue JWT              │
  │<──────────── redirect to /login.html?sso_token=<jwt> ─────│                         │
  │── DOMContentLoaded ──────────>│                           │                         │
  │                               │── handleSSOTokenParam()   │                         │
  │                               │── saveToken + saveUser    │                         │
  │<── redirect to index.html ────│                           │                         │
```

---

## User Upsert Logic (SSO callback)

Resolution order mirrors the existing LTI upsert pattern in `blueprints/lti.py`:

1. **Match by `sso_provider_id` + `sso_subject`** — returning user, issue JWT directly
2. **Match by email** — link SSO identity to existing account, issue JWT
3. **Create new SSO-only user** — `password_hash = NULL`, `tenant_id` from provider, role from mapping; create companion rows (`user_profiles`, `user_settings`, `user_preferences`, `ai_agent_digest`)

---

## Role Mapping

When creating a new SSO user, the role is determined by `_map_role()` in `blueprints/sso.py`:

1. Read the OIDC claim named in `role_mapping_attribute` (e.g. `"department"`, `"groups"`)
2. Look up that claim's value in `role_mapping` JSON (exact match first, then substring)
3. Fall back to `default_role` (defaults to `"student"`)

**Example provider config:**
```json
{
  "role_mapping_attribute": "department",
  "role_mapping": {
    "Faculty": "professor",
    "Staff": "professor",
    "Student": "student"
  },
  "default_role": "student"
}
```

If no `role_mapping_attribute` is set, all SSO users get `default_role`.

---

## Client Secret Encryption

Client secrets are Fernet-encrypted before being stored in the database. The encryption key is derived from the app's `SECRET_KEY`:

```python
key = hashlib.sha256(SECRET_KEY.encode()).digest()
fernet = Fernet(base64.urlsafe_b64encode(key))
```

**Important:** If `SECRET_KEY` is rotated, existing client secrets in the database become unreadable. Re-enter them via `PUT /api/sso/admin/providers/<id>` after a key rotation.

---

## OAuth2 State Management

The OAuth2 `state` parameter is stored in Redis with a 10-minute TTL to prevent CSRF attacks:

- Key: `sso_state:{state}`
- Value: `{"provider_id": "<id>"}`
- TTL: `SSO_STATE_TTL` seconds (default 600)

If Redis is unavailable, state storage silently fails and the callback will reject the request (state mismatch). This is the safe/secure failure mode — SSO login will fail but the app remains accessible via email/password.

---

## JWT Changes

The JWT payload now includes an optional `tenant_id` claim:

```json
{
  "user_id": "...",
  "role": "tenant_admin",
  "tenant_id": "abc-123",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "iat": 1234567890,
  "exp": 1235172690
}
```

`g.tenant_id` is set by `require_auth` for all authenticated requests. For `professor` and `student` users, `g.tenant_id` may be `None`.

---

## Well-Known Discovery URLs

| Provider type | Discovery URL |
|---------------|---------------|
| `google` | `https://accounts.google.com/.well-known/openid-configuration` (hardcoded) |
| `microsoft` | `https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration` — enter the Azure AD tenant ID or `common` in the `discovery_url` field |
| `oidc` | Full discovery URL — must be provided when creating the provider |

Discovery documents are cached in-process. A process restart clears the cache.

---

## Assigning the `tenant_admin` Role

Only a `superadmin` can promote a user to `tenant_admin`:

```http
PATCH /api/superadmin/users/<user_id>/role
Authorization: Bearer <superadmin_jwt>
Content-Type: application/json

{
  "role": "tenant_admin",
  "tenant_id": "<tenant_id>"
}
```

`tenant_id` is required when setting `tenant_admin`. The user's `tenant_id` column is updated and their next sign-in JWT will include the `tenant_id` claim.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FEATURE_SSO` | `False` | Set to `True` to enable all SSO routes |
| `SSO_STATE_TTL` | `600` | OAuth2 state lifetime in seconds (Redis TTL) |
| `FRONTEND_URL` | `https://myanalytiq.org` | Used to build callback URIs and post-login redirects |

---

## Activation Checklist

1. Run the migration:
   ```bash
   psql $DATABASE_URL -f migrations/004_sso_and_tenant_admin.sql
   ```

2. Set `FEATURE_SSO=True` in Render environment variables.

3. Register your app with the IdP and obtain a `client_id` and `client_secret`.
   - **Google:** [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials → OAuth 2.0 Client
     - Authorized redirect URI: `https://myanalytiq.org/api/sso/callback/<provider_id>`
   - **Microsoft:** [Azure Portal](https://portal.azure.com/) → App registrations → New registration
     - Redirect URI: `https://myanalytiq.org/api/sso/callback/<provider_id>`
     - Note: `provider_id` is known after creating the provider record — create it first, then update the IdP config.

4. Create the provider record (as superadmin):
   ```http
   POST /api/sso/admin/providers
   Authorization: Bearer <superadmin_jwt>
   Content-Type: application/json

   {
     "provider_name": "Hult Microsoft",
     "provider_type": "microsoft",
     "tenant_id": "<analytiq_tenant_id>",
     "client_id": "<azure_client_id>",
     "client_secret": "<azure_client_secret>",
     "discovery_url": "<azure_tenant_id_or_common>",
     "allowed_domains": ["hult.edu", "student.hult.edu"],
     "role_mapping_attribute": "department",
     "role_mapping": {"Faculty": "professor"},
     "default_role": "student"
   }
   ```

5. The `provider_id` returned becomes part of the callback URI. Register it with your IdP.

6. Verify: visit `/api/sso/providers` — the new provider should appear. The login page will show the SSO button automatically.

---

## Deferred: SAML 2.0

SAML 2.0 support requires `python3-saml`, which depends on `libxml2` and `libxmlsec1` native C libraries. Render's default Python buildpack does not include these.

Options to enable SAML in a future PR:

- **Custom Render build command:** add an `apt-get install libxml2-dev libxmlsec1-dev` step
- **Docker deployment:** use a custom Dockerfile with the native libraries pre-installed

The `provider_type` column is already designed to accept `'saml'` as a value. The `blueprints/sso.py` and `repositories/sso_repository.py` schemas are forward-compatible.

---

## Tenant Admin Dashboard

The tenant admin dashboard (`/tenant-admin-dashboard.html`) mirrors the superadmin dashboard in layout and CSS, but all data is scoped to the `tenant_admin`'s tenant.

### Tabs

| Tab | Endpoint | Description |
|-----|----------|-------------|
| Overview | `GET /api/tenant-admin/overview` | Total users, active (30d), total classes, SSO providers, pending approvals |
| Analytics | `GET /api/tenant-admin/analytics` | Users by role, new/active counts, content totals, top audit actions |
| Users | `GET /api/tenant-admin/users` | Paginated user list; "Manage" button opens detail modal |
| Classes | `GET /api/tenant-admin/classes` | Paginated class list; transfer ownership or delete |
| SSO Config | `GET /api/sso/admin/providers` | List/create/edit/delete SSO providers for the tenant |
| Pending Approvals | `GET /api/tenant-admin/pending-approvals` | Approve or deny accounts waiting for access |
| Audit Log | `GET /api/tenant-admin/audit` | Events by all users in the tenant |

### Security properties

- `tenant_admin` **cannot** escalate any user to `superadmin` — the role picker in the modal is limited to `student`, `professor`, `tenant_admin`.
- Every mutation endpoint verifies the target user's `tenant_id` matches the requester's (ownership check).
- `tenant_admin` **cannot** impersonate another `tenant_admin` or `superadmin`.
- A `superadmin` can also use all `/api/tenant-admin/*` endpoints by appending `?tenant_id=<uuid>` — useful for remote support.
- All mutations emit audit events (reuses existing `audit()` helper).

### Tenant admin API routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/tenant-admin/overview` | High-level tenant stats |
| `GET` | `/api/tenant-admin/analytics` | Tenant-scoped usage metrics |
| `GET` | `/api/tenant-admin/users` | Paginated user search |
| `PATCH` | `/api/tenant-admin/users/<id>/status` | Enable/disable account |
| `PATCH` | `/api/tenant-admin/users/<id>/role` | Change role (student/professor/tenant_admin only) |
| `POST` | `/api/tenant-admin/users/<id>/force-reset` | Require password change on next login |
| `GET` | `/api/tenant-admin/users/<id>/export` | GDPR JSON export (file download) |
| `DELETE` | `/api/tenant-admin/users/<id>` | Cascade-delete user |
| `POST` | `/api/tenant-admin/users/<id>/impersonate` | 1-hr scoped impersonation token |
| `GET` | `/api/tenant-admin/pending-approvals` | Users with `account_status = 'pending_approval'` |
| `PATCH` | `/api/tenant-admin/users/<id>/approve` | Set status to `active` |
| `PATCH` | `/api/tenant-admin/users/<id>/deny` | Set status to `denied` |
| `GET` | `/api/tenant-admin/classes` | Paginated class list |
| `PATCH` | `/api/tenant-admin/classes/<id>/transfer` | Transfer to another professor in same tenant |
| `DELETE` | `/api/tenant-admin/classes/<id>` | Cascade-delete class |
| `GET` | `/api/tenant-admin/audit` | Audit events for tenant users |

SSO provider management is handled by the existing `/api/sso/admin/providers` routes (already tenant-scoped).

---

## Modified Files Reference

| File | Change |
|------|--------|
| `requirements.txt` | Added `authlib>=1.3.0` |
| `config.py` | Added `FEATURE_SSO`, `SSO_STATE_TTL`, `SSO_REDIRECT_BASE_URL` |
| `core/auth.py` | New `require_tenant_admin` decorator; `tenant_id` param in `create_jwt_token`; `g.tenant_id` set in `require_auth` |
| `repositories/auth_repository.py` | `get_user_by_email` returns 6-tuple including `tenant_id` |
| `blueprints/auth.py` | `signin()` passes `tenant_id` to JWT |
| `blueprints/superadmin.py` | `change_user_role` accepts `tenant_admin` + `tenant_id` body param |
| `app.py` | Registers `sso_bp` and `tenant_admin_bp` |
| `templates/login.html` | SSO divider + `#ssoSection` / `#ssoButtons` container |
| `static/js/auth.js` | `loadSSOProviders()`, `initSSOLogin()`, `handleSSOTokenParam()` |
