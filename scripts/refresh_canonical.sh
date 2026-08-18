#!/bin/bash
# Pulls the canonical usage numbers straight from the production database and
# prints them as a markdown table for reports/metrics-engineer/CANONICAL_NUMBERS.md.
#
# Why this exists: the weekly refresh (B3) was blamed on "no production DB access
# from this machine," but scripts/backup_db.sh has been reaching Supabase through a
# containerised client all along. Same approach here — there is no host psql either.
#
# Credential discipline matches backup_db.sh and send_digest.py: DATABASE_URL is
# sourced inside this script and never echoed, and the output is AGGREGATES ONLY
# (guardrail 3 — no agent handles credentials or student personal data).
#
# The two active-* definitions below are copied from blueprints/superadmin.py as
# shipped in 14f7721, so this reports what the product reports. If they ever drift,
# this script is wrong and the fix belongs here, not in the numbers.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PG_IMAGE="${PG_IMAGE:-postgres:17-alpine@sha256:18cfe3ef5e6815560c98237d6216d1e5119702fb0f3894c8785dd58b8bbe5d73}"

if [ -f "$HOME/.analytiq_env" ]; then source "$HOME/.analytiq_env"; fi
if [ -z "${DATABASE_URL:-}" ] && [ -f "$REPO/.env" ]; then
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$REPO/.env" | head -1 | cut -d= -f2- | tr -d '"'"'"'')"
fi
[ -n "${DATABASE_URL:-}" ] || { echo "DATABASE_URL not set" >&2; exit 1; }

SQL=$(cat <<'EOSQL'
SELECT 'Total users',                    COUNT(*)::text FROM users
UNION ALL SELECT '  Students',           COUNT(*)::text FROM users WHERE role='student'
UNION ALL SELECT '  Professors',         COUNT(*)::text FROM users WHERE role='professor'
UNION ALL SELECT '  Tenant admins',      COUNT(*)::text FROM users WHERE role='tenant_admin'
UNION ALL SELECT '  Superadmins',        COUNT(*)::text FROM users WHERE role='superadmin'
UNION ALL SELECT 'Tenants',              COUNT(*)::text FROM tenants
UNION ALL SELECT 'Classes (total)',      COUNT(*)::text FROM classes
UNION ALL SELECT 'Classes (active)',     (SELECT COUNT(*) FROM classes c
                                           WHERE EXISTS (SELECT 1 FROM class_enrollments ce WHERE ce.class_id=c.class_id)
                                             AND EXISTS (SELECT 1 FROM practice_progress pp
                                                          WHERE pp.class_id=c.class_id
                                                            AND pp.updated_at >= NOW() - INTERVAL '30 days'))::text
UNION ALL SELECT 'Chapters',             COUNT(*)::text FROM class_chapters
UNION ALL SELECT 'Exercises',            COUNT(*)::text FROM class_exercises
UNION ALL SELECT 'Completions',          (SELECT COUNT(*) FROM practice_progress WHERE completed = TRUE)::text
UNION ALL SELECT 'WAU (7-day active)',   COUNT(*) FILTER (WHERE last_login  >= NOW() - INTERVAL '7 days')::text  FROM users
UNION ALL SELECT 'MAU (30-day active)',  COUNT(*) FILTER (WHERE last_login  >= NOW() - INTERVAL '30 days')::text FROM users
UNION ALL SELECT 'New users (7d)',       COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days')::text  FROM users
UNION ALL SELECT 'New users (30d)',      COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days')::text FROM users;
EOSQL
)

docker run --rm -i -e PGCONNECT_TIMEOUT=20 "$PG_IMAGE" \
  psql "$DATABASE_URL" -At -F '|' -c "$SQL"|
  awk -F'|' 'BEGIN{print "| Metric | Value |"; print "|---|---|"} {printf "| %s | %s |\n",$1,$2}'
