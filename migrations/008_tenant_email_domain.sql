-- Migration 008: Add email_domain to tenants for auto-assignment at signup
-- Safe to run multiple times (IF NOT EXISTS / IF EXISTS guards).

-- ---------------------------------------------------------------------------
-- 1. Add email_domain column (e.g. "hult.edu", "student.hult.edu")
--    NULL means no auto-assignment for that tenant.
-- ---------------------------------------------------------------------------
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS email_domain VARCHAR(255);

-- ---------------------------------------------------------------------------
-- 2. Unique index so two tenants cannot claim the same domain
-- ---------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_email_domain
    ON tenants (email_domain)
    WHERE email_domain IS NOT NULL;
