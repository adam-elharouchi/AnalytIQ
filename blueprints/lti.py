"""
LTI 1.3 Blueprint — LMS integration (Canvas, Blackboard, Moodle, D2L, etc.)

Routes:
  GET  /lti/jwks                          — Tool's public JWKS (platform verifies our JWTs)
  POST /lti/login                         — OIDC login initiation
  POST /lti/launch                        — LTI resource launch (main entry point)
  GET  /lti/setup                         — Serve professor setup UI
  GET  /api/lti/config                    — List registered LMS platforms  [professor]
  POST /api/lti/config                    — Register a new LMS platform    [professor]
  DELETE /api/lti/config/<config_id>      — Remove a platform registration [professor]
  POST /lti/deep-link/return              — Return signed deep-link response to LMS
  POST /api/lti/sync-roster/<class_id>    — NRPS: sync students from LMS   [professor]
  POST /api/lti/ags/<class_id>/<ex_id>    — AGS: submit grade to LMS       [internal]
  POST /api/lti/link-class/<class_id>     — Link a class to an LTI context [professor]
  PUT  /api/lti/ags-toggle/<class_id>     — Toggle AGS on/off for a class  [professor]
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import config
from core.auth import (
    create_jwt_token,
    create_refresh_token,
    get_user_token_version,
    require_auth,
    require_role,
)
from core.database import get_db_connection
from core.extensions import csrf_exempt
from flask import Blueprint, g, jsonify, render_template, request
from repositories import auth_repository as auth_repo
from repositories import class_repository as class_repo
from repositories import lti_repository as lti_repo

logger = logging.getLogger(__name__)
bp = Blueprint("lti", __name__)


# ---------------------------------------------------------------------------
# Redis-backed state storage for PyLTI1p3
# Avoids SameSite cookie issues when AnalytIQ is embedded in LMS iframes.
# ---------------------------------------------------------------------------


try:
    from pylti1p3.launch_data_storage.base import LaunchDataStorage as _LtiStorageBase
except ImportError:
    _LtiStorageBase = object  # type: ignore[assignment,misc]


class _RedisLtiStorage(_LtiStorageBase):
    """Redis-backed launch data storage for pylti1p3 v2.x.

    Extends LaunchDataStorage to inherit set_request / set_session_id /
    _prepare_key / etc., then stores state in Redis so the OIDC flow works
    inside LMS iframes where SameSite=Lax cookies are blocked.
    """

    _DEFAULT_TTL = 7200  # 2 hours

    def get_session_cookie_name(self):
        # Returning None tells pylti1p3 to skip cookie-based session_id lookup.
        # Keys are already unique per nonce/state so no session prefix is needed,
        # and cookies are blocked anyway when AnalytIQ is embedded in an LMS iframe.
        return None

    def can_set_keys_expiration(self):
        return True

    def get_value(self, key):
        try:
            from core.cache import redis_client

            if not redis_client:
                return None
            raw = redis_client.get(self._prepare_key(key))
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.debug("LTI storage get error: %s", exc)
            return None

    def set_value(self, key, value, exp=None):
        try:
            from core.cache import redis_client

            if not redis_client:
                return
            ttl = int(exp) if exp else self._DEFAULT_TTL
            redis_client.setex(self._prepare_key(key), ttl, json.dumps(value))
        except Exception as exc:
            logger.debug("LTI storage set error: %s", exc)

    def check_value(self, key):
        try:
            from core.cache import redis_client

            if not redis_client:
                return False
            return redis_client.exists(self._prepare_key(key)) > 0
        except Exception as exc:
            logger.debug("LTI storage check error: %s", exc)
            return False


def _get_lti_storage():
    """Return a Redis-backed LTI storage instance for pylti1p3."""
    return _RedisLtiStorage()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_tool_conf(conn):
    """Load all LTI configs from DB and build a ToolConfDict with our RSA keys.

    Returns None (and logs a warning) if PyLTI1p3 is not installed or if no
    private key is configured.
    """
    try:
        from pylti1p3.contrib.flask import FlaskRequest  # noqa: F401 — availability check
        from pylti1p3.tool_config import ToolConfDict
    except ImportError:
        logger.warning("PyLTI1p3 is not installed. LTI features will not work.")
        return None

    if not config.LTI_PRIVATE_KEY or not config.LTI_PUBLIC_KEY:
        logger.warning("LTI_PRIVATE_KEY / LTI_PUBLIC_KEY not configured.")
        return None

    configs = lti_repo.get_all_lti_configs(conn)
    if not configs:
        return ToolConfDict({})

    # ToolConfDict format: { issuer: [ { "client_id": ..., "auth_login_url": ..., ... } ] }
    tool_conf_dict = {}
    for cfg in configs:
        issuer = cfg["issuer"]
        entry = {
            "client_id": cfg["client_id"],
            "auth_login_url": cfg["auth_login_url"],
            "auth_token_url": cfg["auth_token_url"],
            "key_set_url": cfg["key_set_url"],
            "deployment_ids": cfg.get("deployment_ids") or [],
        }
        tool_conf_dict.setdefault(issuer, []).append(entry)

    tc = ToolConfDict(tool_conf_dict)

    # Normalise PEM — env vars often store \n as literal backslash-n
    private_key = config.LTI_PRIVATE_KEY.replace("\\n", "\n")
    public_key = config.LTI_PUBLIC_KEY.replace("\\n", "\n")

    for cfg in configs:
        tc.set_private_key(cfg["issuer"], private_key, client_id=cfg["client_id"])
        tc.set_public_key(cfg["issuer"], public_key, client_id=cfg["client_id"])

    return tc


def _upsert_lti_user(conn, launch_data):
    """Find or create a user from LTI launch claims.

    Resolution order:
      1. Existing user with matching lti_sub + issuer
      2. Existing user with matching email → link LTI identity
      3. Create new LTI-only account (password_hash = NULL)

    Returns (user_row, jwt_token) where user_row is a 4-tuple
    (user_id, name, email, role).
    """
    lti_sub = launch_data.get("sub", "")
    issuer = launch_data.get("iss", "")
    email = launch_data.get("email", "").strip().lower() if launch_data.get("email") else ""
    given = launch_data.get("given_name", "")
    family = launch_data.get("family_name", "")
    name = (launch_data.get("name") or f"{given} {family}").strip() or "LTI User"

    roles_claim = launch_data.get("https://purl.imsglobal.org/spec/lti/claim/roles", [])
    role = (
        "professor"
        if any("Instructor" in r or "Administrator" in r for r in roles_claim)
        else "student"
    )

    # 1. Find by LTI sub
    user_row = lti_repo.get_user_by_lti_sub(conn, lti_sub, issuer)

    # 2. Find by email and link
    if not user_row and email:
        email_row = auth_repo.get_user_by_email(conn, email)
        if email_row:
            # email_row = (user_id, name, email, password_hash, role)
            existing_role = email_row[4]
            # SECURITY: never federate an LTI identity into a privileged account
            # via an email-claim match. Without this, an LMS launch carrying
            # email=<an admin's email> would mint a JWT for that admin account.
            # Privileged users must sign in directly.
            if existing_role in ("superadmin", "tenant_admin"):
                raise PermissionError(
                    "This email is associated with a privileged account that "
                    "cannot be accessed via LMS launch."
                )
            lti_repo.link_lti_identity(conn, email_row[0], lti_sub, issuer)
            # Promote to professor if Canvas says Instructor but account is student.
            # Never demote an existing professor/admin via LTI.
            effective_role = (
                role if role == "professor" and existing_role == "student" else existing_role
            )
            if effective_role != existing_role:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE users SET role = %s WHERE user_id = %s",
                    (effective_role, email_row[0]),
                )
                cur.close()
            user_row = (email_row[0], email_row[1], email_row[2], effective_role)

    # 3. Create new account
    if not user_row:
        user_id = str(uuid.uuid4())
        new_row = auth_repo.insert_user(conn, user_id, name, email or f"{lti_sub}@lti", None, role)
        if new_row:
            lti_repo.link_lti_identity(conn, new_row[0], lti_sub, issuer)
            # Create companion profile / settings rows (ignore errors — tables may differ)
            try:
                auth_repo.create_default_profile(conn, new_row[0])
                auth_repo.create_default_settings(conn, new_row[0])
                auth_repo.create_default_preferences(conn, new_row[0])
                auth_repo.create_default_ai_digest(conn, new_row[0])
            except Exception as e:
                logger.debug(
                    "Non-critical: default profile creation failed for new LTI user %s: %s",
                    new_row[0],
                    e,
                )
            user_row = (new_row[0], new_row[1], new_row[2], role)

    if not user_row:
        raise RuntimeError("Failed to resolve LTI user")

    user_id, user_name, user_email, user_role = user_row[0], user_row[1], user_row[2], user_row[3]
    _tv = get_user_token_version(conn, user_id)
    jwt_token = create_jwt_token(
        user_id,
        user_role,
        user_name,
        user_email,
        token_version=_tv,
    )
    refresh_token = create_refresh_token(user_id, token_version=_tv)
    return (user_id, user_name, user_email, user_role), jwt_token, refresh_token


def _store_lti_session(conn, launch_data, user_id, class_id):
    """Persist a short-lived LTI session record in the DB."""
    session_id = str(uuid.uuid4())
    issuer = launch_data.get("iss", "")
    client_id = launch_data.get("aud", "")
    if isinstance(client_id, list):
        client_id = client_id[0] if client_id else ""

    context_claim = launch_data.get("https://purl.imsglobal.org/spec/lti/claim/context", {}) or {}
    lti_context_id = context_claim.get("id", "")

    nrps_claim = (
        launch_data.get("https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice", {}) or {}
    )
    nrps_url = nrps_claim.get("context_memberships_url", "")

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=config.LTI_SESSION_TTL)

    # Store a safe subset of launch data (exclude private key material)
    safe_launch = {
        "iss": issuer,
        "sub": launch_data.get("sub"),
        "email": launch_data.get("email"),
        "name": launch_data.get("name"),
        "roles": launch_data.get("https://purl.imsglobal.org/spec/lti/claim/roles", []),
        "context": context_claim,
        "nrps_url": nrps_url,
    }

    lti_repo.create_lti_session(
        conn,
        session_id=session_id,
        user_id=user_id,
        class_id=class_id,
        nrps_context_url=nrps_url,
        lti_context_id=lti_context_id,
        issuer=issuer,
        client_id=client_id,
        launch_data=safe_launch,
        expires_at=expires_at,
    )
    return session_id


_LTI_ENDPOINTS = ("/lti/jwks", "/lti/login", "/lti/launch")


_CONTENT_PAGES = (
    "/student-chapter.html",
    "/student-classes.html",
    "/student-class.html",
    "/professor-class.html",
    "/professor-dashboard.html",
)


def _resolve_target_url(launch_data, class_id, db_role="student"):
    """Return the AnalytIQ page to redirect to after a successful launch.

    DB role takes precedence for admin accounts. target_link_uri is only
    trusted for known content pages (deep-linked chapters/classes).
    """
    from urllib.parse import urlparse

    # Superadmin → superadmin dashboard (has no tenant_id, must not hit tenant-admin routes)
    if db_role == "superadmin":
        return "/superadmin-dashboard.html"

    # Tenant admin → their scoped dashboard (they have a tenant_id)
    if db_role == "tenant_admin":
        return "/tenant-admin-dashboard.html"

    # For professor/student, honour deep-linked content pages only
    target_link_uri = launch_data.get(
        "https://purl.imsglobal.org/spec/lti/claim/target_link_uri", ""
    )
    parsed = urlparse(target_link_uri)
    is_same_origin = bool(target_link_uri and target_link_uri.startswith(config.LTI_TOOL_URL))
    is_content_page = any(parsed.path.startswith(p.split("?")[0]) for p in _CONTENT_PAGES)
    if is_same_origin and is_content_page:
        return target_link_uri

    # Role-based routing from LTI claims
    roles = launch_data.get("https://purl.imsglobal.org/spec/lti/claim/roles", [])
    if db_role == "professor" or any("Instructor" in r or "Administrator" in r for r in roles):
        if class_id:
            return f"/professor-class.html?id={class_id}"
        return "/professor-dashboard.html"

    if class_id:
        return f"/student-class.html?id={class_id}"
    return "/student-classes.html"


# ---------------------------------------------------------------------------
# JWKS — Tool's public key for platform verification
# ---------------------------------------------------------------------------


@bp.route("/lti/jwks", methods=["GET"])
def lti_jwks():
    """Return the tool's public JWKS so the LMS can verify our JWTs."""
    try:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
        import base64
    except ImportError:
        return jsonify({"error": "cryptography package not installed"}), 500

    if not config.LTI_PUBLIC_KEY:
        return jsonify({"error": "LTI public key not configured"}), 500

    public_pem = config.LTI_PUBLIC_KEY.replace("\\n", "\n").encode("utf-8")
    try:
        pub_key = load_pem_public_key(public_pem, backend=default_backend())
    except Exception as e:
        logger.error("Failed to load LTI public key: %s", e)
        return jsonify({"error": "Invalid LTI public key"}), 500

    if not isinstance(pub_key, RSAPublicKey):
        return jsonify({"error": "LTI key must be RSA"}), 500

    pub_numbers = (
        pub_key.public_key().public_numbers()
        if hasattr(pub_key, "public_key")
        else pub_key.public_numbers()
    )

    def _int_to_base64url(n):
        length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode("ascii")

    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": config.LTI_KEY_ID,
                "n": _int_to_base64url(pub_numbers.n),
                "e": _int_to_base64url(pub_numbers.e),
            }
        ]
    }
    return jsonify(jwks)


# ---------------------------------------------------------------------------
# OIDC Login initiation
# ---------------------------------------------------------------------------


@bp.route("/lti/login", methods=["GET", "POST"])
@csrf_exempt
def lti_login():
    """Platform-initiated OIDC login — redirect back to platform for auth."""
    try:
        from pylti1p3.contrib.flask import FlaskOIDCLogin, FlaskRequest
        from pylti1p3.exception import OIDCException
    except ImportError:
        return jsonify({"error": "PyLTI1p3 not installed"}), 500

    conn = get_db_connection()
    tool_conf = _build_tool_conf(conn)
    if tool_conf is None:
        return jsonify({"error": "LTI not configured"}), 500

    try:
        flask_req = FlaskRequest()
        target_link_uri = flask_req.get_param("target_link_uri") or f"{config.LTI_TOOL_URL}/"
        oidc_login = FlaskOIDCLogin(flask_req, tool_conf, launch_data_storage=_get_lti_storage())
        # enable_check_cookies() is intentionally omitted: it requires
        # third-party cookie support, which browsers block in LMS iframes.
        # Redis-backed storage makes the cookie check unnecessary.
        return oidc_login.redirect(target_link_uri)
    except OIDCException as e:
        logger.warning("LTI OIDC login error: %s", e)
        return jsonify({"error": "OIDC login failed"}), 400
    except Exception as e:
        logger.error("LTI login unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500


# ---------------------------------------------------------------------------
# LTI Launch
# ---------------------------------------------------------------------------


@bp.route("/lti/launch", methods=["POST"])
@csrf_exempt
def lti_launch():
    """Main LTI 1.3 launch endpoint. Validates id_token, upserts user, issues JWT."""
    try:
        from pylti1p3.contrib.flask import FlaskMessageLaunch, FlaskRequest
    except ImportError:
        return jsonify({"error": "PyLTI1p3 not installed"}), 500

    conn = get_db_connection()
    tool_conf = _build_tool_conf(conn)
    if tool_conf is None:
        return jsonify({"error": "LTI not configured"}), 500

    # Decode raw JWT claims before validation so we can surface debug info on failure
    raw_deployment_id = None
    try:
        import base64 as _b64
        import json as _json

        raw_token = request.form.get("id_token", "")
        if raw_token:
            payload_b64 = raw_token.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            raw_claims = _json.loads(_b64.urlsafe_b64decode(payload_b64))
            raw_deployment_id = raw_claims.get(
                "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
            )
            logger.info(
                "LTI launch raw claims — iss=%s client_id=%s deployment_id=%s",
                raw_claims.get("iss"),
                raw_claims.get("aud"),
                raw_deployment_id,
            )
    except Exception:
        pass

    try:
        flask_req = FlaskRequest()
        message_launch = FlaskMessageLaunch(
            flask_req, tool_conf, launch_data_storage=_get_lti_storage()
        )
        launch_data = message_launch.get_launch_data()
    except Exception as e:
        logger.warning("LTI launch validation failed: %s", e)
        error_msg = f"LTI launch validation failed: {e}"
        if "deployment" in str(e).lower() and raw_deployment_id:
            error_msg += f" | Canvas sent deployment_id: {raw_deployment_id}"
        return (
            render_template("lti-launch-error.html", error=error_msg),
            400,
        )

    # Deep linking launch — professor selecting content to embed in LMS
    if message_launch.is_deep_link_launch():
        return _handle_deep_link(conn, message_launch, launch_data)

    try:
        user_tuple, jwt_token, refresh_token = _upsert_lti_user(conn, launch_data)
        user_id = user_tuple[0]

        # Determine which AnalytIQ class matches this LTI course context
        context_claim = (
            launch_data.get("https://purl.imsglobal.org/spec/lti/claim/context", {}) or {}
        )
        lti_context_id = context_claim.get("id", "")
        issuer = launch_data.get("iss", "")

        class_id = None
        if lti_context_id and issuer:
            class_row = lti_repo.get_class_by_lti_context(conn, lti_context_id, issuer)
            if class_row:
                class_id = class_row["class_id"]
                # Auto-capture AGS lineitems URL from launch data
                ags_claim = (
                    launch_data.get("https://purl.imsglobal.org/spec/lti-ags/claim/endpoint", {})
                    or {}
                )
                ags_lineitems_url = ags_claim.get("lineitems", "")
                if ags_lineitems_url and not class_row.get("ags_lineitems_url"):
                    try:
                        lti_repo.update_class_ags_lineitems_url(conn, class_id, ags_lineitems_url)
                    except Exception as ags_url_err:
                        logger.warning("Could not save AGS lineitems URL: %s", ags_url_err)
                # Auto-enroll students who launch via LTI
                if user_tuple[3] == "student" and class_id:
                    try:
                        if not class_repo.check_enrollment(conn, class_id, user_id):
                            class_repo.enroll_student(conn, class_id, user_id)
                    except Exception as enroll_err:
                        logger.warning("Auto-enroll failed: %s", enroll_err)

        _store_lti_session(conn, launch_data, user_id, class_id)
        conn.commit()

        redirect_url = _resolve_target_url(launch_data, class_id, db_role=user_tuple[3])
        return render_template(
            "lti-launch.html",
            jwt_token=jwt_token,
            refresh_token=refresh_token,
            redirect_url=redirect_url,
            user_name=user_tuple[1],
        )

    except Exception as e:
        logger.error("LTI launch processing error: %s", e, exc_info=True)
        conn.rollback()
        return render_template("lti-launch-error.html", error="Launch processing failed"), 500


# ---------------------------------------------------------------------------
# Deep Linking
# ---------------------------------------------------------------------------


def _handle_deep_link(conn, message_launch, launch_data):
    """Render chapter/exercise selector so a professor can embed content in the LMS."""
    try:
        user_tuple, _, _ = _upsert_lti_user(conn, launch_data)
        professor_id = user_tuple[0]
        conn.commit()
    except Exception as e:
        logger.error("Deep link user upsert failed: %s", e)
        conn.rollback()
        return render_template("lti-launch-error.html", error="User resolution failed"), 500

    classes = class_repo.get_professor_classes(conn, professor_id, limit=100, offset=0)
    launch_id = message_launch.get_launch_id()
    return render_template(
        "lti-deep-link.html",
        classes=classes,
        launch_id=launch_id,
        tool_url=config.LTI_TOOL_URL,
    )


@bp.route("/lti/deep-link/return", methods=["POST"])
@csrf_exempt
def deep_link_return():
    """Professor selected content; return signed deep-link JWT to the LMS."""
    try:
        from pylti1p3.contrib.flask import FlaskMessageLaunch, FlaskRequest
        from pylti1p3.deep_link_resource import DeepLinkResource
    except ImportError:
        return jsonify({"error": "PyLTI1p3 not installed"}), 500

    launch_id = request.form.get("launch_id")
    chapter_id = request.form.get("chapter_id")
    title = request.form.get("title", "AnalytIQ Chapter")

    if not launch_id or not chapter_id:
        return jsonify({"error": "launch_id and chapter_id are required"}), 400

    conn = get_db_connection()
    tool_conf = _build_tool_conf(conn)
    if tool_conf is None:
        return jsonify({"error": "LTI not configured"}), 500

    try:
        flask_req = FlaskRequest()
        message_launch = FlaskMessageLaunch.from_cache(launch_id, flask_req, tool_conf)
        dl_response = message_launch.get_deep_link_response()

        resource = (
            DeepLinkResource()
            .set_url(f"{config.LTI_TOOL_URL}/chapter-view.html?id={chapter_id}")
            .set_title(title)
        )
        html = dl_response.get_embed_html([resource])
        return html
    except Exception as e:
        logger.error("Deep link return error: %s", e, exc_info=True)
        return jsonify({"error": "Deep link failed"}), 500


# ---------------------------------------------------------------------------
# LMS Platform Config CRUD (professor only)
# ---------------------------------------------------------------------------


@bp.route("/lti/setup", methods=["GET"])
@require_auth
@require_role("professor", "superadmin")
def lti_setup():
    """Render the LTI setup UI for professors."""
    return render_template("lti-setup.html")


@bp.route("/api/lti/config", methods=["GET"])
@csrf_exempt
@require_auth
@require_role("professor", "superadmin")
def list_lti_configs():
    """Return all LTI platform registrations."""
    conn = get_db_connection()
    configs = lti_repo.get_all_lti_configs(conn)
    # Omit private details; surface only what the UI needs
    public_configs = [
        {
            "config_id": c["config_id"],
            "platform_name": c["platform_name"],
            "issuer": c["issuer"],
            "client_id": c["client_id"],
            "auth_login_url": c["auth_login_url"],
            "auth_token_url": c["auth_token_url"],
            "key_set_url": c["key_set_url"],
            "deployment_ids": c.get("deployment_ids") or [],
            "created_at": c["created_at"].isoformat() if c.get("created_at") else None,
        }
        for c in configs
    ]
    return jsonify({"configs": public_configs})


@bp.route("/api/lti/config", methods=["POST"])
@csrf_exempt
@require_auth
@require_role("superadmin")
def create_lti_config():
    """Register a new LMS platform (superadmin only).

    An LTI platform registration declares a TRUSTED issuer + JWKS key set used
    to validate launch tokens. Allowing arbitrary professors to register
    platforms would let them sign their own launches and impersonate any user,
    so this is restricted to superadmins.
    """
    data = request.json or {}
    required = [
        "platform_name",
        "issuer",
        "client_id",
        "auth_login_url",
        "auth_token_url",
        "key_set_url",
    ]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    conn = get_db_connection()
    try:
        cfg = lti_repo.insert_lti_config(
            conn,
            platform_name=data["platform_name"].strip(),
            issuer=data["issuer"].strip(),
            client_id=data["client_id"].strip(),
            auth_login_url=data["auth_login_url"].strip(),
            auth_token_url=data["auth_token_url"].strip(),
            key_set_url=data["key_set_url"].strip(),
            deployment_ids=data.get("deployment_ids") or [],
            created_by=g.user_id,
        )
        conn.commit()
        return (
            jsonify(
                {
                    "config_id": cfg["config_id"],
                    "platform_name": cfg["platform_name"],
                    "issuer": cfg["issuer"],
                    "client_id": cfg["client_id"],
                    "created_at": cfg["created_at"].isoformat() if cfg.get("created_at") else None,
                }
            ),
            201,
        )
    except Exception as e:
        conn.rollback()
        # Duplicate (issuer, client_id) pair
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return jsonify({"error": "A config for this issuer + client_id already exists"}), 409
        logger.error("Failed to create LTI config: %s", e, exc_info=True)
        return jsonify({"error": "Failed to save configuration"}), 500


@bp.route("/api/lti/config/<config_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
@require_role("superadmin")
def delete_lti_config(config_id):
    """Delete an LTI platform registration (superadmin only)."""
    conn = get_db_connection()
    deleted = lti_repo.delete_lti_config(conn, config_id, g.user_id)
    if not deleted:
        return jsonify({"error": "Config not found or not authorized"}), 404
    conn.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Link a class to an LTI course context (professor action)
# ---------------------------------------------------------------------------


@bp.route("/api/lti/link-class/<class_id>", methods=["POST"])
@csrf_exempt
@require_auth
@require_role("professor", "superadmin")
def link_class(class_id):
    """Manually link an AnalytIQ class to an LMS course context."""
    data = request.json or {}
    lti_context_id = (data.get("lti_context_id") or "").strip()
    issuer = (data.get("issuer") or "").strip()
    nrps_context_url = (data.get("nrps_context_url") or "").strip()
    ags_lineitems_url = (data.get("ags_lineitems_url") or "").strip() or None

    if not lti_context_id or not issuer:
        return jsonify({"error": "lti_context_id and issuer are required"}), 400

    conn = get_db_connection()
    # Verify professor owns the class
    class_row = class_repo.get_class_with_name(conn, class_id)
    if not class_row or class_row[2] != g.user_id:
        return jsonify({"error": "Class not found or not authorized"}), 404

    lti_repo.link_class_to_lti_context(
        conn, class_id, lti_context_id, issuer, nrps_context_url, ags_lineitems_url
    )
    conn.commit()
    return jsonify({"linked": True, "class_id": class_id, "lti_context_id": lti_context_id})


# ---------------------------------------------------------------------------
# Toggle AGS grade passback
# ---------------------------------------------------------------------------


@bp.route("/api/lti/ags-toggle/<class_id>", methods=["PUT"])
@csrf_exempt
@require_auth
@require_role("professor", "superadmin")
def toggle_ags(class_id):
    """Enable or disable AGS grade passback for a class."""
    data = request.json or {}
    if "enabled" not in data:
        return jsonify({"error": "'enabled' field is required"}), 400

    conn = get_db_connection()
    class_row = class_repo.get_class_with_name(conn, class_id)
    if not class_row or class_row[2] != g.user_id:
        return jsonify({"error": "Class not found or not authorized"}), 404

    lti_repo.set_class_ags_enabled(conn, class_id, bool(data["enabled"]))
    conn.commit()
    return jsonify({"class_id": class_id, "ags_enabled": bool(data["enabled"])})


# ---------------------------------------------------------------------------
# NRPS — Sync roster from LMS
# ---------------------------------------------------------------------------


@bp.route("/api/lti/sync-roster/<class_id>", methods=["POST"])
@csrf_exempt
@require_auth
@require_role("professor", "superadmin")
def sync_roster(class_id):
    """Fetch students from LMS Names & Roles Provisioning Service and enroll them."""
    try:
        from pylti1p3.names_roles import NamesRolesProvisioningService
    except ImportError:
        return jsonify({"error": "PyLTI1p3 not installed"}), 500

    conn = get_db_connection()

    # Pull the class row (needs nrps_context_url stored from a prior launch)
    cur = conn.cursor()
    cur.execute(
        """SELECT class_id, professor_id, name, nrps_context_url, lti_issuer, lti_context_id,
                  ags_enabled, ags_lineitems_url
           FROM classes WHERE class_id = %s""",
        (class_id,),
    )
    row = cur.fetchone()
    cur.close()

    if not row:
        return jsonify({"error": "Class not found"}), 404
    if row[1] != g.user_id:
        return jsonify({"error": "Not authorized"}), 403

    nrps_url = row[3]
    if not nrps_url:
        return (
            jsonify({"error": "This class is not linked to an LMS or NRPS is not available"}),
            400,
        )

    tool_conf = _build_tool_conf(conn)
    if tool_conf is None:
        return jsonify({"error": "LTI not configured"}), 500

    lti_issuer = row[4]

    try:
        # Build a minimal service context
        nrps_service = NamesRolesProvisioningService(
            tool_conf,
            {"context_memberships_url": nrps_url},
            lti_issuer,
        )
        members_response = nrps_service.get_members()
    except Exception as e:
        logger.error("NRPS sync failed for class %s: %s", class_id, e, exc_info=True)
        return jsonify({"error": "Failed to fetch roster from LMS"}), 502

    members = (
        members_response
        if isinstance(members_response, list)
        else members_response.get("members", [])
    )

    enrolled_count = 0
    skipped_count = 0
    for member in members:
        member_roles = member.get("roles", [])
        if not any("Learner" in r for r in member_roles):
            skipped_count += 1
            continue

        # Build synthetic launch_data subset for _upsert_lti_user
        member_launch = {
            "sub": member.get("user_id", ""),
            "iss": lti_issuer,
            "email": member.get("email", ""),
            "name": member.get("name", ""),
            "given_name": member.get("given_name", ""),
            "family_name": member.get("family_name", ""),
            "https://purl.imsglobal.org/spec/lti/claim/roles": member_roles,
        }

        try:
            user_tuple, _, _ = _upsert_lti_user(conn, member_launch)
            student_id = user_tuple[0]
            if not class_repo.check_enrollment(conn, class_id, student_id):
                class_repo.enroll_student(conn, class_id, student_id)
                enrolled_count += 1
        except Exception as member_err:
            logger.warning("Failed to enroll member %s: %s", member.get("user_id"), member_err)

    conn.commit()
    return jsonify(
        {
            "enrolled": enrolled_count,
            "skipped": skipped_count,
            "total_members": len(members),
        }
    )


# ---------------------------------------------------------------------------
# AGS — grade passback helpers


def _push_ags_grade(conn, class_id, exercise_id, lti_user_id, score, max_score=100):
    """Push a grade to the LMS via AGS.

    Parameters
    ----------
    conn         : DB connection
    class_id     : AnalytIQ class_id (must have ags_enabled=True and ags_lineitems_url set)
    exercise_id  : used as the line-item tag
    lti_user_id  : the LTI platform's user identifier (users.lti_sub), NOT the internal user_id
    score        : numeric score 0-100
    max_score    : maximum score (default 100)

    Raises on failure so callers can decide whether to swallow or propagate.
    """
    try:
        from pylti1p3.assignments_grades import AssignmentsGradesService
        from pylti1p3.grade import Grade
        from pylti1p3.lineitem import LineItem
    except ImportError:
        raise RuntimeError("PyLTI1p3 not installed")

    cur = conn.cursor()
    cur.execute(
        "SELECT ags_enabled, ags_lineitems_url, lti_issuer FROM classes WHERE class_id = %s",
        (class_id,),
    )
    row = cur.fetchone()
    cur.close()

    if not row or not row[0] or not row[1]:
        return  # AGS not enabled or lineitems URL missing — silently skip

    ags_url, lti_issuer = row[1], row[2]
    tool_conf = _build_tool_conf(conn)
    if tool_conf is None:
        raise RuntimeError("LTI tool not configured")

    ags = AssignmentsGradesService(
        tool_conf,
        {"lineitems": ags_url, "scope": ["https://purl.imsglobal.org/spec/lti-ags/scope/score"]},
        lti_issuer,
    )
    grade = (
        Grade()
        .set_score_given(score)
        .set_score_maximum(max_score)
        .set_timestamp(datetime.now(timezone.utc).isoformat())
        .set_activity_progress("Completed")
        .set_grading_progress("FullyGraded")
        .set_user_id(lti_user_id)
    )
    line_item = LineItem()
    line_item.set_tag(f"exercise-{exercise_id}").set_score_maximum(max_score)
    ags.put_grade(grade, line_item)


# AGS — Submit a grade to the LMS
# ---------------------------------------------------------------------------


@bp.route("/api/lti/ags/<class_id>/<exercise_id>", methods=["POST"])
@csrf_exempt
@require_auth
def submit_grade(class_id, exercise_id):
    """Push the caller's server-graded score for an exercise to the LMS via AGS.

    The score is NOT taken from the request body — it is read from the
    authoritative server-graded record (exercise_attempts, written by
    /api/exercises/<id>/grade). This prevents a student from POSTing an
    arbitrary score (e.g. 100) straight to their LMS gradebook.
    """
    from repositories import user_repository as user_repo

    data = request.json or {}
    max_score = data.get("max_score", 100)

    conn = get_db_connection()

    # Look up the LTI sub for the requesting user
    cur = conn.cursor()
    cur.execute("SELECT lti_sub FROM users WHERE user_id = %s", (g.user_id,))
    user_row = cur.fetchone()
    cur.close()

    lti_user_id = user_row[0] if user_row and user_row[0] else None
    if not lti_user_id:
        return jsonify({"error": "No LTI identity for this user"}), 400

    # Use the server-graded score, never a client-supplied value.
    server_score = user_repo.get_max_attempt_score(conn, g.user_id, exercise_id)
    if server_score is None:
        return jsonify({"error": "No graded score on record for this exercise"}), 400

    try:
        _push_ags_grade(conn, class_id, exercise_id, lti_user_id, server_score, max_score)
        return jsonify({"submitted": True, "score": server_score, "max_score": max_score})
    except Exception as e:
        logger.error("AGS grade submission failed: %s", e, exc_info=True)
        return jsonify({"error": "Grade submission to LMS failed"}), 502


# ---------------------------------------------------------------------------
# Tool URL info (returned in config UI so professors can paste into LMS)
# ---------------------------------------------------------------------------


@bp.route("/api/lti/tool-info", methods=["GET"])
@csrf_exempt
@require_auth
@require_role("professor", "superadmin")
def tool_info():
    """Return the tool's LTI endpoints for pasting into the LMS registration form."""
    base = config.LTI_TOOL_URL.rstrip("/")
    return jsonify(
        {
            "jwks_url": f"{base}/lti/jwks",
            "login_url": f"{base}/lti/login",
            "launch_url": f"{base}/lti/launch",
            "deep_link_url": f"{base}/lti/launch",
            "key_id": config.LTI_KEY_ID,
        }
    )
