"""
SSO blueprint — OAuth2/OIDC sign-in for tenants.

Public routes (no auth required):
  GET  /api/sso/providers                     — list enabled providers for login page
  GET  /api/sso/init/<provider_id>            — begin OAuth2 flow; returns redirect URL
  GET  /api/sso/callback/<provider_id>        — OAuth2 callback; issues JWT, redirects to login page

Admin routes (tenant_admin or superadmin):
  GET    /api/sso/admin/providers             — list providers for caller's tenant
  POST   /api/sso/admin/providers             — create provider config
  PUT    /api/sso/admin/providers/<id>        — update provider config
  DELETE /api/sso/admin/providers/<id>        — remove provider config

SAML 2.0 is intentionally deferred (requires native libxmlsec1 — not available on Render's
default buildpack). The provider_type column accepts 'saml' for future use.
"""

import base64
import hashlib
import json
import logging
import secrets
import uuid
from urllib.parse import urlencode
from typing import Optional

import requests as http_client
from cryptography.fernet import Fernet, InvalidToken
from flask import Blueprint, g, jsonify, redirect, request

import config
from core.audit import audit
from core.auth import (
    create_jwt_token,
    create_refresh_token,
    get_user_token_version,
    require_auth,
    require_tenant_admin,
)
from core.database import get_db_connection
from core.extensions import csrf_exempt, limiter
from repositories import auth_repository as auth_repo
from repositories import sso_repository as sso_repo

logger = logging.getLogger(__name__)
bp = Blueprint("sso", __name__)

# In-memory cache for OIDC discovery documents (keyed by discovery_url).
# These documents are stable and rarely change; a process restart resets the cache.
_OIDC_DISCOVERY_CACHE: dict = {}

# Canonical Google discovery URL for pre-validation
_GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
# Microsoft v2.0 template (tenant_id = 'common' works for multi-tenant apps)
_MICROSOFT_DISCOVERY_TEMPLATE = (
    "https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"
)

_VALID_PROVIDER_TYPES = {"google", "microsoft", "oidc"}


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------


def _get_fernet() -> Fernet:
    """Derive the Fernet cipher for stored SSO client secrets.

    Uses the dedicated SSO_ENCRYPTION_KEY when set, otherwise falls back to
    SECRET_KEY (backward compatible — existing ciphertext still decrypts). Set a
    distinct SSO_ENCRYPTION_KEY so rotating SECRET_KEY/JWT_SECRET_KEY does not
    invalidate stored SSO secrets. Changing SSO_ENCRYPTION_KEY requires
    re-entering each provider's client secret.
    """
    key_source = config.SSO_ENCRYPTION_KEY or config.SECRET_KEY
    key_bytes = hashlib.sha256(key_source.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def _decrypt_secret(ciphertext: str) -> str:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Failed to decrypt client secret — SECRET_KEY may have changed.")


# ---------------------------------------------------------------------------
# OIDC discovery
# ---------------------------------------------------------------------------


def _fetch_oidc_discovery(discovery_url: str) -> dict:
    """Fetch (and in-process cache) an OIDC discovery document."""
    if discovery_url not in _OIDC_DISCOVERY_CACHE:
        resp = http_client.get(discovery_url, timeout=10)
        resp.raise_for_status()
        _OIDC_DISCOVERY_CACHE[discovery_url] = resp.json()
    return _OIDC_DISCOVERY_CACHE[discovery_url]


def _discovery_url_for_provider(provider: dict) -> str:
    """Resolve the OIDC discovery URL for well-known provider types."""
    ptype = provider["provider_type"]
    if ptype == "google":
        return _GOOGLE_DISCOVERY_URL
    if ptype == "microsoft":
        # discovery_url field stores the Azure AD tenant ID or full URL
        raw = provider["discovery_url"]
        if raw.startswith("http"):
            return raw
        # If it's just a tenant ID/domain, expand it
        return _MICROSOFT_DISCOVERY_TEMPLATE.format(tenant=raw)
    # generic oidc — discovery_url is the full URL
    return provider["discovery_url"]


def _verify_id_token(
    id_token: str, jwks_uri: str, client_id: str, issuer: Optional[str] = None
) -> dict:
    """Verify an OIDC id_token's signature (via the provider JWKS) and claims.

    Enforces audience == client_id, expiry, and (when known) issuer. Raises on
    any verification failure so the caller can reject the login.
    """
    import jwt as pyjwt
    from jwt import PyJWKClient

    signing_key = PyJWKClient(jwks_uri).get_signing_key_from_jwt(id_token)
    decode_kwargs = {
        "algorithms": ["RS256", "RS384", "RS512", "ES256"],
        "audience": client_id,
        "options": {"require": ["exp", "iat"]},
    }
    if issuer:
        decode_kwargs["issuer"] = issuer
    return pyjwt.decode(id_token, signing_key.key, **decode_kwargs)


# ---------------------------------------------------------------------------
# OAuth2 state management (Redis)
# ---------------------------------------------------------------------------


def _store_state(state: str, data: dict) -> None:
    """Persist OAuth2 state in Redis with TTL. Falls back gracefully if Redis unavailable."""
    try:
        from core.cache import redis_client

        if redis_client:
            redis_client.setex(
                f"sso_state:{state}",
                config.SSO_STATE_TTL,
                json.dumps(data),
            )
    except Exception as exc:
        logger.warning("Could not store SSO state in Redis: %s", exc)


def _pop_state(state: str) -> Optional[dict]:
    """Retrieve and atomically delete OAuth2 state from Redis."""
    try:
        from core.cache import redis_client

        if redis_client:
            key = f"sso_state:{state}"
            raw = redis_client.get(key)
            if raw:
                redis_client.delete(key)
                return json.loads(raw)
    except Exception as exc:
        logger.warning("Could not retrieve SSO state from Redis: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Tenant access guard (for admin routes)
# ---------------------------------------------------------------------------


def _can_manage_tenant(tenant_id: str) -> bool:
    """Return True if the current user may manage the given tenant's SSO config."""
    if g.user_role == "superadmin":
        return True
    if g.user_role == "tenant_admin":
        return getattr(g, "tenant_id", None) == tenant_id
    return False


# ---------------------------------------------------------------------------
# User upsert
# ---------------------------------------------------------------------------


def _map_role(claims: dict, provider: dict) -> str:
    """Map OIDC token claims to an AnalytIQ role using the provider's role_mapping config."""
    attr = provider.get("role_mapping_attribute") or ""
    claim_value = str(claims.get(attr, "")) if attr else ""
    mapping: dict = provider.get("role_mapping") or {}

    if claim_value and mapping:
        # Exact match first
        if claim_value in mapping:
            return mapping[claim_value]
        # Substring match (e.g. "Staff Member" → key "Staff")
        for k, v in mapping.items():
            if k in claim_value:
                return v

    return provider.get("default_role") or "student"


def _callback_uri(provider_id: str) -> str:
    base = config.SSO_REDIRECT_BASE_URL.rstrip("/")
    return f"{base}/api/sso/callback/{provider_id}"


def _upsert_sso_user(conn, provider: dict, claims: dict):
    """
    Find or create a user from OIDC id_token/userinfo claims.

    Resolution order (mirrors LTI user upsert in blueprints/lti.py):
      1. Existing user matched by (sso_provider_id, sso_subject)
      2. Existing user matched by email → link SSO identity
      3. Create new user (password_hash = NULL, SSO-only account)

    Returns (user_id, name, email, role, tenant_id).
    """
    # Microsoft uses 'oid' as the stable subject; fall back to 'sub'
    sub = claims.get("sub") or claims.get("oid")
    email = (claims.get("email") or claims.get("preferred_username") or "").lower().strip()
    name = (claims.get("name") or email.split("@")[0]).strip()

    if not sub or not email:
        raise ValueError("OIDC claims are missing required 'sub'/'oid' or 'email' fields.")

    provider_id = provider["provider_id"]
    tenant_id = provider["tenant_id"]

    # Domain allowlist check
    allowed_domains: list = provider.get("allowed_domains") or []
    if allowed_domains:
        domain = email.split("@")[1] if "@" in email else ""
        if domain not in allowed_domains:
            raise PermissionError(
                f"Email domain '{domain}' is not permitted for this SSO provider."
            )

    role = _map_role(claims, provider)

    # 1. Lookup by SSO identity
    existing = sso_repo.get_user_by_sso_identity(conn, provider_id, sub)
    if existing:
        return existing[0], existing[1], existing[2], existing[3], tenant_id

    # 2. Lookup by email — link SSO identity to existing account
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, name, email, COALESCE(role, 'student') FROM users WHERE email = %s",
        (email,),
    )
    email_user = cur.fetchone()
    cur.close()

    if email_user:
        # SECURITY: never federate an SSO identity into a privileged account via
        # an email-claim match — that would let an IdP login mint an admin
        # session for a matching email. Privileged users must sign in directly.
        if email_user[3] in ("superadmin", "tenant_admin"):
            raise PermissionError(
                "This email is associated with a privileged account that cannot "
                "be accessed via SSO."
            )
        # Only auto-link to a pre-existing account when the IdP asserts the email
        # is verified — otherwise an attacker with an unverified same-email IdP
        # account could take over the existing account.
        if claims.get("email_verified") not in (True, "true", "True", 1):
            raise PermissionError(
                "An account with this email already exists but the identity "
                "provider did not confirm the email is verified. Automatic "
                "linking was refused; sign in with your password instead."
            )
        user_id = email_user[0]
        sso_repo.link_sso_identity(conn, user_id, provider_id, sub)
        return user_id, email_user[1], email_user[2], email_user[3], tenant_id

    # 3. Create new SSO-only user
    new_user_id = str(uuid.uuid4())
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users
            (user_id, name, email, password_hash, role, tenant_id, sso_provider_id, sso_subject)
        VALUES (%s, %s, %s, NULL, %s, %s, %s, %s)
        RETURNING user_id, name, email, COALESCE(role, 'student')
        """,
        (new_user_id, name, email, role, tenant_id, provider_id, sub),
    )
    row = cur.fetchone()
    cur.close()

    # Companion rows — mirror auth.py signup pattern
    for fn_name in (
        "create_default_profile",
        "create_default_settings",
        "create_default_preferences",
        "create_default_ai_digest",
    ):
        try:
            getattr(auth_repo, fn_name)(conn, new_user_id)
        except Exception as exc:
            logger.warning("Failed to create %s for SSO user: %s", fn_name, exc)

    audit(
        conn,
        "SSO_CREATE_USER",
        resource_type="user",
        resource_id=new_user_id,
        details={"provider_id": provider_id, "role": role, "tenant_id": tenant_id},
    )

    return row[0], row[1], row[2], row[3], tenant_id


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------


@bp.route("/api/sso/providers", methods=["GET"])
@csrf_exempt
def list_public_providers():
    """Return enabled SSO providers (safe fields only) for the login page."""
    if not config.FEATURE_SSO:
        return jsonify({"providers": []}), 200

    try:
        conn = get_db_connection()
        providers = sso_repo.get_enabled_providers(conn)
        return jsonify({"providers": providers}), 200
    except Exception as exc:
        logger.error("Failed to list SSO providers: %s", exc, exc_info=True)
        return jsonify({"providers": []}), 200  # fail open — don't break login page


@bp.route("/api/sso/init/<provider_id>", methods=["GET"])
@csrf_exempt
@limiter.limit("30 per minute")
def sso_init(provider_id):
    """
    Begin the OAuth2/OIDC authorization code flow.

    Returns JSON: {"auth_url": "<IdP authorization endpoint + params>"}
    The frontend redirects the browser to auth_url.
    """
    if not config.FEATURE_SSO:
        return jsonify({"error": "SSO is not enabled"}), 404

    try:
        conn = get_db_connection()
        provider = sso_repo.get_provider_by_id(conn, provider_id)
        if not provider or not provider["is_enabled"]:
            return jsonify({"error": "SSO provider not found or disabled"}), 404

        discovery = _fetch_oidc_discovery(_discovery_url_for_provider(provider))
        auth_endpoint = discovery["authorization_endpoint"]

        state = secrets.token_urlsafe(32)
        _store_state(state, {"provider_id": provider_id})

        params = {
            "response_type": "code",
            "client_id": provider["client_id"],
            "redirect_uri": _callback_uri(provider_id),
            "scope": "openid email profile",
            "state": state,
        }
        auth_url = f"{auth_endpoint}?{urlencode(params)}"

        return jsonify({"auth_url": auth_url}), 200

    except Exception as exc:
        logger.error("SSO init error for provider %s: %s", provider_id, exc, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/sso/callback/<provider_id>", methods=["GET"])
@csrf_exempt
def sso_callback(provider_id):
    """
    OAuth2 callback — the IdP redirects here after the user authenticates.

    On success: redirect to {FRONTEND_URL}/login.html?sso_token=<jwt>
    On error:   redirect to {FRONTEND_URL}/login.html?sso_error=<message>
    """
    frontend_base = config.SSO_REDIRECT_BASE_URL.rstrip("/")
    login_page = f"{frontend_base}/login.html"

    if not config.FEATURE_SSO:
        return redirect(f"{login_page}?sso_error=SSO+is+not+enabled")

    error = request.args.get("error")
    if error:
        desc = request.args.get("error_description", error)
        logger.warning("IdP returned error for provider %s: %s", provider_id, desc)
        return redirect(f"{login_page}?sso_error={desc}")

    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state:
        return redirect(f"{login_page}?sso_error=Missing+code+or+state+parameter")

    # Verify state
    state_data = _pop_state(state)
    if not state_data or state_data.get("provider_id") != provider_id:
        return redirect(f"{login_page}?sso_error=Invalid+or+expired+state+parameter")

    conn = None
    try:
        conn = get_db_connection()
        provider = sso_repo.get_provider_by_id(conn, provider_id)
        if not provider or not provider["is_enabled"]:
            return redirect(f"{login_page}?sso_error=SSO+provider+not+found+or+disabled")

        client_secret = _decrypt_secret(provider["client_secret"])
        discovery_url = _discovery_url_for_provider(provider)
        discovery = _fetch_oidc_discovery(discovery_url)
        token_endpoint = discovery["token_endpoint"]
        userinfo_endpoint = discovery.get("userinfo_endpoint")

        # Exchange authorization code for tokens
        token_resp = http_client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _callback_uri(provider_id),
                "client_id": provider["client_id"],
                "client_secret": client_secret,
            },
            timeout=15,
        )
        if not token_resp.ok:
            logger.error("Token exchange failed for provider %s: %s", provider_id, token_resp.text)
            return redirect(f"{login_page}?sso_error=Token+exchange+failed")

        tokens = token_resp.json()
        access_token = tokens.get("access_token", "")
        id_token = tokens.get("id_token", "")

        # Identity comes from the id_token, whose signature and claims we verify
        # against the provider's JWKS. An unverified id_token is never trusted.
        claims: dict = {}
        if id_token:
            jwks_uri = discovery.get("jwks_uri")
            if not jwks_uri:
                logger.error("Provider %s exposes no jwks_uri; cannot verify id_token", provider_id)
                return redirect(f"{login_page}?sso_error=Provider+identity+cannot+be+verified")
            try:
                claims = _verify_id_token(
                    id_token, jwks_uri, provider["client_id"], discovery.get("issuer")
                )
            except Exception as exc:
                logger.warning("id_token verification failed for %s: %s", provider_id, exc)
                return redirect(f"{login_page}?sso_error=Identity+verification+failed")

        # userinfo (fetched over TLS with the access token) only *supplements*
        # missing profile fields; it never overrides a verified id_token claim.
        if userinfo_endpoint and access_token:
            try:
                ui_resp = http_client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
                if ui_resp.ok:
                    for _k, _v in ui_resp.json().items():
                        claims.setdefault(_k, _v)
            except Exception as exc:
                logger.debug("userinfo fetch failed for %s: %s", provider_id, exc)

        if not claims.get("sub"):
            return redirect(f"{login_page}?sso_error=Could+not+establish+a+verified+identity")

        user_id, name, email, role, tenant_id = _upsert_sso_user(conn, provider, claims)
        conn.commit()

        _tv = get_user_token_version(conn, user_id)
        token = create_jwt_token(
            user_id,
            role=role,
            name=name,
            email=email,
            tenant_id=tenant_id,
            token_version=_tv,
        )
        refresh = create_refresh_token(user_id, token_version=_tv)
        return redirect(f"{login_page}?sso_token={token}&sso_refresh={refresh}")

    except PermissionError as exc:
        logger.warning("SSO domain restriction for provider %s: %s", provider_id, exc)
        return redirect(
            f"{login_page}?sso_error=Your+email+domain+is+not+allowed+for+this+provider"
        )
    except Exception as exc:
        if conn:
            conn.rollback()
        logger.error("SSO callback error for provider %s: %s", provider_id, exc, exc_info=True)
        return redirect(f"{login_page}?sso_error=An+unexpected+error+occurred.+Please+try+again.")


# ---------------------------------------------------------------------------
# Admin routes (tenant_admin or superadmin)
# ---------------------------------------------------------------------------


@bp.route("/api/sso/admin/providers", methods=["GET"])
@require_auth
@require_tenant_admin
def admin_list_providers():
    """List SSO providers visible to the current admin."""
    try:
        conn = get_db_connection()

        if g.user_role == "superadmin":
            # Superadmin may pass ?tenant_id= to filter
            tenant_id = request.args.get("tenant_id")
            if tenant_id:
                providers = sso_repo.get_providers_for_tenant(conn, tenant_id)
            else:
                # Return providers for all tenants
                cur = conn.cursor()
                cur.execute("SELECT tenant_id FROM tenants WHERE is_active = true")
                all_tenant_ids = [r[0] for r in cur.fetchall()]
                cur.close()
                providers = []
                for tid in all_tenant_ids:
                    providers.extend(sso_repo.get_providers_for_tenant(conn, tid))
        else:
            # tenant_admin — scoped to their own tenant
            tenant_id = g.tenant_id
            if not tenant_id:
                return jsonify({"error": "No tenant associated with your account"}), 400
            providers = sso_repo.get_providers_for_tenant(conn, tenant_id)

        return jsonify({"providers": providers}), 200

    except Exception as exc:
        logger.error("Failed to list admin SSO providers: %s", exc, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/sso/admin/providers", methods=["POST"])
@csrf_exempt
@require_auth
@require_tenant_admin
@limiter.limit("20 per hour")
def admin_create_provider():
    """Create a new SSO provider configuration for a tenant."""
    data = request.json or {}

    provider_name = data.get("provider_name", "").strip()
    provider_type = data.get("provider_type", "").strip().lower()
    tenant_id = data.get("tenant_id") or getattr(g, "tenant_id", None)
    client_id = data.get("client_id", "").strip()
    client_secret = data.get("client_secret", "").strip()
    discovery_url = data.get("discovery_url", "").strip()
    allowed_domains = data.get("allowed_domains") or []
    role_mapping_attribute = data.get("role_mapping_attribute", "").strip() or None
    role_mapping = data.get("role_mapping") or {}
    default_role = data.get("default_role", "student").strip()

    # Validation
    if not provider_name:
        return jsonify({"error": "provider_name is required"}), 400
    if provider_type not in _VALID_PROVIDER_TYPES:
        return (
            jsonify(
                {
                    "error": f"provider_type must be one of: {', '.join(sorted(_VALID_PROVIDER_TYPES))}"
                }
            ),
            400,
        )
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400
    if not client_id or not client_secret:
        return jsonify({"error": "client_id and client_secret are required"}), 400
    if provider_type == "oidc" and not discovery_url:
        return jsonify({"error": "discovery_url is required for generic OIDC providers"}), 400
    if default_role not in ("student", "professor", "tenant_admin"):
        return jsonify({"error": "default_role must be student, professor, or tenant_admin"}), 400

    if not _can_manage_tenant(tenant_id):
        return jsonify({"error": "Forbidden: you cannot manage SSO for this tenant"}), 403

    try:
        conn = get_db_connection()

        # Resolve discovery_url for well-known types
        if provider_type == "google":
            resolved_discovery = _GOOGLE_DISCOVERY_URL
        elif provider_type == "microsoft":
            resolved_discovery = discovery_url or _MICROSOFT_DISCOVERY_TEMPLATE.format(
                tenant="common"
            )
        else:
            resolved_discovery = discovery_url

        # Verify the discovery URL is reachable
        try:
            _fetch_oidc_discovery(resolved_discovery)
        except Exception as exc:
            return jsonify({"error": f"Could not fetch OIDC discovery document: {exc}"}), 400

        provider_id = str(uuid.uuid4())
        secret_encrypted = _encrypt_secret(client_secret)

        sso_repo.insert_provider(
            conn,
            provider_id=provider_id,
            tenant_id=tenant_id,
            provider_name=provider_name,
            provider_type=provider_type,
            client_id=client_id,
            client_secret_encrypted=secret_encrypted,
            discovery_url=resolved_discovery,
            allowed_domains=allowed_domains,
            role_mapping_attribute=role_mapping_attribute,
            role_mapping=role_mapping,
            default_role=default_role,
            created_by=g.user_id,
        )
        audit(
            conn,
            "SSO_CREATE_PROVIDER",
            resource_type="sso_provider",
            resource_id=provider_id,
            details={"tenant_id": tenant_id, "provider_type": provider_type},
        )
        conn.commit()

        return jsonify({"success": True, "provider_id": provider_id}), 201

    except Exception as exc:
        logger.error("Failed to create SSO provider: %s", exc, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/sso/admin/providers/<provider_id>", methods=["PUT"])
@csrf_exempt
@require_auth
@require_tenant_admin
def admin_update_provider(provider_id):
    """Update an existing SSO provider configuration."""
    data = request.json or {}

    try:
        conn = get_db_connection()
        provider = sso_repo.get_provider_by_id(conn, provider_id)
        if not provider:
            return jsonify({"error": "Provider not found"}), 404

        if not _can_manage_tenant(provider["tenant_id"]):
            return jsonify({"error": "Forbidden: you cannot manage SSO for this tenant"}), 403

        updates = {}
        for field in (
            "provider_name",
            "provider_type",
            "client_id",
            "discovery_url",
            "allowed_domains",
            "role_mapping_attribute",
            "role_mapping",
            "default_role",
            "is_enabled",
        ):
            if field in data:
                updates[field] = data[field]

        if "client_secret" in data and data["client_secret"]:
            updates["client_secret"] = _encrypt_secret(data["client_secret"])

        if "provider_type" in updates and updates["provider_type"] not in _VALID_PROVIDER_TYPES:
            return (
                jsonify(
                    {
                        "error": f"provider_type must be one of: {', '.join(sorted(_VALID_PROVIDER_TYPES))}"
                    }
                ),
                400,
            )

        if not updates:
            return jsonify({"error": "No updatable fields provided"}), 400

        sso_repo.update_provider(conn, provider_id, updates)
        audit(
            conn,
            "SSO_UPDATE_PROVIDER",
            resource_type="sso_provider",
            resource_id=provider_id,
            details={"updated_fields": list(updates.keys())},
        )
        conn.commit()

        return jsonify({"success": True}), 200

    except Exception as exc:
        logger.error("Failed to update SSO provider %s: %s", provider_id, exc, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/sso/admin/providers/<provider_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
@require_tenant_admin
def admin_delete_provider(provider_id):
    """Remove an SSO provider configuration."""
    try:
        conn = get_db_connection()
        provider = sso_repo.get_provider_by_id(conn, provider_id)
        if not provider:
            return jsonify({"error": "Provider not found"}), 404

        if not _can_manage_tenant(provider["tenant_id"]):
            return jsonify({"error": "Forbidden: you cannot manage SSO for this tenant"}), 403

        sso_repo.delete_provider(conn, provider_id)
        audit(
            conn,
            "SSO_DELETE_PROVIDER",
            resource_type="sso_provider",
            resource_id=provider_id,
            details={"tenant_id": provider["tenant_id"]},
        )
        conn.commit()

        return jsonify({"success": True}), 200

    except Exception as exc:
        logger.error("Failed to delete SSO provider %s: %s", provider_id, exc, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
