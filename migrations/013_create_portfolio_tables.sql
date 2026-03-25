-- Migration 013: Student Portfolio tables
-- Safe to run multiple times (IF NOT EXISTS guards).

-- ============================================================
-- STUDENT PORTFOLIO PROFILE
-- ============================================================
CREATE TABLE IF NOT EXISTS portfolio_profiles (
    id                    VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id               VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Public URL: myanalytiq.org/portfolio/{slug}
    slug                  VARCHAR(60)  NOT NULL UNIQUE,

    -- Branding
    portfolio_title       VARCHAR(100),
    display_name          VARCHAR(100),
    headline              VARCHAR(200),
    bio                   TEXT,
    avatar_url            VARCHAR(500),

    -- Theme / customization
    accent_color          VARCHAR(7)   DEFAULT '#2569f4',
    layout_style          VARCHAR(20)  DEFAULT 'grid',

    -- Links
    linkedin_url          VARCHAR(300),
    github_username       VARCHAR(80),
    personal_website      VARCHAR(300),

    -- Visibility
    is_public             BOOLEAN      DEFAULT FALSE,

    -- GitHub integration
    github_access_token   TEXT,
    github_repo_name      VARCHAR(200) DEFAULT 'analytiq-portfolio',
    github_sync_enabled   BOOLEAN      DEFAULT FALSE,
    github_last_synced_at TIMESTAMPTZ,

    -- Metadata
    created_at            TIMESTAMPTZ  DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  DEFAULT NOW(),

    CONSTRAINT uq_portfolio_user UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_slug ON portfolio_profiles(slug);
CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio_profiles(user_id);


-- ============================================================
-- PORTFOLIO ITEMS
-- ============================================================
CREATE TABLE IF NOT EXISTS portfolio_items (
    id                   VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    portfolio_id         VARCHAR(255) NOT NULL REFERENCES portfolio_profiles(id) ON DELETE CASCADE,

    -- Item type
    item_type            VARCHAR(20)  NOT NULL CHECK (item_type IN (
                             'class_exercise',
                             'personal_project',
                             'external_link'
                         )),

    -- For class_exercise: link to existing exercise
    exercise_id          VARCHAR(255) REFERENCES class_exercises(exercise_id) ON DELETE SET NULL,
    class_id             VARCHAR(255) REFERENCES classes(class_id) ON DELETE SET NULL,

    -- Display info
    title                VARCHAR(200) NOT NULL,
    description          TEXT,
    language             VARCHAR(30),

    -- Code content
    code_content         TEXT,

    -- For personal_project: execution support
    last_output          TEXT,
    last_error           TEXT,
    last_run_at          TIMESTAMPTZ,
    project_status       VARCHAR(20)  DEFAULT 'draft' CHECK (project_status IN ('draft', 'published')),

    -- External link
    external_url         VARCHAR(500),

    -- Tags (JSON array of strings)
    tags                 JSONB        DEFAULT '[]'::jsonb,

    -- Source metadata (auto-populated for class exercises)
    source_class_name    VARCHAR(200),
    source_chapter_name  VARCHAR(200),
    source_institution   VARCHAR(200),
    score                DECIMAL(5,2),
    show_score           BOOLEAN      DEFAULT FALSE,

    -- Display controls
    display_order        INTEGER      DEFAULT 0,
    is_visible           BOOLEAN      DEFAULT TRUE,
    is_pinned            BOOLEAN      DEFAULT FALSE,

    -- GitHub sync
    github_synced        BOOLEAN      DEFAULT FALSE,
    github_file_path     VARCHAR(300),
    github_commit_sha    VARCHAR(40),

    -- Auto-save support
    last_saved_at        TIMESTAMPTZ,

    -- Metadata
    completed_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ  DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pitems_portfolio ON portfolio_items(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_pitems_type      ON portfolio_items(item_type);
CREATE INDEX IF NOT EXISTS idx_pitems_order     ON portfolio_items(portfolio_id, display_order);
CREATE INDEX IF NOT EXISTS idx_pitems_status    ON portfolio_items(project_status);


-- ============================================================
-- PORTFOLIO VIEWS (anonymous view tracking)
-- ============================================================
CREATE TABLE IF NOT EXISTS portfolio_views (
    id           VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    portfolio_id VARCHAR(255) NOT NULL REFERENCES portfolio_profiles(id) ON DELETE CASCADE,
    viewed_at    TIMESTAMPTZ  DEFAULT NOW(),
    referrer     VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_pviews_portfolio ON portfolio_views(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_pviews_date      ON portfolio_views(viewed_at);
