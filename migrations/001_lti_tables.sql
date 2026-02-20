-- Migration 001: LTI 1.3 Integration
-- Run against production DB before deploying LTI blueprint.
-- Safe to run multiple times (IF NOT EXISTS / IF EXISTS guards).

-- ---------------------------------------------------------------------------
-- 1. Extend users table
-- ---------------------------------------------------------------------------
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS lti_sub    VARCHAR(255),
    ADD COLUMN IF NOT EXISTS lti_issuer VARCHAR(500);

-- Only add unique constraint if it doesn't exist yet
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'users_lti_sub_lti_issuer_key'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_lti_sub_lti_issuer_key
            UNIQUE (lti_sub, lti_issuer);
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 2. Extend classes table
-- ---------------------------------------------------------------------------
ALTER TABLE classes
    ADD COLUMN IF NOT EXISTS lti_context_id   VARCHAR(500),
    ADD COLUMN IF NOT EXISTS lti_issuer       VARCHAR(500),
    ADD COLUMN IF NOT EXISTS nrps_context_url TEXT,
    ADD COLUMN IF NOT EXISTS ags_enabled      BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ags_lineitems_url TEXT;

-- ---------------------------------------------------------------------------
-- 3. LMS platform registrations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lti_configurations (
    config_id      VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    platform_name  VARCHAR(255) NOT NULL,
    issuer         VARCHAR(500) NOT NULL,
    client_id      VARCHAR(255) NOT NULL,
    auth_login_url TEXT        NOT NULL,
    auth_token_url TEXT        NOT NULL,
    key_set_url    TEXT        NOT NULL,
    deployment_ids TEXT[]      DEFAULT '{}',
    created_by     VARCHAR(255) REFERENCES users(user_id) ON DELETE SET NULL,
    created_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (issuer, client_id)
);

-- ---------------------------------------------------------------------------
-- 4. LTI launch sessions (OIDC state + post-launch context)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lti_sessions (
    session_id       VARCHAR(255) PRIMARY KEY,
    user_id          VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    class_id         VARCHAR(255) REFERENCES classes(class_id) ON DELETE SET NULL,
    nrps_context_url TEXT,
    lti_context_id   TEXT,
    issuer           VARCHAR(500),
    client_id        VARCHAR(255),
    launch_data      JSONB,
    expires_at       TIMESTAMP   NOT NULL,
    created_at       TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lti_sessions_user_id  ON lti_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_lti_sessions_class_id ON lti_sessions(class_id);
CREATE INDEX IF NOT EXISTS idx_lti_sessions_expires  ON lti_sessions(expires_at);
