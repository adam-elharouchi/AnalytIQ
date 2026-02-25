-- Migration 004: SSO Providers & tenant_admin Role
-- Safe to run multiple times (IF NOT EXISTS / IF EXISTS guards).

-- ---------------------------------------------------------------------------
-- 1. Create tenant_sso_providers table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenant_sso_providers (
    provider_id             VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id               VARCHAR(255) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    provider_name           VARCHAR(100) NOT NULL,
    -- provider_type: 'google' | 'microsoft' | 'oidc' (saml deferred — requires native libs)
    provider_type           VARCHAR(20)  NOT NULL,
    client_id               TEXT         NOT NULL,
    client_secret           TEXT         NOT NULL, -- Fernet-encrypted with app SECRET_KEY
    -- OIDC discovery endpoint (e.g. https://accounts.google.com/.well-known/openid-configuration)
    discovery_url           TEXT         NOT NULL,
    -- Optional: restrict which email domains may sign in via this provider
    allowed_domains         TEXT[],
    -- Which OIDC claim carries the role value (e.g. 'groups', 'department', 'email')
    role_mapping_attribute  VARCHAR(100),
    -- JSON map from claim value → AnalytIQ role, e.g. {"Staff":"professor","Students":"student"}
    role_mapping            JSONB        DEFAULT '{}',
    default_role            VARCHAR(50)  DEFAULT 'student',
    is_enabled              BOOLEAN      DEFAULT true,
    created_by              VARCHAR(255) REFERENCES users(user_id) ON DELETE SET NULL,
    created_at              TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sso_providers_tenant
    ON tenant_sso_providers (tenant_id);

CREATE INDEX IF NOT EXISTS idx_sso_providers_enabled
    ON tenant_sso_providers (is_enabled)
    WHERE is_enabled = true;

-- ---------------------------------------------------------------------------
-- 2. Extend users table: SSO identity columns
-- ---------------------------------------------------------------------------
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS sso_provider_id VARCHAR(255)
        REFERENCES tenant_sso_providers(provider_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS sso_subject TEXT;

-- Unique constraint: one user per (provider, subject) pair, ignoring NULLs
CREATE UNIQUE INDEX IF NOT EXISTS uq_sso_user_identity
    ON users (sso_provider_id, sso_subject)
    WHERE sso_provider_id IS NOT NULL;
