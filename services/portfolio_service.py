"""
Portfolio Service — slug generation and business logic for portfolio management.
"""

import re
import unicodedata
import uuid


def generate_slug(name: str) -> str:
    """
    Generate a URL-safe slug from a name.
    e.g. "Adam El Harouchi" → "adam-el-harouchi"
    """
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name.strip())
    name = re.sub(r"-+", "-", name)
    name = name[:55]  # leave room for suffix
    name = name.strip("-")
    return name or "portfolio"


def unique_slug(base_slug: str, conn, exclude_user_id=None) -> str:
    """
    Return a unique slug derived from base_slug.
    Appends a short random suffix if the base is already taken.
    """
    from repositories import portfolio_repository as repo

    slug = base_slug
    if not repo.slug_exists(conn, slug, exclude_user_id=exclude_user_id):
        return slug

    # Try numbered suffixes
    for i in range(2, 20):
        candidate = f"{base_slug}-{i}"
        if not repo.slug_exists(conn, candidate, exclude_user_id=exclude_user_id):
            return candidate

    # Fall back to random suffix
    suffix = uuid.uuid4().hex[:6]
    return f"{base_slug}-{suffix}"


def new_id() -> str:
    """Generate a new VARCHAR-compatible UUID string."""
    return str(uuid.uuid4())


def portfolio_title_from_name(display_name: str) -> str:
    """Generate a default portfolio title like "Adam's Portfolio"."""
    first = (display_name or "My").split()[0]
    return f"{first}'s Portfolio"


def item_to_dict(row) -> dict:
    """Convert a portfolio_items DB row (tuple) to a dict."""
    import json

    keys = [
        "id", "portfolio_id", "item_type", "exercise_id", "class_id",
        "title", "description", "language", "code_content", "last_output",
        "last_error", "last_run_at", "project_status", "external_url", "tags",
        "source_class_name", "source_chapter_name", "source_institution",
        "score", "show_score", "display_order", "is_visible", "is_pinned",
        "github_synced", "github_file_path", "last_saved_at", "completed_at",
        "created_at", "updated_at",
    ]
    d = dict(zip(keys, row))
    # Normalise tags
    tags = d.get("tags")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    d["tags"] = tags or []
    # Convert datetimes to ISO strings
    for key in ("last_run_at", "last_saved_at", "completed_at", "created_at", "updated_at"):
        if d.get(key):
            d[key] = d[key].isoformat()
    # Convert score to float
    if d.get("score") is not None:
        d["score"] = float(d["score"])
    return d


def profile_to_dict(row) -> dict:
    """Convert a portfolio_profiles DB row (tuple) to a dict (omits token)."""
    keys = [
        "id", "user_id", "slug", "portfolio_title", "display_name",
        "headline", "bio", "avatar_url", "accent_color", "layout_style",
        "linkedin_url", "github_username", "personal_website", "is_public",
        "github_username2", "github_repo_name", "github_sync_enabled",
        "github_last_synced_at", "created_at", "updated_at",
    ]
    d = dict(zip(keys, row))
    d.pop("github_username2", None)
    for key in ("github_last_synced_at", "created_at", "updated_at"):
        if d.get(key):
            d[key] = d[key].isoformat()
    return d
