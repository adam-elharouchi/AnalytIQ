"""
Portfolio Repository — SQL operations for portfolio profiles, items, and views.

Every function receives a DB *connection* and returns plain Python data.
The caller (blueprint) is responsible for commit / rollback / connection lifecycle.
"""

import json
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Portfolio Profile
# ---------------------------------------------------------------------------


def get_profile_by_user(conn, user_id):
    """Return the portfolio profile row for a user, or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, user_id, slug, portfolio_title, display_name, headline, bio,
               avatar_url, accent_color, layout_style, linkedin_url, github_username,
               personal_website, is_public, github_username, github_repo_name,
               github_sync_enabled, github_last_synced_at, created_at, updated_at
        FROM portfolio_profiles
        WHERE user_id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def get_profile_by_slug(conn, slug):
    """Return the portfolio profile row for a public slug, or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, user_id, slug, portfolio_title, display_name, headline, bio,
               avatar_url, accent_color, layout_style, linkedin_url, github_username,
               personal_website, is_public, github_repo_name,
               github_sync_enabled, github_last_synced_at, created_at, updated_at
        FROM portfolio_profiles
        WHERE slug = %s
        """,
        (slug,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def slug_exists(conn, slug, exclude_user_id=None):
    """Return True if slug is already taken (optionally excluding current user)."""
    cur = conn.cursor()
    if exclude_user_id:
        cur.execute(
            "SELECT 1 FROM portfolio_profiles WHERE slug = %s AND user_id != %s",
            (slug, exclude_user_id),
        )
    else:
        cur.execute(
            "SELECT 1 FROM portfolio_profiles WHERE slug = %s",
            (slug,),
        )
    exists = cur.fetchone() is not None
    cur.close()
    return exists


def insert_profile(conn, profile_id, user_id, slug, portfolio_title, display_name):
    """Create a new portfolio profile row."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO portfolio_profiles (id, user_id, slug, portfolio_title, display_name)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (profile_id, user_id, slug, portfolio_title, display_name),
    )
    cur.close()


def update_profile(conn, user_id, fields: dict):
    """Update editable profile fields. `fields` is a dict of column→value."""
    if not fields:
        return
    cols = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [user_id]
    cur = conn.cursor()
    cur.execute(
        f"UPDATE portfolio_profiles SET {cols}, updated_at = NOW() WHERE user_id = %s",
        values,
    )
    cur.close()


def delete_profile(conn, user_id):
    """Delete the portfolio profile (cascade deletes items and views)."""
    cur = conn.cursor()
    cur.execute("DELETE FROM portfolio_profiles WHERE user_id = %s", (user_id,))
    cur.close()


# ---------------------------------------------------------------------------
# Portfolio Items
# ---------------------------------------------------------------------------


def get_items(conn, portfolio_id, include_hidden=True):
    """Return all items for a portfolio ordered by pinned first, then display_order."""
    cur = conn.cursor()
    where = "" if include_hidden else "AND is_visible = TRUE AND (project_status IS NULL OR project_status = 'published')"
    cur.execute(
        f"""
        SELECT id, portfolio_id, item_type, exercise_id, class_id,
               title, description, language, code_content, last_output, last_error,
               last_run_at, project_status, external_url, tags,
               source_class_name, source_chapter_name, source_institution,
               score, show_score, display_order, is_visible, is_pinned,
               github_synced, github_file_path, last_saved_at, completed_at,
               created_at, updated_at
        FROM portfolio_items
        WHERE portfolio_id = %s {where}
        ORDER BY is_pinned DESC, display_order ASC, created_at DESC
        """,
        (portfolio_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_item(conn, item_id, portfolio_id=None):
    """Return a single item row, optionally checking portfolio ownership."""
    cur = conn.cursor()
    if portfolio_id:
        cur.execute(
            """
            SELECT id, portfolio_id, item_type, exercise_id, class_id,
                   title, description, language, code_content, last_output, last_error,
                   last_run_at, project_status, external_url, tags,
                   source_class_name, source_chapter_name, source_institution,
                   score, show_score, display_order, is_visible, is_pinned,
                   github_synced, github_file_path, last_saved_at, completed_at,
                   created_at, updated_at
            FROM portfolio_items
            WHERE id = %s AND portfolio_id = %s
            """,
            (item_id, portfolio_id),
        )
    else:
        cur.execute(
            """
            SELECT id, portfolio_id, item_type, exercise_id, class_id,
                   title, description, language, code_content, last_output, last_error,
                   last_run_at, project_status, external_url, tags,
                   source_class_name, source_chapter_name, source_institution,
                   score, show_score, display_order, is_visible, is_pinned,
                   github_synced, github_file_path, last_saved_at, completed_at,
                   created_at, updated_at
            FROM portfolio_items WHERE id = %s
            """,
            (item_id,),
        )
    row = cur.fetchone()
    cur.close()
    return row


def insert_item(conn, item):
    """Insert a new portfolio item. `item` is a dict of column→value."""
    cur = conn.cursor()
    tags = item.get("tags", [])
    if isinstance(tags, list):
        tags = json.dumps(tags)
    cur.execute(
        """
        INSERT INTO portfolio_items (
            id, portfolio_id, item_type, exercise_id, class_id,
            title, description, language, code_content,
            project_status, external_url, tags,
            source_class_name, source_chapter_name, source_institution,
            score, show_score, display_order, is_visible, is_pinned,
            completed_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s
        )
        """,
        (
            item["id"],
            item["portfolio_id"],
            item["item_type"],
            item.get("exercise_id"),
            item.get("class_id"),
            item["title"],
            item.get("description"),
            item.get("language"),
            item.get("code_content"),
            item.get("project_status", "draft"),
            item.get("external_url"),
            tags,
            item.get("source_class_name"),
            item.get("source_chapter_name"),
            item.get("source_institution"),
            item.get("score"),
            item.get("show_score", False),
            item.get("display_order", 0),
            item.get("is_visible", True),
            item.get("is_pinned", False),
            item.get("completed_at"),
        ),
    )
    cur.close()


def update_item(conn, item_id, portfolio_id, fields: dict):
    """Update editable item fields."""
    if not fields:
        return
    if "tags" in fields and isinstance(fields["tags"], list):
        fields["tags"] = json.dumps(fields["tags"])
    cols = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [item_id, portfolio_id]
    cur = conn.cursor()
    cur.execute(
        f"UPDATE portfolio_items SET {cols}, updated_at = NOW() WHERE id = %s AND portfolio_id = %s",
        values,
    )
    cur.close()


def update_item_code(conn, item_id, portfolio_id, code_content):
    """Save code for a personal project item."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE portfolio_items
        SET code_content = %s, last_saved_at = NOW(), updated_at = NOW()
        WHERE id = %s AND portfolio_id = %s AND item_type = 'personal_project'
        """,
        (code_content, item_id, portfolio_id),
    )
    cur.close()


def update_item_run_result(conn, item_id, portfolio_id, stdout, stderr):
    """Store last run output for a personal project."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE portfolio_items
        SET last_output = %s, last_error = %s, last_run_at = NOW(), updated_at = NOW()
        WHERE id = %s AND portfolio_id = %s
        """,
        (stdout, stderr, item_id, portfolio_id),
    )
    cur.close()


def delete_item(conn, item_id, portfolio_id):
    """Delete an item from a portfolio."""
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM portfolio_items WHERE id = %s AND portfolio_id = %s",
        (item_id, portfolio_id),
    )
    cur.close()


def reorder_items(conn, portfolio_id, ordered_ids: list):
    """Set display_order based on the position in ordered_ids list."""
    cur = conn.cursor()
    for position, item_id in enumerate(ordered_ids):
        cur.execute(
            "UPDATE portfolio_items SET display_order = %s WHERE id = %s AND portfolio_id = %s",
            (position, item_id, portfolio_id),
        )
    cur.close()


# ---------------------------------------------------------------------------
# Available exercises for import
# ---------------------------------------------------------------------------


def get_importable_exercises(conn, user_id, portfolio_id):
    """
    Return completed exercises not yet in the portfolio.
    Joins practice_progress with class_exercises for title/language.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            pp.exercise_id,
            COALESCE(ce.title, pp.exercise_title) AS title,
            ce.language,
            pp.best_score,
            pp.last_completed_at,
            c.class_name,
            ch.name AS chapter_name
        FROM practice_progress pp
        LEFT JOIN class_exercises ce ON ce.exercise_id = pp.exercise_id
        LEFT JOIN classes c ON c.class_id = pp.class_id
        LEFT JOIN chapters ch ON ch.chapter_id = ce.chapter_id
        WHERE pp.user_id = %s
          AND pp.completed = TRUE
          AND pp.exercise_id NOT IN (
              SELECT exercise_id FROM portfolio_items
              WHERE portfolio_id = %s AND exercise_id IS NOT NULL
          )
        ORDER BY pp.last_completed_at DESC
        """,
        (user_id, portfolio_id),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


# ---------------------------------------------------------------------------
# View tracking
# ---------------------------------------------------------------------------


def record_view(conn, portfolio_id, referrer=None):
    """Insert a view record for the public portfolio page."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO portfolio_views (id, portfolio_id, referrer)
        VALUES (gen_random_uuid()::text, %s, %s)
        """,
        (portfolio_id, referrer),
    )
    cur.close()


def get_view_count(conn, portfolio_id):
    """Return total view count for a portfolio."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM portfolio_views WHERE portfolio_id = %s",
        (portfolio_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else 0
