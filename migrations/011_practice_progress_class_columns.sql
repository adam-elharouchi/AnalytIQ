-- Migration 011: Add class_id and class_exercise_id to practice_progress
-- These columns track which class assignment an exercise attempt belongs to.
-- The existing UNIQUE(user_id, exercise_id) constraint is preserved so that the
-- upsert ON CONFLICT clause continues to work correctly.

ALTER TABLE practice_progress
    ADD COLUMN IF NOT EXISTS class_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS class_exercise_id VARCHAR(255);
