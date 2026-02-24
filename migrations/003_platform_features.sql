-- ============================================================================
-- Migration 003 — Platform Features
-- Adds: platform_config, announcements, ip_blocklist,
--        requires_password_reset + last_login columns on users.
-- Idempotent: all statements use IF NOT EXISTS / ON CONFLICT DO NOTHING.
-- ============================================================================

-- --------------------------------------------------------------------------
-- 1. Platform key-value config (maintenance mode, registration gate, etc.)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS platform_config (
    key        VARCHAR(100) PRIMARY KEY,
    value      TEXT         NOT NULL DEFAULT '',
    updated_by VARCHAR(255) REFERENCES users(user_id) ON DELETE SET NULL,
    updated_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- Seed defaults (do not overwrite if already present)
INSERT INTO platform_config (key, value) VALUES
    ('maintenance_mode',    'false'),
    ('maintenance_message', 'AnalytIQ is temporarily down for maintenance. Please try again shortly.'),
    ('registration_open',   'true')
ON CONFLICT (key) DO NOTHING;

-- --------------------------------------------------------------------------
-- 2. Platform-wide announcements
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS announcements (
    announcement_id VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    title           VARCHAR(255) NOT NULL,
    message         TEXT         NOT NULL,
    type            VARCHAR(20)  NOT NULL DEFAULT 'info',  -- info | warning | danger | success
    target_roles    TEXT[]       DEFAULT '{}',             -- empty = all roles
    is_active       BOOLEAN      DEFAULT TRUE,
    expires_at      TIMESTAMP,
    created_by      VARCHAR(255) REFERENCES users(user_id) ON DELETE SET NULL,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------------
-- 3. IP blocklist
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ip_blocklist (
    id         SERIAL       PRIMARY KEY,
    ip_address VARCHAR(100) NOT NULL UNIQUE,
    reason     TEXT,
    blocked_by VARCHAR(255) REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------------
-- 4. Extended user columns
-- --------------------------------------------------------------------------
ALTER TABLE users ADD COLUMN IF NOT EXISTS requires_password_reset BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;
