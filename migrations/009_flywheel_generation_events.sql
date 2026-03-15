-- Migration 009: Data flywheel — exercise generation event tracking
-- Safe to run multiple times (IF NOT EXISTS guards).
-- NOTE: exercise_id is VARCHAR(255) to match class_exercises.exercise_id (not a UUID).
--       FK constraints on exercise_id and user_id are intentionally omitted to
--       avoid type mismatches with legacy string IDs.

CREATE TABLE IF NOT EXISTS exercise_generation_events (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise_id             VARCHAR(255),                                             -- matches class_exercises.exercise_id (string PK)
    class_id                VARCHAR(255) REFERENCES classes(class_id)       ON DELETE SET NULL,
    chapter_id              VARCHAR(255) REFERENCES class_chapters(chapter_id) ON DELETE SET NULL,
    tenant_id               TEXT,

    -- What went in
    source_content_hash     VARCHAR(64),
    source_content_type     VARCHAR(50),
    source_char_count       INTEGER,
    was_truncated           BOOLEAN      DEFAULT FALSE,
    detected_language       VARCHAR(20),
    detected_topics         JSONB        DEFAULT '[]'::jsonb,

    -- What we asked Gemini
    gemini_model            VARCHAR(100),
    prompt_template_version VARCHAR(50),
    prompt_tokens           INTEGER,
    completion_tokens       INTEGER,
    generation_params       JSONB        DEFAULT '{}'::jsonb,

    -- What came out
    difficulty_requested    VARCHAR(20),
    difficulty_generated    VARCHAR(20),
    exercise_type           VARCHAR(50),
    exercise_structure      JSONB        DEFAULT '{}'::jsonb,
    num_test_cases          INTEGER,
    generation_time_ms      INTEGER,

    created_at              TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gen_events_exercise ON exercise_generation_events(exercise_id);
CREATE INDEX IF NOT EXISTS idx_gen_events_class    ON exercise_generation_events(class_id);
CREATE INDEX IF NOT EXISTS idx_gen_events_chapter  ON exercise_generation_events(chapter_id);
CREATE INDEX IF NOT EXISTS idx_gen_events_created  ON exercise_generation_events(created_at);
