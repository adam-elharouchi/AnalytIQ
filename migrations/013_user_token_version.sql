-- 013_user_token_version.sql
-- Per-user JWT revocation counter. Every issued JWT embeds the user's current
-- token_version as a "tv" claim; require_auth rejects a token whose tv does not
-- match the stored value. Bumping this column invalidates all outstanding
-- tokens for that user (used on password change/reset and account disable).

ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;
