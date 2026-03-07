-- Migration 006: core application tables (password_resets, audit_log)
-- Safe to run multiple times (IF NOT EXISTS guards).

-- ---------------------------------------------------------------------------
-- 1. password_resets
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS password_resets (
    id         SERIAL       PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    token      VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP    NOT NULL,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets (token);
CREATE INDEX IF NOT EXISTS idx_password_resets_email ON password_resets (email);

-- ---------------------------------------------------------------------------
-- 2. audit_log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id            BIGSERIAL    PRIMARY KEY,
    user_id       TEXT,
    action        TEXT         NOT NULL,
    resource_type TEXT,
    resource_id   TEXT,
    ip_address    TEXT,
    details       JSONB,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id    ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at DESC);
