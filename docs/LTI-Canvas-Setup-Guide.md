# LTI 1.3 Canvas Setup Guide

Step-by-step guide for registering AnalytIQ as an LTI 1.3 tool in a Canvas sandbox
and verifying AGS grade passback end-to-end.

---

## Prerequisites

| What | Where |
|---|---|
| AnalytIQ dev instance (HTTPS required) | e.g. `https://your-ngrok-or-render-url.com` |
| Canvas sandbox account | [canvas.instructure.com](https://canvas.instructure.com) — free |
| Superadmin AnalytIQ account | Signed up with `@myanalytiq.org` email |

> **Local dev tip:** Canvas requires HTTPS. Use `ngrok http 5000` to expose your local
> server, or test against your Render staging deployment.

---

## Step 1 — Get the AnalytIQ Tool Endpoints

Call the tool-info endpoint (no auth required):

```bash
GET https://<your-analytiq>/lti/tool-info
```

You'll get back:

```json
{
  "oidc_initiation_url": "https://<your-analytiq>/lti/login",
  "target_link_uri":     "https://<your-analytiq>/lti/launch",
  "jwks_url":            "https://<your-analytiq>/lti/jwks",
  "deep_link_url":       "https://<your-analytiq>/lti/deep-link/return"
}
```

Keep this open — you'll copy these into Canvas.

---

## Step 2 — Register the Tool in Canvas

1. Log in to your Canvas sandbox as an admin.
2. Go to **Admin → Developer Keys → + Developer Key → LTI Key**.
3. Fill in:

| Canvas Field | Value |
|---|---|
| **Key Name** | AnalytIQ (any label) |
| **Redirect URIs** | `https://<your-analytiq>/lti/launch` |
| **Method** | Manual Entry |
| **Title** | AnalytIQ |
| **Description** | (optional) |
| **Target Link URI** | `https://<your-analytiq>/lti/launch` |
| **OpenID Connect Initiation Url** | `https://<your-analytiq>/lti/login` |
| **JWK Method** | Public JWK URL |
| **Public JWK URL** | `https://<your-analytiq>/lti/jwks` |

4. Under **LTI Advantage Services**, enable:
   - ✅ Can retrieve user data associated with the context in which the tool is installed
   - ✅ Can create and view assignment data in the gradebook associated with the tool
   - ✅ Can view submission data for assignments associated with the tool
   - ✅ Can create and update submission results for assignments associated with the tool
   - ✅ Can retrieve user data associated with the context the tool is installed in (for NRPS)

5. Click **Save** → note the **Client ID** shown (a long number like `170000000000042`).
6. Set the key state to **ON**.

---

## Step 3 — Install the Tool in a Course

1. Go to your Canvas course → **Settings → Apps → + App**.
2. Choose **Configuration Type: By Client ID**.
3. Enter the Client ID from Step 2 → **Submit** → **Install**.

---

## Step 4 — Register Canvas in AnalytIQ

Use the AnalytIQ LTI config endpoint as a superadmin:

```bash
POST https://<your-analytiq>/api/lti/config
Authorization: Bearer <your-superadmin-jwt>
Content-Type: application/json

{
  "issuer":            "https://canvas.instructure.com",
  "client_id":         "170000000000042",
  "auth_login_url":    "https://sso.canvaslms.com/api/lti/authorize_redirect",
  "auth_token_url":    "https://sso.canvaslms.com/api/lti/token",
  "key_set_url":       "https://sso.canvaslms.com/api/lti/security/jwks",
  "private_key_file":  "lti_private_key.pem",
  "public_key_file":   "lti_public_key.pem",
  "deployment_id":     "1"
}
```

> **deployment_id:** Canvas shows this under the installed app's settings — it's
> typically `"1"` for the first deployment in a course.

Expected response:
```json
{ "success": true, "config_id": "<uuid>" }
```

---

## Step 5 — Do an LTI Launch

1. In Canvas, go to your course **Modules** or **Assignments**.
2. Add an **External Tool** assignment pointing to your AnalytIQ tool.
3. Click the assignment to trigger an LTI launch.
4. AnalytIQ will:
   - Create or link your Canvas user account via `lti_sub`
   - Auto-enroll you in the class
   - Store the `ags_lineitems_url` on the class

You can verify the class was linked:
```bash
GET https://<your-analytiq>/api/lti/config
Authorization: Bearer <professor-jwt>
```

---

## Step 6 — Link an AnalytIQ Class (if not auto-linked)

If the professor created the class manually before the LTI launch:

```bash
POST https://<your-analytiq>/api/lti/link-class/<class_id>
Authorization: Bearer <professor-jwt>
Content-Type: application/json

{
  "lti_context_id": "<canvas-course-context-id>",
  "issuer":         "https://canvas.instructure.com",
  "nrps_url":       "https://canvas.instructure.com/api/lti/courses/.../names_and_roles",
  "ags_url":        "https://canvas.instructure.com/api/lti/courses/.../line_items"
}
```

---

## Step 7 — Enable AGS Grade Passback

```bash
PUT https://<your-analytiq>/api/lti/ags-toggle/<class_id>
Authorization: Bearer <professor-jwt>
Content-Type: application/json

{ "enabled": true }
```

Expected: `{ "success": true }`

---

## Step 8 — Submit an Exercise and Verify Passback

1. Log in as a student (use the Canvas LTI launch, so `lti_sub` is populated).
2. Submit code to any exercise in the class:

```bash
POST https://<your-analytiq>/api/exercises/<exercise_id>/grade
Authorization: Bearer <student-jwt>
Content-Type: application/json

{ "code": "def solution(a, b): return a + b" }
```

3. Check the Canvas gradebook — the score should appear within a few seconds.
4. Check AnalytIQ logs for:
   ```
   AGS grade pushed: exercise=<id> class=<id> score=<n>
   ```

If passback fails silently, the log will show:
```
AGS passback skipped for <exercise_id>: <reason>
```

---

## Step 9 — Sync the Roster (optional)

To pull all Canvas-enrolled students into AnalytIQ:

```bash
POST https://<your-analytiq>/api/lti/sync-roster/<class_id>
Authorization: Bearer <professor-jwt>
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Launch fails with "invalid JWT" | JWKS URL unreachable from Canvas | Ensure `/lti/jwks` is publicly accessible |
| Grade doesn't appear in Canvas | `ags_enabled=False` or student has no `lti_sub` | Enable AGS (Step 7); student must launch via LTI first |
| "LTI tool not configured" error | No LTI config registered for the issuer | Repeat Step 4 |
| Canvas shows `401` on launch | Wrong `client_id` or `deployment_id` | Re-check Step 4 values |
| `ags_lineitems_url` is NULL | Class was linked before the LTI launch stored the AGS URL | Re-link with `POST /api/lti/link-class/<id>` |

---

## Canvas Sandbox URLs (instructure.com)

| Endpoint | URL |
|---|---|
| Issuer | `https://canvas.instructure.com` |
| OIDC Auth | `https://sso.canvaslms.com/api/lti/authorize_redirect` |
| Token URL | `https://sso.canvaslms.com/api/lti/token` |
| JWKS | `https://sso.canvaslms.com/api/lti/security/jwks` |
