"""
Guards on the migrations/ directory itself.

These are cheap structural checks, not database tests: they run without a
server and protect the two properties the migration runner relies on —
a single total order, and files that are safe to apply to a database that
already has them.
"""

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

#: Destructive statements. 000_initial_schema.sql is applied to every existing
#: deployment as well as to new ones, so it must not contain any of these.
_DESTRUCTIVE = re.compile(
    r"\b(DROP\s+(TABLE|COLUMN|CONSTRAINT|INDEX|DATABASE|SCHEMA)"
    r"|ALTER\s+COLUMN"
    r"|RENAME\s+(TO|COLUMN)"
    r"|TRUNCATE"
    r"|DELETE\s+FROM"
    r"|UPDATE\s+\w+\s+SET)\b",
    re.IGNORECASE,
)


def _sql_files():
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _strip_comments(sql):
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def test_migrations_directory_is_not_empty():
    assert _sql_files(), f"no migrations found in {MIGRATIONS_DIR}"


def test_baseline_migration_exists():
    """A fresh database is built by 000; without it nothing else can apply."""
    assert (MIGRATIONS_DIR / "000_initial_schema.sql").is_file()


@pytest.mark.parametrize("path", _sql_files(), ids=lambda p: p.name)
def test_filename_is_a_numbered_migration(path):
    assert re.fullmatch(
        r"\d{3}_[a-z0-9_]+\.sql", path.name
    ), f"{path.name} does not match NNN_lower_snake_case.sql"


def test_numeric_prefixes_are_unique():
    """Two files sharing a number have no defined order relative to each other.

    db_migrate.py sorts by full filename, so a collision silently depends on the
    rest of the name — which is how 013_create_portfolio_tables.sql and
    013_user_token_version.sql ended up adjacent before the latter became 014.
    """
    seen = {}
    for path in _sql_files():
        prefix = path.name[:3]
        seen.setdefault(prefix, []).append(path.name)
    collisions = {k: v for k, v in seen.items() if len(v) > 1}
    assert not collisions, f"duplicate migration numbers: {collisions}"


@pytest.mark.parametrize("path", _sql_files(), ids=lambda p: p.name)
def test_create_statements_are_guarded(path):
    """Every migration must be safe to re-apply (the runner makes no promises)."""
    sql = _strip_comments(path.read_text())
    for match in re.finditer(r"CREATE\s+(?:UNIQUE\s+)?(TABLE|INDEX)\s+(\S+)", sql, re.IGNORECASE):
        kind, following = match.group(1).upper(), match.group(2).upper()
        assert following == "IF", (
            f"{path.name}: CREATE {kind} without IF NOT EXISTS "
            f"(at {sql[match.start():match.start() + 60]!r})"
        )


def test_baseline_migration_is_non_destructive():
    """000 runs against already-migrated production databases too.

    It may only create things and add columns, so that applying it there is a
    no-op. Anything that rewrites or removes existing structure belongs in a
    new, higher-numbered migration.
    """
    sql = _strip_comments((MIGRATIONS_DIR / "000_initial_schema.sql").read_text())
    found = sorted({m.group(0).upper() for m in _DESTRUCTIVE.finditer(sql)})
    assert not found, f"000_initial_schema.sql contains destructive SQL: {found}"
