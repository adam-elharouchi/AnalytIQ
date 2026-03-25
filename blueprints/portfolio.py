"""
Portfolio Blueprint — /api/portfolio/* and page routes for /portfolio/*
"""

import logging
import re

import requests
from flask import Blueprint, g, jsonify, render_template, request

import config
from core.auth import require_auth, validate_fields
from core.database import get_db_connection
from core.extensions import csrf_exempt
from repositories import portfolio_repository as repo
from services import portfolio_service as svc
from services.portfolio_execution_service import execute_project_code

logger = logging.getLogger(__name__)
bp = Blueprint("portfolio", __name__)

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$")
_VALID_LANGUAGES = {"python", "javascript", "sql", "r", "java"}
_VALID_ITEM_TYPES = {"class_exercise", "personal_project", "external_link"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_user_portfolio(conn, user_id):
    """Return portfolio profile row or None."""
    return repo.get_profile_by_user(conn, user_id)


def _require_portfolio(conn, user_id):
    """Return portfolio or (error_response, status_code) tuple."""
    profile = _get_user_portfolio(conn, user_id)
    if not profile:
        return None, (jsonify({"error": "Portfolio not found. Create one first."}), 404)
    return profile, None


# ---------------------------------------------------------------------------
# Portfolio Profile — Private API
# ---------------------------------------------------------------------------

@bp.route("/api/portfolio/profile", methods=["GET"])
@require_auth
def get_profile():
    """Get own portfolio profile."""
    try:
        conn = get_db_connection()
        profile = repo.get_profile_by_user(conn, g.user_id)
        if not profile:
            return jsonify({"profile": None}), 200
        return jsonify({"profile": svc.profile_to_dict(profile)}), 200
    except Exception as e:
        logger.error("get_profile error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/profile", methods=["POST"])
@csrf_exempt
@require_auth
def create_profile():
    """Create portfolio profile (first time setup)."""
    try:
        data = request.json or {}
        conn = get_db_connection()

        # Don't create duplicate
        existing = repo.get_profile_by_user(conn, g.user_id)
        if existing:
            return jsonify({"error": "Portfolio already exists."}), 409

        # Resolve display_name from currentUser or request body
        display_name = (data.get("display_name") or "").strip()
        if not display_name:
            # Fall back to user record
            cur = conn.cursor()
            cur.execute("SELECT name FROM users WHERE user_id = %s", (g.user_id,))
            row = cur.fetchone()
            cur.close()
            display_name = (row[0] if row else None) or "Student"

        slug_base = svc.generate_slug(display_name)
        slug = svc.unique_slug(slug_base, conn)
        portfolio_title = svc.portfolio_title_from_name(display_name)
        profile_id = svc.new_id()

        repo.insert_profile(conn, profile_id, g.user_id, slug, portfolio_title, display_name)
        conn.commit()

        profile = repo.get_profile_by_user(conn, g.user_id)
        return jsonify({"profile": svc.profile_to_dict(profile)}), 201
    except Exception as e:
        logger.error("create_profile error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/profile", methods=["PUT"])
@csrf_exempt
@require_auth
def update_profile():
    """Update portfolio profile settings."""
    try:
        data = request.json or {}
        conn = get_db_connection()

        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        allowed = {
            "portfolio_title", "display_name", "headline", "bio", "avatar_url",
            "accent_color", "layout_style", "linkedin_url", "github_username",
            "personal_website", "is_public",
        }
        fields = {k: v for k, v in data.items() if k in allowed}

        # Validate slug separately
        if "slug" in data:
            new_slug = str(data["slug"]).lower().strip()
            if not _SLUG_RE.match(new_slug):
                return jsonify({"error": "Slug must be 3–60 chars, lowercase letters, numbers, hyphens only."}), 400
            if repo.slug_exists(conn, new_slug, exclude_user_id=g.user_id):
                return jsonify({"error": "That URL is already taken."}), 409
            fields["slug"] = new_slug

        # Validate bio length
        if "bio" in fields and fields["bio"] and len(fields["bio"]) > 500:
            return jsonify({"error": "Bio must be 500 characters or less."}), 400

        repo.update_profile(conn, g.user_id, fields)
        conn.commit()

        profile = repo.get_profile_by_user(conn, g.user_id)
        return jsonify({"profile": svc.profile_to_dict(profile)}), 200
    except Exception as e:
        logger.error("update_profile error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/profile", methods=["DELETE"])
@csrf_exempt
@require_auth
def delete_profile():
    """Delete the entire portfolio (cascade deletes all items)."""
    try:
        conn = get_db_connection()
        repo.delete_profile(conn, g.user_id)
        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("delete_profile error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ---------------------------------------------------------------------------
# Portfolio Items — Private API
# ---------------------------------------------------------------------------

@bp.route("/api/portfolio/items", methods=["GET"])
@require_auth
def list_items():
    """List all own portfolio items."""
    try:
        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err
        rows = repo.get_items(conn, profile[0])
        return jsonify({"items": [svc.item_to_dict(r) for r in rows]}), 200
    except Exception as e:
        logger.error("list_items error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/items", methods=["POST"])
@csrf_exempt
@require_auth
def add_item():
    """Add an item to the portfolio (any type)."""
    try:
        data = request.json or {}
        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        item_type = data.get("item_type", "")
        if item_type not in _VALID_ITEM_TYPES:
            return jsonify({"error": f"item_type must be one of: {', '.join(_VALID_ITEM_TYPES)}"}), 400

        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "Title is required."}), 400
        if len(title) > 200:
            return jsonify({"error": "Title must be 200 characters or less."}), 400

        description = data.get("description") or None
        if description and len(description) > 1000:
            return jsonify({"error": "Description must be 1000 characters or less."}), 400

        language = (data.get("language") or "python").lower()
        if language not in _VALID_LANGUAGES:
            language = "python"

        tags = data.get("tags") or []
        if len(tags) > 10:
            return jsonify({"error": "Maximum 10 tags per item."}), 400

        item = {
            "id": svc.new_id(),
            "portfolio_id": profile[0],
            "item_type": item_type,
            "title": title,
            "description": description,
            "language": language,
            "tags": tags,
            "code_content": data.get("code_content"),
            "external_url": data.get("external_url"),
            "show_score": data.get("show_score", False),
            "is_visible": data.get("is_visible", True),
            "is_pinned": data.get("is_pinned", False),
            "project_status": "draft" if item_type == "personal_project" else None,
        }

        repo.insert_item(conn, item)
        conn.commit()

        row = repo.get_item(conn, item["id"], profile[0])
        return jsonify({"item": svc.item_to_dict(row)}), 201
    except Exception as e:
        logger.error("add_item error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/items/<item_id>", methods=["PUT"])
@csrf_exempt
@require_auth
def update_item(item_id):
    """Update a portfolio item."""
    try:
        data = request.json or {}
        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        row = repo.get_item(conn, item_id, profile[0])
        if not row:
            return jsonify({"error": "Item not found."}), 404

        allowed = {
            "title", "description", "language", "tags", "external_url",
            "show_score", "is_visible", "is_pinned", "display_order", "project_status",
        }
        fields = {k: v for k, v in data.items() if k in allowed}
        if "title" in fields and not fields["title"]:
            return jsonify({"error": "Title is required."}), 400
        if "description" in fields and fields["description"] and len(fields["description"]) > 1000:
            return jsonify({"error": "Description must be 1000 characters or less."}), 400

        repo.update_item(conn, item_id, profile[0], fields)
        conn.commit()

        row = repo.get_item(conn, item_id, profile[0])
        return jsonify({"item": svc.item_to_dict(row)}), 200
    except Exception as e:
        logger.error("update_item error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/items/<item_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
def delete_item(item_id):
    """Delete a portfolio item."""
    try:
        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        row = repo.get_item(conn, item_id, profile[0])
        if not row:
            return jsonify({"error": "Item not found."}), 404

        repo.delete_item(conn, item_id, profile[0])
        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("delete_item error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/items/reorder", methods=["POST"])
@csrf_exempt
@require_auth
def reorder_items():
    """Bulk reorder items. Body: {"order": ["id1", "id2", ...]}"""
    try:
        data = request.json or {}
        ordered_ids = data.get("order", [])
        if not isinstance(ordered_ids, list):
            return jsonify({"error": "order must be a list of item IDs."}), 400

        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        repo.reorder_items(conn, profile[0], ordered_ids)
        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("reorder_items error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ---------------------------------------------------------------------------
# Import from classes
# ---------------------------------------------------------------------------

@bp.route("/api/portfolio/available-exercises", methods=["GET"])
@require_auth
def available_exercises():
    """List completed exercises not yet in portfolio."""
    try:
        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        rows = repo.get_importable_exercises(conn, g.user_id, profile[0])
        exercises = []
        for row in rows:
            exercises.append({
                "exercise_id": row[0],
                "title": row[1],
                "language": row[2],
                "best_score": float(row[3]) if row[3] is not None else None,
                "last_completed_at": row[4].isoformat() if row[4] else None,
                "class_name": row[5],
                "chapter_name": row[6],
            })
        return jsonify({"exercises": exercises}), 200
    except Exception as e:
        logger.error("available_exercises error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/import-exercise", methods=["POST"])
@csrf_exempt
@require_auth
def import_exercise():
    """Import a completed exercise as a portfolio item."""
    try:
        data = request.json or {}
        exercise_id = data.get("exercise_id", "").strip()
        if not exercise_id:
            return jsonify({"error": "exercise_id is required."}), 400

        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        # Fetch exercise details
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ce.exercise_id, ce.title, ce.language,
                   c.name AS class_name, ch.title AS chapter_name, t.name AS tenant_name,
                   pp.best_score, pp.last_completed_at, ce.class_id
            FROM class_exercises ce
            LEFT JOIN classes c ON c.class_id = ce.class_id
            LEFT JOIN class_chapters ch ON ch.chapter_id = ce.chapter_id
            LEFT JOIN tenants t ON t.tenant_id = c.tenant_id
            LEFT JOIN practice_progress pp
                   ON pp.exercise_id = ce.exercise_id AND pp.user_id = %s
            WHERE ce.exercise_id = %s AND pp.completed = TRUE
            """,
            (g.user_id, exercise_id),
        )
        ex = cur.fetchone()
        cur.close()

        if not ex:
            return jsonify({"error": "Exercise not found or not completed."}), 404

        item = {
            "id": svc.new_id(),
            "portfolio_id": profile[0],
            "item_type": "class_exercise",
            "exercise_id": ex[0],
            "class_id": ex[8],
            "title": ex[1] or "Untitled Exercise",
            "language": ex[2] or "python",
            "source_class_name": ex[3],
            "source_chapter_name": ex[4],
            "source_institution": ex[5],
            "score": ex[6],
            "show_score": False,
            "is_visible": True,
            "is_pinned": False,
            "completed_at": ex[7],
        }

        repo.insert_item(conn, item)
        conn.commit()

        row = repo.get_item(conn, item["id"], profile[0])
        return jsonify({"item": svc.item_to_dict(row)}), 201
    except Exception as e:
        logger.error("import_exercise error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ---------------------------------------------------------------------------
# Personal Projects — code execution + AI assistant
# ---------------------------------------------------------------------------

@bp.route("/api/portfolio/projects", methods=["POST"])
@csrf_exempt
@require_auth
def create_project():
    """Create a new personal project and return the item."""
    try:
        data = request.json or {}
        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "Title is required."}), 400
        if len(title) > 200:
            return jsonify({"error": "Title must be 200 characters or less."}), 400

        language = (data.get("language") or "python").lower()
        if language not in _VALID_LANGUAGES:
            language = "python"

        description = data.get("description") or None
        if description and len(description) > 1000:
            return jsonify({"error": "Description must be 1000 characters or less."}), 400

        item = {
            "id": svc.new_id(),
            "portfolio_id": profile[0],
            "item_type": "personal_project",
            "title": title,
            "language": language,
            "description": description,
            "tags": data.get("tags") or [],
            "project_status": "draft",
            "is_visible": True,
            "is_pinned": False,
        }

        repo.insert_item(conn, item)
        conn.commit()

        row = repo.get_item(conn, item["id"], profile[0])
        return jsonify({"item": svc.item_to_dict(row)}), 201
    except Exception as e:
        logger.error("create_project error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/projects/<item_id>/code", methods=["PUT"])
@csrf_exempt
@require_auth
def save_code(item_id):
    """Save (auto-save) code for a personal project."""
    try:
        data = request.json or {}
        code = data.get("code", "")
        if len(code) > 50000:
            return jsonify({"error": "Code must be 50,000 characters or less."}), 400

        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        row = repo.get_item(conn, item_id, profile[0])
        if not row or row[2] != "personal_project":
            return jsonify({"error": "Project not found."}), 404

        repo.update_item_code(conn, item_id, profile[0], code)
        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("save_code error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/projects/<item_id>/run", methods=["POST"])
@csrf_exempt
@require_auth
def run_project(item_id):
    """Execute personal project code in sandbox."""
    try:
        data = request.json or {}
        code = data.get("code", "")
        if not code.strip():
            return jsonify({"error": "No code to run."}), 400
        if len(code) > 50000:
            return jsonify({"error": "Code must be 50,000 characters or less."}), 400

        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        row = repo.get_item(conn, item_id, profile[0])
        if not row or row[2] != "personal_project":
            return jsonify({"error": "Project not found."}), 404

        language = row[7] or "python"
        result = execute_project_code(code, language=language)

        repo.update_item_run_result(conn, item_id, profile[0], result["stdout"], result["stderr"])
        conn.commit()

        return jsonify(result), 200
    except Exception as e:
        logger.error("run_project error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/projects/<item_id>/publish", methods=["PUT"])
@csrf_exempt
@require_auth
def publish_project(item_id):
    """Mark a personal project as published (visible in portfolio)."""
    try:
        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        row = repo.get_item(conn, item_id, profile[0])
        if not row or row[2] != "personal_project":
            return jsonify({"error": "Project not found."}), 404

        repo.update_item(conn, item_id, profile[0], {"project_status": "published"})
        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("publish_project error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/portfolio/projects/<item_id>/assistant", methods=["POST"])
@csrf_exempt
@require_auth
def project_assistant(item_id):
    """
    AI Code Assistant for personal projects.
    Uses the main Gemini API (same as /api/ai/chat) with a project-aware system prompt.
    """
    try:
        data = request.json or {}
        contents = data.get("contents", [])

        if not contents:
            return jsonify({"error": "contents is required."}), 400

        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        row = repo.get_item(conn, item_id, profile[0])
        if not row:
            return jsonify({"error": "Project not found."}), 404

        item = svc.item_to_dict(row)
        language = item.get("language") or "python"
        title = item.get("title") or "Personal Project"
        description = item.get("description") or ""
        code_snippet = (item.get("code_content") or "")[:3000]  # cap context

        system_prompt = (
            f"You are a coding assistant helping a student build a personal project.\n"
            f"The student is working in {language} on a project called \"{title}\".\n"
        )
        if description:
            system_prompt += f"Project description: {description}\n"
        if code_snippet:
            system_prompt += (
                f"\nCurrent code:\n```{language}\n{code_snippet}\n```\n"
            )
        system_prompt += (
            "\nHelp the student build their project. You can write code, debug errors, "
            "suggest architecture, refactor, explain concepts, and provide complete "
            "solutions when asked. This is their personal project — treat them like "
            "a developer, not a student taking a test. Be direct and helpful."
        )

        # Prepend system prompt as first user message if not already present
        full_contents = [
            {"role": "user", "parts": [{"text": system_prompt}]},
            {"role": "model", "parts": [{"text": "Understood. I'm ready to help you build your project!"}]},
        ] + contents

        api_key = config.GEMINI_API_KEY
        if not api_key:
            return jsonify({"error": "Server configuration error: AI API Key missing"}), 500

        model = data.get("model", config.GEMINI_MODEL or "gemini-2.5-flash")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/{model}:generateContent?key={api_key}"
        )

        response = requests.post(
            url,
            json={"contents": full_contents},
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        if not response.ok:
            return jsonify(response.json()), response.status_code

        return jsonify(response.json()), 200
    except requests.exceptions.Timeout:
        logger.error("project_assistant: Gemini request timed out for item %s", item_id)
        return jsonify({"error": "AI request timed out. Please try again."}), 504
    except Exception as e:
        logger.error("project_assistant error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@bp.route("/api/portfolio/analytics", methods=["GET"])
@require_auth
def get_analytics():
    """View count and basic stats for own portfolio."""
    try:
        conn = get_db_connection()
        profile, err = _require_portfolio(conn, g.user_id)
        if err:
            return err

        view_count = repo.get_view_count(conn, profile[0])
        return jsonify({"view_count": view_count}), 200
    except Exception as e:
        logger.error("get_analytics error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ---------------------------------------------------------------------------
# Public API — no auth required
# ---------------------------------------------------------------------------

@bp.route("/api/portfolio/public/<slug>", methods=["GET"])
def public_portfolio_api(slug):
    """JSON API for a public portfolio page."""
    try:
        conn = get_db_connection()
        profile = repo.get_profile_by_slug(conn, slug)
        if not profile:
            return jsonify({"error": "Portfolio not found."}), 404

        if not profile[13]:  # is_public column
            return jsonify({"error": "This portfolio is private."}), 403

        # Record view
        referrer = request.referrer
        repo.record_view(conn, profile[0], referrer)
        conn.commit()

        view_count = repo.get_view_count(conn, profile[0])
        items = repo.get_items(conn, profile[0], include_hidden=False)

        return jsonify({
            "profile": svc.profile_to_dict(profile),
            "items": [svc.item_to_dict(r) for r in items],
            "view_count": view_count,
        }), 200
    except Exception as e:
        logger.error("public_portfolio_api error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ---------------------------------------------------------------------------
# Page routes — Jinja2 templates
# ---------------------------------------------------------------------------

@bp.route("/portfolio", methods=["GET"])
def portfolio_dashboard():
    """Portfolio management dashboard (auth enforced client-side via JS)."""
    return render_template("portfolio/dashboard.html")


@bp.route("/portfolio/settings", methods=["GET"])
def portfolio_settings():
    """Portfolio settings page."""
    return render_template("portfolio/settings.html")


@bp.route("/portfolio/projects/<item_id>/edit", methods=["GET"])
def portfolio_project_editor(item_id):
    """Personal project editor page."""
    return render_template("portfolio/project_editor.html", item_id=item_id)


@bp.route("/portfolio/<slug>", methods=["GET"])
def public_portfolio_page(slug):
    """Public-facing portfolio page (no auth required)."""
    return render_template("portfolio/public.html", slug=slug)
