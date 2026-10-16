"""
Generate docs/DATABASE_SCHEMA.md from a live database.

The table listings in that document are generated rather than hand-maintained,
so they cannot drift from the schema the migrations actually produce. The prose
-- the conventions section and the paragraph under each table -- lives in this
file next to the queries, so regenerating keeps it.

Usage:

    createdb analytiq_doc
    DATABASE_URL=postgresql://localhost/analytiq_doc python db_migrate.py
    DATABASE_URL=postgresql://localhost/analytiq_doc \
        python scripts/dump_schema_doc.py > docs/DATABASE_SCHEMA.md

A table present in the database but not placed in a SECTIONS entry below (or the
other way round) is a hard error, so adding a table to the schema forces whoever
added it to describe it here.
"""

import os
import sys

import psycopg2

TYPE_MAP = {
    "character varying": "VARCHAR",
    "character": "CHAR",
    "timestamp without time zone": "TIMESTAMP",
    "timestamp with time zone": "TIMESTAMPTZ",
    "double precision": "FLOAT",
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "boolean": "BOOLEAN",
    "numeric": "NUMERIC",
    "text": "TEXT",
    "jsonb": "JSONB",
    "bytea": "BYTEA",
    "uuid": "UUID",
}

# "a" is PostgreSQL's default when no ON DELETE clause was written. It is
# spelled out rather than left blank so a foreign key nobody decided on is
# visible in this document instead of looking like every other one.
_FK_ACTIONS = {
    "a": " NO ACTION",
    "c": " CASCADE",
    "n": " SET NULL",
    "d": " SET DEFAULT",
    "r": " RESTRICT",
}


# ---------------------------------------------------------------------------
# Catalogue queries
# ---------------------------------------------------------------------------


def all_tables(cur):
    cur.execute(
        """
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r' ORDER BY c.relname
        """
    )
    return [r[0] for r in cur.fetchall()]


def columns(cur, table):
    cur.execute(
        """
        SELECT column_name, data_type, character_maximum_length, numeric_precision,
               numeric_scale, is_nullable, column_default, udt_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return cur.fetchall()


def primary_key(cur, table):
    cur.execute(
        """
        SELECT a.attname FROM pg_constraint c
        JOIN pg_class r ON r.oid = c.conrelid
        JOIN unnest(c.conkey) k(attnum) ON true
        JOIN pg_attribute a ON a.attrelid = r.oid AND a.attnum = k.attnum
        WHERE r.relname = %s AND c.contype = 'p'
        """,
        (table,),
    )
    return {r[0] for r in cur.fetchall()}


def _constraints(cur, table, contype):
    cur.execute(
        """
        SELECT c.conname, pg_get_constraintdef(c.oid) FROM pg_constraint c
        JOIN pg_class r ON r.oid = c.conrelid
        WHERE r.relname = %s AND c.contype = %s ORDER BY c.conname
        """,
        (table, contype),
    )
    return cur.fetchall()


def foreign_keys(cur, table):
    cur.execute(
        """
        SELECT a.attname, cl.relname, af.attname, c.confdeltype
        FROM pg_constraint c
        JOIN pg_class r ON r.oid = c.conrelid
        JOIN pg_class cl ON cl.oid = c.confrelid
        JOIN unnest(c.conkey) k(attnum) ON true
        JOIN unnest(c.confkey) fk(attnum) ON true
        JOIN pg_attribute a ON a.attrelid = r.oid AND a.attnum = k.attnum
        JOIN pg_attribute af ON af.attrelid = cl.oid AND af.attnum = fk.attnum
        WHERE r.relname = %s AND c.contype = 'f'
        """,
        (table,),
    )
    return {
        col: "FK&rarr;`{}.{}`{}".format(ftable, fcol, _FK_ACTIONS.get(on_delete, ""))
        for col, ftable, fcol, on_delete in cur.fetchall()
    }


def indexes(cur, table):
    cur.execute(
        "SELECT indexname, indexdef FROM pg_indexes "
        "WHERE schemaname = 'public' AND tablename = %s ORDER BY indexname",
        (table,),
    )
    return cur.fetchall()


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def fmt_type(data_type, char_len, precision, scale, udt):
    if data_type == "ARRAY":
        base = udt.lstrip("_")
        return "{}[]".format(TYPE_MAP.get(base, base.upper()))
    base = TYPE_MAP.get(data_type, data_type.upper())
    if char_len:
        return "{}({})".format(base, char_len)
    if data_type == "numeric" and precision:
        return "NUMERIC({},{})".format(precision, scale)
    return base


def fmt_default(default):
    if default is None:
        return ""
    if default.startswith("nextval("):
        return "auto"
    for suffix in ("::character varying", "::text[]", "::text", "::jsonb"):
        default = default.replace(suffix, "")
    return "`{}`".format(default)


def render_table(cur, table):
    """Return the markdown block for one table: heading, column table, then constraints."""
    pk = primary_key(cur, table)
    fks = foreign_keys(cur, table)
    uniques = _constraints(cur, table, "u")
    checks = _constraints(cur, table, "c")

    lines = [
        "### `{}`".format(table),
        "",
        "| Column | Type | Null | Default | Notes |",
        "|---|---|---|---|---|",
    ]
    for name, data_type, char_len, precision, scale, nullable, default, udt in columns(cur, table):
        notes = []
        if name in pk:
            notes.append("**PK**")
        if name in fks:
            notes.append(fks[name])
        lines.append(
            "| `{}` | `{}` | {} | {} | {} |".format(
                name,
                fmt_type(data_type, char_len, precision, scale, udt),
                "yes" if nullable == "YES" else "no",
                fmt_default(default),
                " · ".join(notes),
            )
        )
    lines.append("")

    unique_names = {name for name, _ in uniques}
    for _, definition in uniques:
        lines.append("- Unique: `{}`".format(definition))
    for _, definition in checks:
        lines.append("- Check: `{}`".format(definition))
    for name, definition in indexes(cur, table):
        if name.endswith("_pkey") or name in unique_names:
            continue
        definition = definition.split(" ON ", 1)[-1]
        definition = definition.replace("public.", "").replace(" USING btree", "")
        lines.append("- Index `{}`: `{}`".format(name, definition))

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Prose
# ---------------------------------------------------------------------------

PREAMBLE = """# AnalytIQ Database Schema Reference

{count} tables in PostgreSQL (>= 13 -- `gen_random_uuid()` is used as a column default).

The schema has a single home: the numbered SQL files in `migrations/`.
`migrations/000_initial_schema.sql` creates all of it from nothing and each later
migration changes it once, so

```bash
createdb analytiq && python db_migrate.py
```

is the whole setup. Nothing else in the repository creates tables -- the
integration test suite builds its schema by running these same migrations.

The table listings below are generated from a database built exactly that way,
by `scripts/dump_schema_doc.py`; see the end of this file.

## Conventions

- `user_id`, `tenant_id`, `class_id`, `chapter_id` and `exercise_id` are VARCHAR
  **strings** -- UUID text, or a human-readable join code for `class_id` -- never
  integers.
- Tables with an `id SERIAL` primary key also carry a UNIQUE business key, and
  the application joins on the business key. `users.user_id` is the identifier
  that matters; `users.id` is an implementation detail.
- `tenant_id IS NULL` means a platform-level row rather than one belonging to a
  tenant.
- `password_hash IS NULL` means an SSO-only or LTI-only account.
- Timestamps are `TIMESTAMP` (no zone) on the older tables and `TIMESTAMPTZ` on
  everything added from migration 009 onwards. New tables should use TIMESTAMPTZ.
- `exercise_id` columns outside `class_exercises` are deliberately unconstrained:
  they also hold ids of built-in practice exercises, and recorded events outlive
  the exercises they describe.
- Every foreign key states an `ON DELETE` action; none is left on PostgreSQL's
  default `NO ACTION`, which would turn a delete into a foreign-key violation.
  A column that *belongs to* its parent is `CASCADE`; a column that merely
  *records who made the row* -- `created_by`, `blocked_by` -- is `SET NULL`, so
  an announcement, SSO provider, LTI config or blocked address outlives the
  admin who created it and loses only the attribution. This is what makes a user
  deletable whatever they left behind, and
  `tests/integration/test_schema_constraints.py` holds the schema to it.

## Table index

"""

EPILOGUE = """
---

## Regenerating this document

```bash
createdb analytiq_doc
DATABASE_URL=postgresql://localhost/analytiq_doc python db_migrate.py
DATABASE_URL=postgresql://localhost/analytiq_doc \\
    python scripts/dump_schema_doc.py > docs/DATABASE_SCHEMA.md
```

The prose -- the conventions above and the paragraph under each table -- lives in
`scripts/dump_schema_doc.py` next to the catalogue queries. The script fails if
the database contains a table it has no note for, so a new table cannot be added
without describing it.
"""

NOTES = {
    "users": (
        "One row per account, however it authenticates. `user_id` is the application's "
        "identifier -- a UUID string -- and every other table references it rather than "
        "the `id` surrogate key. `password_hash` is NULL for LTI-only and SSO-only "
        "accounts. `role` is one of `student`, `professor`, `tenant_admin`, `superadmin`; "
        "`is_super_admin` is a legacy duplicate of `role = 'superadmin'`. `token_version` "
        "is the JWT revocation counter: every issued token carries it as a `tv` claim and "
        "`require_auth` rejects a token whose claim no longer matches, so bumping it signs "
        "that user out everywhere. `archived_at` soft-deletes users whose tenant was removed."
    ),
    "user_profiles": (
        "Display fields shown on the profile page. Created empty at signup "
        "(`INSERT ... ON CONFLICT DO NOTHING`), so a row exists for every user."
    ),
    "user_settings": "Notification and display toggles. Also created empty at signup.",
    "user_preferences": (
        "Editor language and AI-provider preferences. Also created empty at signup."
    ),
    "password_resets": (
        "Short-lived reset tokens, keyed by email rather than user_id. Rows are deleted "
        "once used; the TTL is `PW_RESET_EXPIRY_HOURS`."
    ),
    "tenants": (
        "An institution. `email_domain` drives automatic tenant assignment at signup, and "
        "`lti_issuer` maps 1:1 with `lti_configurations.issuer`."
    ),
    "tenant_sso_providers": (
        "Per-tenant OIDC configuration. `client_secret` is Fernet-encrypted with the app "
        "`SECRET_KEY`, and the repository layer only ever handles the encrypted value. "
        "`role_mapping` maps a claim value to an AnalytIQ role; `default_role` applies when "
        "nothing matches. SAML is not supported."
    ),
    "lti_configurations": (
        "A registered LMS platform (Canvas, Moodle, ...), one row per issuer/client_id pair."
    ),
    "lti_sessions": (
        "One row per LTI launch; `session_id` is the OIDC `state` parameter. Expired rows "
        "are swept by `expires_at`."
    ),
    "classes": (
        "A professor's class. `class_id` is both the primary key and the join code students "
        "type in. The `lti_*`, `nrps_*` and `ags_*` columns are populated only for classes "
        "created through an LMS launch."
    ),
    "class_enrollments": (
        "Student-to-class membership. The UNIQUE on `(class_id, student_id)` is what makes "
        "enrolling twice a no-op."
    ),
    "class_chapters": (
        "A PDF chapter within a class. The file lives in Supabase Storage (`pdf_url`), with "
        "the raw bytes kept in `pdf_data` as a fallback for deployments that have no storage "
        "configured."
    ),
    "class_exercises": (
        "A coding exercise, usually generated from a chapter PDF. `test_cases` holds "
        "`[{description, input, expected_output, weight}]` and drives output-based grading; "
        "`function_name` is the function students must define. `generation_event_id` links "
        "back to the AI run that produced the exercise."
    ),
    "class_resources": (
        "Supplementary files and links attached to a class. Deliberately carries no foreign "
        "keys -- it predates the conventions used elsewhere."
    ),
    "practice_progress": (
        "Current best result per (user, exercise); the UNIQUE on `(user_id, exercise_id)` is "
        "the upsert's `ON CONFLICT` target. `class_exercise_id` is the link used by the class "
        "progress and leaderboard queries, and is NULL for built-in practice exercises."
    ),
    "exercise_attempts": (
        "Append-only log of every graded submission. `MAX(score)` here is the trusted ceiling "
        "for a client-submitted score."
    ),
    "exercise_ratings": (
        "A student's thumbs-up/down on an exercise, upserted on `(exercise_id, user_id)`. "
        "Feeds exercise-quality analysis."
    ),
    "conversations": (
        "An AI chat thread. Deletes are soft (`deleted = true`), and `conversation_id` rather "
        "than `id` is the key the API and child rows use."
    ),
    "conversation_messages": (
        "Messages within a thread, ordered by `message_order` rather than by timestamp."
    ),
    "ai_agent_digest": (
        "Rolling per-user context injected into the AI system prompt. One row per user, "
        "created at signup."
    ),
    "ai_agent_memory": (
        "Individual long-lived facts the assistant remembers for a user. Replaced wholesale "
        "on update."
    ),
    "exercise_generation_events": (
        "One row per Gemini generation call: what went in, what we asked for, and what came "
        "out. `exercise_id` and `tenant_id` are unconstrained so an event survives deletion "
        "of what it refers to."
    ),
    "exercise_outcome_events": (
        "One row per graded submission, linked back to the generation event, so model inputs "
        "can be correlated with student outcomes."
    ),
    "exercise_quality_scores": (
        "Per-exercise rollup of the two event tables, recomputed by a Celery task. One row "
        "per exercise."
    ),
    "portfolio_profiles": (
        "A student's public portfolio, served at `/portfolio/{slug}`. `is_public` gates "
        "visibility; the `github_*` columns drive optional sync to a repository."
    ),
    "portfolio_items": (
        "An entry in a portfolio: a class exercise, a personal project, or an external link. "
        "The `source_*` columns are denormalised provenance shown on the public page."
    ),
    "portfolio_views": "Anonymous view counter for public portfolios.",
    "platform_config": (
        "Key-value runtime settings, read and written by the superadmin dashboard. Migration "
        "003 defines a wider table (with `updated_by` and `updated_at`), but every database "
        "already had the key/value table by the time 003 ran, so this two-column shape is "
        "what exists -- and only `key` and `value` are ever read."
    ),
    "announcements": (
        "Banner messages. `tenant_id IS NULL` means platform-wide, and an empty `target_roles` "
        "means all roles."
    ),
    "ip_blocklist": "Addresses refused by the request middleware.",
    "contact_submissions": (
        "Public contact-form submissions, read by the superadmin dashboard. `user_id` is NULL "
        "for signed-out visitors."
    ),
    "audit_log": (
        "FERPA mutation log, written by `core/audit.py` inside the same transaction as the "
        "mutation it describes, so a rolled-back operation leaves no audit row. `user_id` is "
        "unconstrained TEXT so a record outlives the actor it names."
    ),
    "schema_migrations": (
        "Which migration files have been applied, one row per filename. Created and managed "
        "exclusively by `db_migrate.py`."
    ),
}

SECTIONS = [
    (
        "Identity and accounts",
        ["users", "user_profiles", "user_settings", "user_preferences", "password_resets"],
    ),
    ("Multi-tenancy and SSO", ["tenants", "tenant_sso_providers"]),
    ("LTI 1.3", ["lti_configurations", "lti_sessions"]),
    (
        "Course content",
        ["classes", "class_enrollments", "class_chapters", "class_exercises", "class_resources"],
    ),
    ("Progress and grading", ["practice_progress", "exercise_attempts", "exercise_ratings"]),
    (
        "AI assistant",
        ["conversations", "conversation_messages", "ai_agent_digest", "ai_agent_memory"],
    ),
    (
        "Data flywheel",
        [
            "exercise_generation_events",
            "exercise_outcome_events",
            "exercise_quality_scores",
        ],
    ),
    ("Student portfolios", ["portfolio_profiles", "portfolio_items", "portfolio_views"]),
    (
        "Platform administration",
        ["platform_config", "announcements", "ip_blocklist", "contact_submissions", "audit_log"],
    ),
    ("Infrastructure", ["schema_migrations"]),
]


def build_document(cur):
    tables = all_tables(cur)

    placed = [t for _, section in SECTIONS for t in section]
    unplaced = sorted(set(tables) - set(placed))
    unknown = sorted(set(placed) - set(tables))
    undocumented = sorted(t for t in tables if t not in NOTES)
    if unplaced:
        raise SystemExit("tables not placed in a SECTIONS entry: {}".format(unplaced))
    if unknown:
        raise SystemExit("SECTIONS names tables that are not in the database: {}".format(unknown))
    if undocumented:
        raise SystemExit("tables with no entry in NOTES: {}".format(undocumented))

    out = [PREAMBLE.format(count=len(tables))]
    for title, section in SECTIONS:
        links = " · ".join("[`{0}`](#{0})".format(t) for t in section)
        out.append("**{}** -- {}\n\n".format(title, links))
    out.append("---\n")

    for title, section in SECTIONS:
        out.append("\n## {}\n".format(title))
        for table in section:
            heading, _, table_md = render_table(cur, table).partition("\n")
            out.append("\n{}\n".format(heading))
            out.append("\n{}\n".format(NOTES[table]))
            out.append("\n{}".format(table_md.lstrip("\n")))

    out.append(EPILOGUE)
    return "".join(out)


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set")
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            sys.stdout.write(build_document(cur))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
