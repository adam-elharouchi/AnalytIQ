-- Migration 012: Add tenant_id to announcements + archived_at to users
-- Safe to run multiple times (IF NOT EXISTS guards).

-- ---------------------------------------------------------------------------
-- 1. announcements.tenant_id — scopes announcements to a tenant (NULL = platform-wide)
-- ---------------------------------------------------------------------------
ALTER TABLE announcements
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255)
        REFERENCES tenants(tenant_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_announcements_tenant_id ON announcements (tenant_id);

-- ---------------------------------------------------------------------------
-- 2. users.archived_at — soft-delete timestamp for users whose tenant was removed
-- ---------------------------------------------------------------------------
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_users_archived_at ON users (archived_at)
    WHERE archived_at IS NOT NULL;
