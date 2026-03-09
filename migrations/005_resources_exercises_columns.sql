-- Migration 005: class_resources table + class_exercises column additions
-- Safe to run multiple times (IF NOT EXISTS / DO $$ guards).

-- ---------------------------------------------------------------------------
-- 1. class_resources table (create if not already present)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS class_resources (
    resource_id   VARCHAR(255) PRIMARY KEY,
    class_id      VARCHAR(255) NOT NULL,
    user_id       VARCHAR(255) NOT NULL,
    title         VARCHAR(255) NOT NULL,
    description   TEXT,
    resource_type VARCHAR(50)  NOT NULL,
    resource_url  TEXT,
    file_data     BYTEA,
    filename      VARCHAR(255),
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 2. class_resources — add missing columns for older deployments
-- ---------------------------------------------------------------------------
ALTER TABLE class_resources ADD COLUMN IF NOT EXISTS user_id       VARCHAR(255) NOT NULL DEFAULT 'admin';
ALTER TABLE class_resources ADD COLUMN IF NOT EXISTS resource_type VARCHAR(255);
ALTER TABLE class_resources ADD COLUMN IF NOT EXISTS file_data     BYTEA;
ALTER TABLE class_resources ADD COLUMN IF NOT EXISTS filename      VARCHAR(255);

-- Rename legacy "type" column to "resource_type" (guard: skip if type doesn't exist)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'class_resources' AND column_name = 'type'
    ) THEN
        UPDATE class_resources
           SET resource_type = type
         WHERE resource_type IS NULL OR resource_type = '';
        ALTER TABLE class_resources DROP COLUMN type;
    END IF;
END$$;

-- ---------------------------------------------------------------------------
-- 3. class_exercises — add missing columns for older deployments
-- ---------------------------------------------------------------------------
ALTER TABLE class_exercises ADD COLUMN IF NOT EXISTS solution_code   TEXT;
ALTER TABLE class_exercises ADD COLUMN IF NOT EXISTS exercise_number INTEGER DEFAULT 1;
ALTER TABLE class_exercises ADD COLUMN IF NOT EXISTS created_by      VARCHAR(255);
