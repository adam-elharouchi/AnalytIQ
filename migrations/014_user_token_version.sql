-- 014_user_token_version.sql
-- Per-user JWT revocation counter. Every issued JWT embeds the user's current
-- token_version as a "tv" claim; require_auth rejects a token whose tv does not
-- match the stored value. Bumping this column invalidates all outstanding
-- tokens for that user (used on password change/reset and account disable).
--
-- Renamed from 013_user_token_version.sql, which collided with
-- 013_create_portfolio_tables.sql. Databases that already applied it under the
-- old name will apply this file once more; the statement below is a no-op when
-- the column exists, so the only effect is a second row in schema_migrations.
-- The relative order is unchanged: "013_create..." sorted before "013_user..."
-- and still sorts before "014_".

ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;
