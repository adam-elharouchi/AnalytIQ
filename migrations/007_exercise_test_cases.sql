-- Migration 007: output-based grading — add test_cases + function_name to class_exercises
-- Safe to run multiple times (IF NOT EXISTS guards).

-- ---------------------------------------------------------------------------
-- 1. Add test_cases column (JSONB array of test case objects)
--    Shape: [{"description": str, "input": {...}, "expected_output": any, "weight": int}]
-- ---------------------------------------------------------------------------
ALTER TABLE class_exercises ADD COLUMN IF NOT EXISTS test_cases    JSONB;

-- ---------------------------------------------------------------------------
-- 2. Add function_name column (name of the function students must define)
--    Defaults to "solution" for exercises that pre-date this migration.
-- ---------------------------------------------------------------------------
ALTER TABLE class_exercises ADD COLUMN IF NOT EXISTS function_name VARCHAR(255) DEFAULT 'solution';

-- ---------------------------------------------------------------------------
-- 3. Add language column (e.g. "Python", "R", "JavaScript", "SQL")
--    Needed so the grading endpoint can dispatch to the correct runner.
-- ---------------------------------------------------------------------------
ALTER TABLE class_exercises ADD COLUMN IF NOT EXISTS language VARCHAR(50) DEFAULT 'Python';

-- ---------------------------------------------------------------------------
-- 4. Index for fast lookup of exercises that have test cases
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_class_exercises_has_test_cases
    ON class_exercises ((test_cases IS NOT NULL));
