# LTI / LMS Deployment Walkthrough
> Delete this file once you've completed all 3 steps.

---

## Step 1 — Add these 3 env vars to Render

Go to your Render service → **Environment** → add each of these:

---

### LTI_PRIVATE_KEY
```
REDACTED_RSA_PRIVATE_KEY\n
```
Paste the entire string above (including the `-----BEGIN...` and `-----END...` parts) as the value.

---

### LTI_PUBLIC_KEY
```
-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqXtgNoEtB8jfmgo9fj/K\n0EsUy7Nm3osKBvTxSGkUX9g0e9DlXQTlg54vuVdWIamxCoaATTlU/NYdToR0ks4f\n6kIyEI7AQBtbmWVt246bUZV0Ii8eUXAE3O2DZV14VKUoeK5KfLmIc0a0xDATQ9Hu\nisHW1oTIrQ1ZG7X43/x5g7qe4R79yM6Swme/PfzFB33Zc8KRrdQsfmmlul3EfP6b\nBjVIIZBgAK6V6RDSrchoHBbne0dSlnU2QgUyzlQ8vs1U0CJRhQ5po9pqqTnsKoKn\nLfFd52/ft1o1g7gEONoGdUqhXAmNHRzQ6P3rH3lrpkOmxdzff37r8O5CYoac2aig\nJQIDAQAB\n-----END PUBLIC KEY-----\n
```

---

### LTI_TOOL_URL
```
https://myanalytiq.org
```

---

## Step 2 — Run the DB migration in Supabase

1. Go to your Supabase project → **SQL Editor**
2. Paste and run the entire contents of `migrations/001_lti_tables.sql`
3. It's safe to run multiple times (all statements use `IF NOT EXISTS` / `IF NOT EXISTS`)

What it does:
- Creates `lti_configurations` table (stores Canvas/Moodle platform registrations)
- Creates `lti_sessions` table (stores LTI launch sessions)
- Adds `lti_sub`, `lti_issuer` columns to `users` (allows NULL password for LTI-only accounts)
- Adds `lti_context_id`, `nrps_context_url`, `ags_enabled`, `ags_lineitems_url` to `classes`

---

## Step 3 — Register AnalytIQ in your LMS (Canvas / Moodle / etc.)

After Render deploys, sign in as a professor and go to:
**https://myanalytiq.org/lti-setup.html** → **Tool Info** tab

The URLs you'll need to paste into your LMS:

| LMS field name | Value |
|----------------|-------|
| JWKS URL / Public Keyset URL | `https://myanalytiq.org/lti/jwks` |
| Login Initiation URL / OIDC Auth Request URL | `https://myanalytiq.org/lti/login` |
| Launch URL / Redirect URI / Target Link URI | `https://myanalytiq.org/lti/launch` |
| Deep Linking URL (if asked separately) | `https://myanalytiq.org/lti/launch` |

### After registering in the LMS:
The LMS will give you a **Client ID** and your institution's **Issuer URL**.
Go to the **Register Platform** tab in the LTI Setup page and enter:
- Platform Name (e.g. "Canvas HULT")
- Issuer (e.g. `https://canvas.instructure.com`)
- Client ID (from the LMS)
- Auth Login URL (from the LMS)
- Auth Token URL (from the LMS)
- Key Set URL / JWKS URL (from the LMS — their public key, not ours)

---

## Done — delete this file
```
git rm LTI_DEPLOY.md && git commit -m "Remove LTI deployment walkthrough"
```
