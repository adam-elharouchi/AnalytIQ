-- ============================================================================
-- Migration 015 — contact_submissions and exercise_ratings
--
-- Two tables the application writes to that no migration ever created:
--
--   * contact_submissions — written by POST /api/contact, read by the superadmin
--     dashboard. Its DDL only existed in scripts/migrate_create_contact_table.py,
--     a one-off script somebody had to remember to run.
--
--   * exercise_ratings — written by POST /api/exercises/<id>/rate. It had no DDL
--     anywhere; the endpoint catches the resulting error and logs "table may not
--     exist yet", so student ratings were silently discarded on every database.
--
-- Both are CREATE TABLE IF NOT EXISTS, so a deployment that already has them
-- (from the one-off script) is unaffected.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. contact_submissions
--    Shape matches scripts/migrate_create_contact_table.py exactly, so existing
--    deployments and new ones agree. user_id is nullable and unconstrained: the
--    contact form works for signed-out visitors.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_submissions (
    submission_id SERIAL       PRIMARY KEY,
    user_id       VARCHAR(255),
    name          VARCHAR(255) NOT NULL,
    email         VARCHAR(255) NOT NULL,
    subject       VARCHAR(255) NOT NULL,
    message       TEXT         NOT NULL,
    status        VARCHAR(50)  DEFAULT 'submitted',
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 2. exercise_ratings
--    One thumbs-up/down per (exercise, user); the endpoint upserts on that pair,
--    so it is the primary key. exercise_id is unconstrained for the same reason
--    as in the flywheel tables: ratings can refer to built-in practice
--    exercises that have no class_exercises row.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exercise_ratings (
    exercise_id VARCHAR(255) NOT NULL,
    user_id     VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    rating      VARCHAR(10)  NOT NULL CHECK (rating IN ('up', 'down')),
    created_at  TIMESTAMPTZ  DEFAULT NOW(),
    PRIMARY KEY (exercise_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_exercise_ratings_exercise ON exercise_ratings (exercise_id);
