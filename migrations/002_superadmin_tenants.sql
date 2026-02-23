-- Migration 002: Super Admin & Multi-Tenant Integration
-- Safe to run multiple times (IF NOT EXISTS / IF EXISTS guards).

-- ---------------------------------------------------------------------------
-- 1. Create tenants table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(255) NOT NULL,
    lti_issuer VARCHAR(500) UNIQUE, -- Maps 1:1 with lti_configurations.issuer
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 2. Extend users table
-- ---------------------------------------------------------------------------
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255) REFERENCES tenants(tenant_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS is_super_admin BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS account_status VARCHAR(50) DEFAULT 'active';

-- ---------------------------------------------------------------------------
-- 3. Extend classes table
-- ---------------------------------------------------------------------------
ALTER TABLE classes
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255) REFERENCES tenants(tenant_id) ON DELETE SET NULL;

-- ---------------------------------------------------------------------------
-- 4. Extend lti_configurations table
-- ---------------------------------------------------------------------------
ALTER TABLE lti_configurations
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255) REFERENCES tenants(tenant_id) ON DELETE CASCADE;
