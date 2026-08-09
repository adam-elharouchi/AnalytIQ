# CSRF Threat Model & Mitigation — JWT Bearer Authentication

**Status:** Current design. **Owner:** Security Engineering. **Last verified:** 2026-08-08.
**Audience:** Compliance packet reviewers, buyer technical diligence.

## 1. Claim

AnalytIQ's API is not exposed to Cross-Site Request Forgery (CSRF) despite having
CSRF auto-enforcement (`WTF_CSRF_CHECK_DEFAULT`) disabled application-wide. This is
a deliberate architectural position, not an oversight, and it holds because the
application has **no cookie-based ambient authentication** for the browser to
forge in the first place.

## 2. Threat Model

CSRF works when a browser automatically attaches an authentication credential
(typically a session cookie) to a request, regardless of which site initiated
that request. An attacker's page can then trigger a state-changing request
(`<form>` POST, `fetch()`, `<img>` GET) against the victim's session on another
origin, and the browser "helpfully" attaches the victim's cookie, authenticating
the forged request.

The attack requires two conditions simultaneously:
1. The server accepts an ambient, browser-attached credential (a cookie) as proof
   of identity.
2. That credential is attached automatically, without the attacking page needing
   to know its value.

## 3. Why AnalytIQ's Design Breaks Condition 1

Authentication is exclusively **JWT Bearer token via the `Authorization` HTTP
header**, verified in `require_auth()`:

- `core/auth.py:439-441` — the only code path that extracts an access token reads
  `request.headers.get("Authorization")` and requires a `Bearer ` prefix. There is
  no fallback to `request.cookies` anywhere in `require_auth()` or elsewhere in the
  codebase (`grep -rn "session\[" blueprints/ core/` returns zero matches; no route
  reads `request.cookies` for identity).
- The token is generated once (`core/auth.py:100-143`, `create_jwt_token`) and
  handed to the client in the HTTP response body (JSON on normal signin, an inline
  `<script>` payload on LTI launch — see §5), never via `Set-Cookie`. A full-repo
  search for `set_cookie`/`Set-Cookie` in `blueprints/` and `core/` returns no
  results — the backend never sets an authentication cookie.
- The frontend stores the token in `localStorage` and attaches it manually on every
  request: `static/js/api-client.js:23-24` (`localStorage.getItem('authToken')` →
  `headers['Authorization'] = 'Bearer ' + token`) and `static/js/auth.js:29-34`.
  `localStorage` is **not** sent automatically by the browser on cross-origin
  requests — a third-party page has no way to read it (Same-Origin Policy) and no
  way to make the victim's browser attach it.
- Flask's built-in cookie session (`flask.session`) is configured in `config.py:94-101`
  (`SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE`) but is **never populated** anywhere in
  the application (`session[...] = ...` does not occur in `blueprints/` or `core/`).
  It is inert configuration, not an active auth mechanism — see §6 for the
  recommended hygiene fix.

**Because there is no ambient, browser-attached credential, a forged cross-site
request arrives with no `Authorization` header and is rejected with 401 by
`require_auth` before any state-changing code runs.** This is true regardless of
whether `WTF_CSRF_CHECK_DEFAULT` is on or off — the CSRF-synchronizer-token
pattern exists specifically to protect cookie-authenticated endpoints, and there
are none here.

## 4. Why a Motivated Attacker Still Can't Forge the Header

Even setting aside condition 1, an attacker attempting to attach an `Authorization`
header via `fetch()`/XHR faces condition 2: the browser CORS preflight.
`Authorization` is a non-simple header, so any cross-origin request that sets it
triggers a mandatory `OPTIONS` preflight. `core/factory.py:279-300` handles this:
the server echoes `Access-Control-Allow-Origin` only for allow-listed origins
(`config.CORS_ORIGINS`, empty by default in production — `config.py:129-130`,
same-origin only) and always sends
`Access-Control-Allow-Credentials: false` (`core/factory.py:300`). Even in the
permissive non-production default (`CORS_ORIGINS = "*"`), the attacker still does
not know the victim's token value — it lives only in the victim's `localStorage`
on the AnalytIQ origin — so there is nothing valid to put in the forged header.
CORS misconfiguration is a distinct risk category (see gap table) but it does not
resurrect CSRF here.

## 5. The LTI Iframe Case

LTI 1.3 launches AnalytIQ inside a third-party LMS iframe, which is exactly the
context where cookie-based CSRF defenses (`SameSite=Lax/Strict`) break down and
where browsers increasingly block third-party cookies outright. AnalytIQ's LTI
implementation was built cookie-free by design, which sidesteps that fragility
rather than fighting it:

- `blueprints/lti.py:44-97` — LTI launch/OIDC state is stored server-side in
  Redis, not in a cookie. `get_session_cookie_name()` is overridden to return
  `None` (`blueprints/lti.py:65-68`), with an explicit comment: "cookies are
  blocked anyway when AnalytIQ is embedded in an LMS iframe."
- After a successful launch, `_upsert_lti_user()` mints a JWT
  (`blueprints/lti.py:249-256`) exactly like normal signin. `lti_launch()` renders
  `templates/lti-launch.html`, which writes that token into `localStorage` via
  inline JS (`templates/lti-launch.html:72-73`) — the identical mechanism used by
  the non-LTI login flow.
- All post-launch, state-changing LTI endpoints (`lti_setup`, `create_lti_config`,
  `link_class`, `toggle_ags`, `sync_roster`, `submit_grade`, etc. —
  `blueprints/lti.py:630-1012`) are gated by the same `@require_auth` Bearer-token
  check as every other endpoint in the app. There is no separate, weaker,
  cookie-based trust path for LTI-originated sessions.
- The LTI launch endpoint itself (`POST /lti/launch`) is intentionally
  unauthenticated — the LMS platform, not a logged-in AnalytIQ user, POSTs the
  `id_token` there. That is correct per the LTI 1.3 / OIDC spec, and forgery of
  that POST is defended by the spec's own state/nonce validation
  (`pylti1p3`, Redis-backed — `blueprints/lti.py:44-97`), which is a different
  control from application-level CSRF and out of scope for this memo.

**Net effect: the LTI iframe constraint does not weaken this analysis — it is the
reason the app never introduced cookie-based auth to begin with.**

## 6. Residual Risk (stated honestly)

- **XSS, not CSRF, is the live threat to this token.** Because the JWT lives in
  `localStorage`, any successful script injection can read and exfiltrate it
  directly — a strictly worse outcome than a forged request, and one CSRF tokens
  would not have prevented either. This app's primary defense against that is CSP.
  `CSP_ENFORCE` defaults to `False` (`config.py:230`). The **enforced**
  `Content-Security-Policy` header always carries `object-src 'none'; base-uri
  'self'`, and only adds the nonce-based `script-src` when `CSP_ENFORCE=True`
  (`core/factory.py:355-359`). Everything else — `default-src`, `style-src`,
  `img-src`, `connect-src`, `font-src`, `frame-ancestors` — currently ships only
  in `Content-Security-Policy-Report-Only`, i.e. monitored, not blocked
  (`core/factory.py:361-374`). Verify the live `CSP_ENFORCE` value in the
  production Render environment before stating "script-src CSP enforced" in the
  compliance packet, and do not describe `frame-ancestors`/`default-src` as
  enforced — this memo does not check that runtime value and the code shows
  those directives are report-only today.
- **`WTF_CSRF_ENABLED`/`FEATURE_CSRF_PROTECTION` is cosmetic today.** It defaults to
  `True` (`config.py:194`) and initializes `CSRFProtect` (`core/factory.py:163-167`),
  but `WTF_CSRF_CHECK_DEFAULT` is hard-coded `False` regardless
  (`core/factory.py:161`), and every mutating route additionally carries an
  explicit `@csrf_exempt` decorator. No route is actually protected by
  `CSRFProtect` today. The extension is wired up only so `generate_csrf()` /
  `GET /api/csrf-token` work if a future traditional form-submit route needs
  explicit `@csrf.protect`.
- **Dead `SESSION_COOKIE_*` config is a hygiene risk, not a vulnerability.**
  `config.py:94-101` configures Flask's session cookie (including
  `SameSite=None` in production) as if it were in use. It is not. Left as-is, it
  could mislead a future contributor into believing cookie-based auth exists, or
  into building a new feature on top of `flask.session` without realizing it
  carries no current CSRF protection. Recommend either removing the unused
  config or adding a code comment cross-referencing this memo (tracked as a gap
  in the audit; not fixed here since fixes require Adam's approval).
- **This analysis is invalidated the moment any endpoint accepts a cookie as an
  authentication credential** (e.g., a future "remember me" cookie, a third-party
  SSO cookie bridge, or a session cookie fallback for browsers that block
  `localStorage`). Any such change must trigger a re-review of this memo before
  shipping.

## 7. Compensating Controls Already in Place

- Token revocation via `token_version` checked on every request
  (`core/auth.py:518-520`), so compromised tokens can be invalidated without
  waiting for expiry.
- Short access-token TTL (24h default, `config.py:109`) with a separate,
  narrowly-scoped refresh token that is never accepted by `require_auth`
  (`core/auth.py:146-160`, `core/auth.py:449-450`).
- Rate limiting on auth-sensitive endpoints (`docs/SECURITY.md:42-56`).
- `Access-Control-Allow-Credentials: false` sent on every `/api/*` response
  (`core/factory.py:300`), closing off the one CORS pathway that could otherwise
  matter if a cookie-based credential were ever introduced.

## 8. Verdict

**No code change required to close a CSRF gap, because there is no CSRF-exploitable
surface under the current cookie-free, header-only JWT design.** The
recommendation is to ship this memo as the compliance-packet answer rather than
implement a synchronizer-token/double-submit-cookie scheme (see
`reports/security-engineer/2026-08-08.md` §"Needs Adam" for the full Path A vs.
Path B trade-off write-up).
