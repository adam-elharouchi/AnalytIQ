# LTI / LMS Deployment Walkthrough
> Delete this file once you've completed all 3 steps.

---

## Step 1 — Add these 3 env vars to Render

Go to your Render service → **Environment** → add each of these:

---

### LTI_PRIVATE_KEY
```
-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAqXtgNoEtB8jfmgo9fj/K0EsUy7Nm3osKBvTxSGkUX9g0e9Dl\nXQTlg54vuVdWIamxCoaATTlU/NYdToR0ks4f6kIyEI7AQBtbmWVt246bUZV0Ii8e\nUXAE3O2DZV14VKUoeK5KfLmIc0a0xDATQ9HuisHW1oTIrQ1ZG7X43/x5g7qe4R79\nyM6Swme/PfzFB33Zc8KRrdQsfmmlul3EfP6bBjVIIZBgAK6V6RDSrchoHBbne0dS\nlnU2QgUyzlQ8vs1U0CJRhQ5po9pqqTnsKoKnLfFd52/ft1o1g7gEONoGdUqhXAmN\nHRzQ6P3rH3lrpkOmxdzff37r8O5CYoac2aigJQIDAQABAoIBAAOaXxsBh4TLGS/T\n6GdC8WuYsQY8l+MCxzGLKwb8TuXTuZfpQrsFw+BWsFKLIAZirmQYJGmf3qXqYmCd\nMcI+NhD7m8dc1Yr3Wezqqll40GX9XKTuZgFatYvB0+GHiWuZQEFCiUxaAGPc/LJQ\nCFTQhXb3NHtGguKk7kBHz9TpL+ckO1pTa35k21TyLLqHcNMXuJsFbnV5y9Fp+RwU\nz0c5F8XFkdRUu+lYn6vsKhkcT71vK0lB4b1fIv63lUzVJmvTnTHb4REFN9jRmiYu\nRcgL+oNugW/PCxkyVwd3hxEtca6DLBHIM5qxervIHKVxS9Z/B6tZxTBBUP2J0kx9\nTv/738ECgYEA6gBYhPczutOmpt/9c/75AgSFwKJgpIwsHFka8C8wanLv2JtSQbVo\n+naC2WdybMYD+LDZmImXF9QNtZp4IS7sthuZ9JXRe2Le3+uAHVWPtyQ7zgK3/ji7\n6OyIW7tmQfshn+2dnPk5sbsG2rVEb+/e+yw64pvVGGeYcBZawHo/OsECgYEAuWpB\nwDDy8+XXbw5zj5d2bV7JJ2vHFIRav1guOt9ahjlzK0g3vBGR8v4XdKdSp+rsKx4v\nQTFRQiYEWREMtP3jGLcu8JcsPAQsSSOIqeMA5BxykORmf+3LUheodoUq2O01zn86\n8gr5gYamRr8y3VdUm7pxJqPnVcqBuFUnrsAs8mUCgYA/YkiX+73vZVVG7nVg7jfU\n7BSu0U0MRUvNgfViCeY7b1a4fZoSYmlFLsTSzsqX3CtHOeA3CU38DlyITIctteA4\nk9FoBwzvNyDX1pqlV3/OQ+pPKz1bh1KfDTMCZgiU5sl84IhI9NlD4z1AEMmw6HCl\n6J0qtLtMGQOZmPSMHpDyAQKBgBNQkVbfAoALwlxsSfd8VLbh99xmas+lVfq2yeIS\nIFD5LRkmJcAuqGCCvZjGUWLyovV+6HdHFuroIO3SS9uS0xRhCL/BT7dUy/Q2gmcI\nIbChkgGr+U18TQDZPBBUoPkGBOPk9xP9tq4ag7m88ySBk2vBiUX4LwIN3WOBY2fd\n1xDNAoGBAImGMc0bwpVut7FmUqF1hrlsfPXyTSBHpXJ6hmpyOyk/UvfCqo3dZAmX\nTpuW1pxLE9CNXk7JNeK85GosHTpn47JOT8AAp6igHJi6RUd6yiMNVEvgzjyU5u7X\nqlnml3z2aikmrgjmG2bV5kD68OVxLo3RtKXJxQryn71eHI8Sf9JV\n-----END RSA PRIVATE KEY-----\n
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
