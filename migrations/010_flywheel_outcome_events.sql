-- Migration 010: Data flywheel — grading outcome tracking and quality scores
-- Safe to run multiple times (IF NOT EXISTS guards).
-- NOTE: exercise_id is VARCHAR(255) and user_id is TEXT to match existing schema
--       conventions; FK constraints on these columns are intentionally omitted.

-- ---------------------------------------------------------------------------
-- 1. exercise_outcome_events — one row per grading submission
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exercise_outcome_events (
    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise_id          VARCHAR(255),                                                      -- matches class_exercises.exercise_id
    generation_event_id  UUID         REFERENCES exercise_generation_events(id) ON DELETE SET NULL,
    user_id              TEXT,
    class_id             VARCHAR(255),
    tenant_id            TEXT,

    -- Submission context
    attempt_number       INTEGER,
    time_spent_seconds   INTEGER,
    hints_requested      INTEGER      DEFAULT 0,
    ai_chat_messages     INTEGER      DEFAULT 0,
    code_char_count      INTEGER,

    -- Grading results
    passed               BOOLEAN,
    total_score          NUMERIC(5,2),
    correctness_score    NUMERIC(5,2),
    quality_score        NUMERIC(5,2),
    tests_total          INTEGER,
    tests_passed         INTEGER,
    test_results         JSONB        DEFAULT '[]'::jsonb,
    error_category       VARCHAR(50),
    execution_time_ms    INTEGER,

    created_at           TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outcome_exercise  ON exercise_outcome_events(exercise_id);
CREATE INDEX IF NOT EXISTS idx_outcome_user      ON exercise_outcome_events(user_id);
CREATE INDEX IF NOT EXISTS idx_outcome_gen_event ON exercise_outcome_events(generation_event_id);
CREATE INDEX IF NOT EXISTS idx_outcome_created   ON exercise_outcome_events(created_at);

-- ---------------------------------------------------------------------------
-- 2. exercise_quality_scores — aggregated per-exercise quality, computed by Celery
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exercise_quality_scores (
    id                        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise_id               VARCHAR(255) UNIQUE NOT NULL,
    generation_event_id       UUID         REFERENCES exercise_generation_events(id) ON DELETE SET NULL,

    total_attempts            INTEGER      DEFAULT 0,
    unique_students           INTEGER      DEFAULT 0,
    first_attempt_pass_rate   FLOAT,
    overall_pass_rate         FLOAT,
    avg_attempts_to_pass      FLOAT,
    median_time_to_pass_seconds INTEGER,
    avg_hints_before_pass     FLOAT,
    dropout_rate              FLOAT,

    quality_score             FLOAT,
    quality_label             VARCHAR(20),
    dominant_error_category   VARCHAR(50),
    common_failure_pattern    JSONB        DEFAULT '{}'::jsonb,

    last_computed_at          TIMESTAMPTZ  DEFAULT NOW(),
    sample_size               INTEGER
);

-- ---------------------------------------------------------------------------
-- 3. Add generation_event_id to class_exercises for backward linking
-- ---------------------------------------------------------------------------
ALTER TABLE class_exercises
    ADD COLUMN IF NOT EXISTS generation_event_id UUID
        REFERENCES exercise_generation_events(id) ON DELETE SET NULL;
