# AnalytIQ Student Portfolio — Technical Specification v2
**Version:** 2.0
**Author:** Adam El Harouchi / Claude (Strategic Partner)
**Date:** March 24, 2026
**Status:** Ready for Implementation
**Priority:** HIGH — EF/Hult buyer signal (James Warner mentioned GitHub specifically)

---

## 1. WHAT WE'RE BUILDING

A **Portfolio** page in the main navigation where students can:
1. Build and manage their coding portfolio — class exercises, personal projects, and new projects built directly in AnalytIQ
2. Connect to GitHub — all portfolio items sync to a GitHub repo
3. Share a public link — `myanalytiq.org/portfolio/{slug}` branded as **"Adam's Portfolio"**
4. Start new coding projects from scratch inside AnalytIQ with a built-in editor

The Portfolio is a **first-class section of the app** — it sits in the top nav alongside Classes, not buried in settings.

---

## 2. NAVIGATION CHANGE

### Current Header Nav (Student View)
```
[AnalytIQ]    Home  |  My Classes  |  Code    [Avatar]
```

### New Header Nav (Student View)
```
[AnalytIQ]    Home  |  My Classes  |  Portfolio  |  Code    [Avatar]
```

**Portfolio** sits between **My Classes** and **Code** in the top nav. It leads to `/portfolio` (authenticated dashboard). The public shareable page lives at `/portfolio/{slug}` (no auth).

---

## 3. PORTFOLIO PAGE STRUCTURE

When a student clicks "Portfolio" in the nav, they land on their portfolio dashboard. This page has three sections:

### Section A: Profile Header (top of page)
- Student's name displayed as **"Adam's Portfolio"** (auto-generated from display name, editable)
- Headline (e.g. "Business Analytics @ Hult | Python, SQL, R")
- Bio (max 500 chars)
- Avatar (optional upload or pulled from profile)
- Links: LinkedIn, GitHub, personal website
- **"Share Portfolio"** button → copies public URL
- **"Connect GitHub"** button → initiates OAuth flow
- GitHub sync status badge (connected / not connected / last synced)
- Visibility toggle: Public / Private
- View count (if public)

### Section B: Action Bar
- **"Start New Project"** button (primary CTA, prominent)
- **"Add from Class"** button → opens modal to import completed exercises
- **"Add External Link"** button → add link to external repo/project
- Filter/sort controls: All | Class Exercises | Personal Projects | External Links
- Search bar

### Section C: Project Grid/List
- All portfolio items displayed as cards in a grid (or toggle to list view)
- Each card shows:
  - Project title
  - Language badge (Python, SQL, R, JS, Java)
  - Tags (e.g. "pandas", "regression", "data-viz")
  - Source label: "Business Analytics 101" or "Personal Project" or "External"
  - Date
  - Score (only if student opted to show it)
  - GitHub sync icon (synced / not synced)
  - Pin / Hide / Edit / Delete controls
- Drag-to-reorder (or manual order number)
- Pinned items appear first

---

## 4. "START NEW PROJECT" FEATURE

### What It Does
Student clicks **"Start New Project"** and gets:

1. **Project Setup Modal:**
   - Project title (required)
   - Description (optional, max 1000 chars)
   - Language selector: Python | SQL | R | JavaScript | Java
   - Tags (optional, multi-select from predefined + custom)
   - Click "Create" → opens the project editor

2. **Project Editor Page** (`/portfolio/projects/{project_id}/edit`):
   - Full-screen code editor (reuse the existing practice playground editor)
   - Same editor features: syntax highlighting, line numbers, auto-indent
   - **Run Code** button → server-side sandboxed execution (same grading infrastructure), shows output/errors below
   - **AI Code Assistant** panel (right sidebar or bottom panel, collapsible):
     - Reuses the **main Code Assistant** (the full AI code assistant, NOT the hint assistant from exercises)
     - This is the same assistant accessible from the "Code" nav item — full capabilities, no restrictions on giving direct answers
     - Context-aware: knows the project's language, title, description, and current code
     - Students can ask anything: "Write me a function that does X", "Debug this error", "How should I structure this project?", "Refactor this code"
     - No pedagogical guardrails — this is a full coding partner, not a hint system. In personal projects, there's no "answer" to protect.
     - Chat history persists per project (stored in existing AI conversation model)
     - Rate limits apply (same per-user per-minute/hour limits as the main code assistant)
   - **Save** button → saves current code to database (auto-save every 30 seconds as well)
   - **Save & Add to Portfolio** → saves and marks as portfolio item
   - Project metadata panel (collapsible sidebar): title, description, language, tags
   - Status: Draft | Published (to portfolio)

   **Editor Layout:**
   ```
   ┌────────────────────────────────────────────────────────────────┐
   │  ← Back to Portfolio    Stock Price Predictor    [Save] [Run] │
   ├──────────────────────────────────┬─────────────────────────────┤
   │                                  │  🤖 Code Assistant           │
   │  # Code Editor                   │                             │
   │                                  │  Full coding partner.       │
   │  import pandas as pd             │  Ask anything.              │
   │  import numpy as np              │                             │
   │                                  │  [Student]: Write me a      │
   │  df = pd.read_csv('data.csv')   │  function to normalize      │
   │  print(df.head())               │  this dataframe column       │
   │                                  │                             │
   │                                  │  [AI]: Here's a function:   │
   │                                  │  def normalize(df, col):    │
   │                                  │    mn = df[col].mean()      │
   │                                  │    sd = df[col].std()       │
   │                                  │    return (df[col]-mn)/sd   │
   │                                  │                             │
   │                                  │  [Type your question...]    │
   ├──────────────────────────────────┴─────────────────────────────┤
   │  ▶ Output                                                      │
   │  > Hello world                                                 │
   │  > [1, 2, 3, 4, 5]                                            │
   │  > Execution time: 0.24s                                       │
   └────────────────────────────────────────────────────────────────┘
   ```

3. **Execution:**
   - Uses the SAME server-side sandboxed execution as the grading system
   - subprocess isolation, memory caps, import controls
   - Student sees stdout, stderr, and execution time
   - No test cases needed — this is freeform coding, not graded exercises
   - Timeout: 30 seconds per execution

4. **AI Code Assistant (Detail):**
   - Uses the **main Code Assistant** — the same full AI assistant from the "Code" page, NOT the hint assistant from exercise practice
   - The key difference: the hint assistant in exercises deliberately withholds answers to preserve academic integrity. The portfolio code assistant has NO such restriction — it's a full coding partner.
   - System prompt adapted for personal projects:
     ```
     You are a coding assistant helping a student build a personal project.
     The student is working in {language} on a project called "{title}".
     Project description: {description}
     
     Help the student build their project. You can write code, debug errors,
     suggest architecture, refactor, explain concepts, and provide complete
     solutions when asked. This is their personal project — treat them like
     a developer, not a student taking a test.
     
     Reference their actual code when answering. Be direct and helpful.
     ```
   - Context injection: current code content is included in each AI request (within size limits) so the assistant can reference the student's actual code
   - Conversation stored in existing `ai_conversations` or `messages` table, linked to the portfolio project via `portfolio_item_id`
   - Rate limits: same as the main code assistant (configurable per-user per-minute and per-hour)
   - AI interactions in personal projects are NOT used for model training (same policy as all AI features)

### Why This Matters
- Students can use AnalytIQ as their full coding workspace, not just their homework tool
- The **full code assistant** (not the restricted hint assistant) makes personal projects feel like working with a real coding partner — students can ask for complete solutions, architecture advice, and debugging help
- This is a deliberate distinction: class exercises protect academic integrity with the hint assistant; personal projects unleash the full assistant because there's no answer to protect
- Personal projects built in AnalytIQ are first-class portfolio items
- The execution environment and AI assistant are already built — we're reusing both for freeform use
- Every project built here syncs to GitHub automatically (if connected)

---

## 5. PUBLIC PORTFOLIO PAGE

### URL: `myanalytiq.org/portfolio/{slug}`

### Layout
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   [Avatar]  Adam's Portfolio                            │
│   Business Analytics @ Hult | Python, SQL, R            │
│                                                         │
│   A brief bio about the student and their interests...  │
│                                                         │
│   [LinkedIn] [GitHub] [Website]                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   📌 PINNED                                             │
│   ┌──────────┐  ┌──────────┐                           │
│   │ Stock    │  │ Customer │                           │
│   │ Predictor│  │ Churn    │                           │
│   │ [Python] │  │ [Python] │                           │
│   │ Personal │  │ BA 101   │                           │
│   └──────────┘  └──────────┘                           │
│                                                         │
│   ALL PROJECTS                                          │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│   │ SQL Data │  │ Regress  │  │ Web      │            │
│   │ Wrangling│  │ Analysis │  │ Scraper  │            │
│   │ [SQL]    │  │ [R]      │  │ [Python] │            │
│   │ BA 101   │  │ BA 201   │  │ Personal │            │
│   └──────────┘  └──────────┘  └──────────┘            │
│                                                         │
├─────────────────────────────────────────────────────────┤
│   Built with AnalytIQ | myanalytiq.org                  │
└─────────────────────────────────────────────────────────┘
```

### Click-to-Expand
When a visitor clicks a project card, it expands to show:
- Full description
- Code with syntax highlighting (highlight.js)
- Language, tags, date
- Score (if student opted to show)
- Source (course name + institution, or "Personal Project")
- "View on GitHub" link (if synced)
- Copy code button

### Branding
- Page title: **"{Name}'s Portfolio"** (e.g. "Adam's Portfolio")
- HTML `<title>`: "Adam's Portfolio | AnalytIQ"
- OG tags for social sharing:
  - `og:title`: "Adam's Portfolio"
  - `og:description`: "{headline}" or "Coding portfolio built on AnalytIQ"
  - `og:image`: avatar or AnalytIQ branded card
  - `og:url`: full portfolio URL
- Footer: "Built with AnalytIQ | myanalytiq.org" (subtle, links to homepage)

### 404 Handling
- Private portfolio → "This portfolio is private"
- Non-existent slug → standard 404

---

## 6. DATA MODEL

### New Tables

```sql
-- ============================================================
-- STUDENT PORTFOLIO PROFILE
-- ============================================================
CREATE TABLE portfolio_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Public URL: myanalytiq.org/portfolio/{slug}
    slug VARCHAR(60) NOT NULL UNIQUE,
    
    -- Branding
    portfolio_title VARCHAR(100),       -- e.g. "Adam's Portfolio" (auto-generated, editable)
    display_name VARCHAR(100),
    headline VARCHAR(200),
    bio TEXT,                            -- Max 500 chars
    avatar_url VARCHAR(500),
    
    -- Theme/customization
    accent_color VARCHAR(7) DEFAULT '#3B82F6', -- Hex color for portfolio accent
    layout_style VARCHAR(20) DEFAULT 'grid',    -- 'grid' or 'list'
    
    -- Links
    linkedin_url VARCHAR(300),
    github_username VARCHAR(80),
    personal_website VARCHAR(300),
    
    -- Visibility
    is_public BOOLEAN DEFAULT FALSE,
    
    -- GitHub integration
    github_access_token TEXT,           -- Encrypted at rest
    github_repo_name VARCHAR(200) DEFAULT 'analytiq-portfolio',
    github_sync_enabled BOOLEAN DEFAULT FALSE,
    github_last_synced_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_portfolio_user UNIQUE (user_id)
);

CREATE INDEX idx_portfolio_slug ON portfolio_profiles(slug);
CREATE INDEX idx_portfolio_user ON portfolio_profiles(user_id);


-- ============================================================
-- PORTFOLIO ITEMS
-- ============================================================
CREATE TABLE portfolio_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolio_profiles(id) ON DELETE CASCADE,
    
    -- Item type
    item_type VARCHAR(20) NOT NULL CHECK (item_type IN (
        'class_exercise',    -- Imported from completed AnalytIQ exercise
        'personal_project',  -- Created in AnalytIQ editor (Start New Project)
        'external_link'      -- Link to external repo/project
    )),
    
    -- For class_exercise: link to existing exercise
    exercise_id UUID REFERENCES exercises(id) ON DELETE SET NULL,
    class_id UUID REFERENCES classes(id) ON DELETE SET NULL,
    
    -- Display info
    title VARCHAR(200) NOT NULL,
    description TEXT,                   -- Max 1000 chars
    language VARCHAR(30),               -- python, sql, r, javascript, java
    
    -- Code content
    code_content TEXT,                  -- Actual code
    -- class_exercise: pulled from student's best submission
    -- personal_project: written by student in editor
    -- external_link: null
    
    -- For personal_project: execution support
    last_output TEXT,                   -- Last stdout from running the code
    last_error TEXT,                    -- Last stderr
    last_run_at TIMESTAMPTZ,
    project_status VARCHAR(20) DEFAULT 'draft' CHECK (project_status IN ('draft', 'published')),
    
    -- External link
    external_url VARCHAR(500),
    
    -- Tags (JSON array)
    tags JSONB DEFAULT '[]'::jsonb,
    
    -- Source metadata (auto-populated for class exercises)
    source_class_name VARCHAR(200),
    source_chapter_name VARCHAR(200),
    source_institution VARCHAR(200),
    score DECIMAL(5,2),
    show_score BOOLEAN DEFAULT FALSE,
    
    -- Display controls
    display_order INTEGER DEFAULT 0,
    is_visible BOOLEAN DEFAULT TRUE,
    is_pinned BOOLEAN DEFAULT FALSE,
    
    -- GitHub sync
    github_synced BOOLEAN DEFAULT FALSE,
    github_file_path VARCHAR(300),
    github_commit_sha VARCHAR(40),
    
    -- Auto-save support
    last_saved_at TIMESTAMPTZ,
    
    -- Metadata
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pitems_portfolio ON portfolio_items(portfolio_id);
CREATE INDEX idx_pitems_type ON portfolio_items(item_type);
CREATE INDEX idx_pitems_order ON portfolio_items(portfolio_id, display_order);
CREATE INDEX idx_pitems_status ON portfolio_items(project_status);


-- ============================================================
-- PORTFOLIO VIEWS (anonymous tracking for the student)
-- ============================================================
CREATE TABLE portfolio_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolio_profiles(id) ON DELETE CASCADE,
    viewed_at TIMESTAMPTZ DEFAULT NOW(),
    referrer VARCHAR(500)
);

CREATE INDEX idx_pviews_portfolio ON portfolio_views(portfolio_id);
CREATE INDEX idx_pviews_date ON portfolio_views(viewed_at);
```

### Migration: `011_create_portfolio_tables.sql`

**Notes:**
- `github_access_token` encrypted using same symmetric key pattern as SSO secrets
- Verify FK names against your actual `exercises` and `classes` table schemas
- `code_content` for personal projects stores the student's code — this IS stored server-side (unlike class exercise submissions in the old client-side grading model; now that grading is server-side, you may already have submission storage)

---

## 7. API ROUTES

### New Blueprint: `blueprints/portfolio.py`

```
# ============================================================
# PRIVATE — Portfolio Management (require auth, student role)
# ============================================================

# Profile
GET    /api/portfolio/profile              → Get own portfolio profile
POST   /api/portfolio/profile              → Create portfolio (first time)
PUT    /api/portfolio/profile              → Update profile settings
DELETE /api/portfolio/profile              → Delete entire portfolio

# Items
GET    /api/portfolio/items                → List all own portfolio items
POST   /api/portfolio/items                → Add item (any type)
PUT    /api/portfolio/items/<id>           → Update item
DELETE /api/portfolio/items/<id>           → Remove item
POST   /api/portfolio/items/reorder        → Bulk reorder (accepts ordered ID list)

# Import from classes
GET    /api/portfolio/available-exercises   → List completed exercises not yet in portfolio
POST   /api/portfolio/import-exercise       → Import exercise as portfolio item

# Start New Project
POST   /api/portfolio/projects              → Create new personal project (returns project_id)
PUT    /api/portfolio/projects/<id>/code    → Save code (auto-save endpoint)
POST   /api/portfolio/projects/<id>/run     → Execute code (sandboxed, return stdout/stderr)
PUT    /api/portfolio/projects/<id>/publish → Mark project as published (visible in portfolio)

# AI Code Assistant (in project editor)
POST   /api/portfolio/projects/<id>/assistant     → Send message to AI assistant (returns AI response)
GET    /api/portfolio/projects/<id>/assistant/history → Get conversation history for this project
DELETE /api/portfolio/projects/<id>/assistant/history → Clear conversation history

# GitHub
POST   /api/portfolio/github/connect        → Initiate GitHub OAuth
GET    /api/portfolio/github/callback       → OAuth callback
POST   /api/portfolio/github/sync           → Trigger full sync
POST   /api/portfolio/github/disconnect     → Remove connection
GET    /api/portfolio/github/status          → Sync status

# Analytics
GET    /api/portfolio/analytics             → View counts, referrers, trends

# ============================================================
# PUBLIC — No auth required
# ============================================================

GET    /portfolio/<slug>                    → Render public portfolio page
GET    /api/portfolio/public/<slug>         → JSON API for public data
```

### Page Routes (Jinja2 templates)
```
GET    /portfolio                          → Portfolio dashboard (auth required)
GET    /portfolio/settings                 → Portfolio settings page (auth required)
GET    /portfolio/projects/<id>/edit       → Project editor page (auth required)
GET    /portfolio/<slug>                   → Public portfolio page (no auth)
```

**Route conflict note:** `/portfolio` (dashboard) vs `/portfolio/<slug>` (public page). Handle by checking: if user is authenticated and hits `/portfolio`, show dashboard. If the path segment after `/portfolio/` matches a known slug and user is not the owner, show public page. Alternatively, use `/p/<slug>` for public pages to avoid ambiguity.

**Recommended:** Use `/portfolio/<slug>` for public, `/portfolio/dashboard` for private. Redirect `/portfolio` to `/portfolio/dashboard` when authenticated.

---

## 8. GITHUB INTEGRATION

### OAuth Flow
1. Student clicks "Connect GitHub" on portfolio page
2. Redirect → `https://github.com/login/oauth/authorize?client_id={id}&scope=repo&redirect_uri={callback}`
3. GitHub redirects → `/api/portfolio/github/callback?code={code}`
4. Exchange code for access token via `POST https://github.com/login/oauth/access_token`
5. Encrypt token → store in `portfolio_profiles.github_access_token`
6. Fetch GitHub username → store in `portfolio_profiles.github_username`
7. Create repo if doesn't exist (named from `github_repo_name`, default: `analytiq-portfolio`)

### Sync Logic
When sync triggers (manual or on publish):

For each visible portfolio item with code_content:

1. Generate file path: `{category}/{title-slugified}.{ext}`
   - Categories: `class-exercises/`, `personal-projects/`
   - Extension: `.py`, `.sql`, `.r`, `.js`, `.java`

2. Generate file with header:
```python
# ============================================================
# Adam's Portfolio — AnalytIQ
# ============================================================
# Title:    Linear Regression Analysis
# Course:   Business Analytics 101 (Hult International Business School)
# Language: Python
# Date:     March 2026
# Score:    95/100
# 
# Portfolio: https://myanalytiq.org/portfolio/adam-el-harouchi
# ============================================================

import pandas as pd
import numpy as np
# ... student's code ...
```

3. Generate/update `README.md`:
```markdown
# Adam's Portfolio

> Business Analytics @ Hult | Python, SQL, R

**[View full portfolio →](https://myanalytiq.org/portfolio/adam-el-harouchi)**

## Class Exercises

| Project | Language | Course | Score |
|---------|----------|--------|-------|
| [Linear Regression](./class-exercises/linear-regression.py) | Python | Business Analytics 101 | 95/100 |
| [SQL Data Wrangling](./class-exercises/sql-data-wrangling.sql) | SQL | Business Analytics 101 | 100/100 |

## Personal Projects

| Project | Language | Description |
|---------|----------|-------------|
| [Stock Predictor](./personal-projects/stock-predictor.py) | Python | ML model for stock price prediction |

---
*Built with [AnalytIQ](https://myanalytiq.org) — The Executable Syllabus*
```

4. Commit: `"Update portfolio — synced from AnalytIQ ({n} items)"`

### GitHub API (use `requests` or `PyGithub`)
```
POST /user/repos                            → Create repo
GET  /repos/{owner}/{repo}/contents/{path}  → Check if file exists
PUT  /repos/{owner}/{repo}/contents/{path}  → Create or update file (include sha for updates)
```

### Error Handling
- Token expired → set `github_sync_enabled = FALSE`, show re-auth prompt
- Repo deleted → recreate on next sync
- Rate limited → queue retry via Celery (if enabled) or show "try again in X minutes"
- Always: AnalytIQ is source of truth, GitHub is a mirror

---

## 9. FRONTEND

### New Templates

```
templates/portfolio/
    dashboard.html          → Main portfolio management page (nav: Portfolio)
    settings.html           → GitHub connection, profile settings, customization
    project_editor.html     → "Start New Project" code editor
    import_exercises.html   → Modal/page for importing class exercises
    public.html             → Public-facing portfolio page (no auth)
```

### Project Editor (`project_editor.html`)
- Reuse the existing playground editor component
- **Three-panel layout:**
  - **Left/Center: Code editor** (full syntax highlighting, line numbers, auto-indent, tab support)
  - **Right: AI Code Assistant** (collapsible sidebar panel)
    - Chat interface — same UX as the **main Code assistant** (NOT the hint assistant)
    - Full capabilities: can write code, debug, refactor, suggest architecture
    - Message input at bottom
    - Conversation history scrollable above
    - "Clear conversation" button
    - Context badge showing project language
  - **Bottom: Output panel** (stdout/stderr from code execution, collapsible)
- **Run** button → POST to `/api/portfolio/projects/<id>/run`
  - Loading spinner during execution
  - Timeout indicator (30 sec max)
- **Save** button → PUT to `/api/portfolio/projects/<id>/code`
  - Auto-save every 30 seconds (debounced)
  - "Saved" / "Unsaved changes" indicator
- **Publish to Portfolio** button → marks as published, returns to dashboard
- Sidebar (collapsible): title, description, language, tags editor
- Back to Portfolio link

### Public Portfolio (`public.html`)
- No AnalytIQ app chrome (no nav, no sidebar)
- Standalone page, clean design
- Title: **"{Name}'s Portfolio"** in large text
- Responsive (mobile-friendly — recruiters view on phones)
- Code blocks with highlight.js (load from CDN: `cdnjs.cloudflare.com/ajax/libs/highlight.js/`)
- Smooth expand/collapse for project details
- Social meta tags (og:title, og:description, og:image, twitter:card)

### Customization Options (settings page)
- Portfolio title (default: "{First Name}'s Portfolio", editable)
- Accent color picker (used for headings, buttons, badges on public page)
- Layout: Grid view or List view
- Show/hide sections: Class Exercises, Personal Projects, External Links
- Custom bio and headline
- Avatar upload

---

## 10. EXECUTION ENVIRONMENT FOR "START NEW PROJECT"

Reuse the existing grading sandbox but in "freeform mode":

```python
# services/portfolio_execution_service.py

def execute_project_code(code: str, language: str) -> dict:
    """
    Execute student's personal project code in sandbox.
    Same isolation as grading but no test cases — just run and return output.
    
    Returns:
        {
            "stdout": "Hello world\n[1, 2, 3]\n",
            "stderr": "",
            "exit_code": 0,
            "execution_time_ms": 245,
            "timed_out": False
        }
    """
    # Same subprocess isolation as grading:
    # - subprocess.run with timeout=30
    # - Memory limit (e.g. 256MB via resource.setrlimit)
    # - Import controls (block os.system, subprocess, etc.)
    # - Temp directory per execution
    # - No network access
    
    # Difference from grading:
    # - No test cases
    # - Just capture stdout and stderr
    # - Return raw output to student
```

**Supported languages for execution:**
- Python: Direct execution via subprocess
- JavaScript: Node.js subprocess (if available on server)
- SQL: Execute against a temporary in-memory SQLite database (student can CREATE TABLE, INSERT, SELECT)
- R: Rscript subprocess (if available)
- Java: Compile + run subprocess (if available)

**MVP recommendation:** Start with Python execution only for personal projects. Add others after validating usage. Class exercises already support all languages via the grading system.

---

## 11. SECURITY

### Portfolio Privacy
- Portfolio is **PRIVATE by default**. Student must explicitly toggle public.
- Only items marked `is_visible = TRUE` appear on public page.
- Scores hidden by default (`show_score = FALSE`).
- Draft projects never appear on public page (only `project_status = 'published'`).
- FERPA: This is student-controlled disclosure. The student decides what to share.

### GitHub Token
- Encrypted at rest (symmetric encryption, same pattern as SSO secrets)
- Never exposed in API responses
- Scoped to `repo` only
- Revocable by student at any time
- Overwritten on re-authentication

### Code Execution (Personal Projects)
- Same sandbox as grading: subprocess isolation, memory limits, import controls
- 30-second timeout per execution
- No network access from sandbox
- No filesystem access outside temp directory
- Rate limit: 30 executions/hour per student

### Public Page
- Rate limited: 100 requests/min per IP
- No sensitive data exposed (no email, no internal IDs)
- All user content (bio, descriptions, code) escaped before rendering
- Code rendered in `<pre><code>` blocks — sanitized for XSS

### Input Validation
- Slug: 3-60 chars, alphanumeric + hyphens, lowercase, unique
- Title: max 200 chars
- Description: max 1000 chars
- Bio: max 500 chars
- Code: max 50,000 chars
- Tags: max 10 per item, max 30 chars each
- File upload: max 1MB, code files only (.py, .sql, .r, .js, .java, .txt)

---

## 12. CONFIGURATION

```python
# Portfolio feature
PORTFOLIO_ENABLED = True
PORTFOLIO_MAX_ITEMS = 100
PORTFOLIO_MAX_CODE_LENGTH = 50000
PORTFOLIO_SLUG_MIN = 3
PORTFOLIO_SLUG_MAX = 60
PORTFOLIO_BIO_MAX = 500
PORTFOLIO_DESCRIPTION_MAX = 1000
PORTFOLIO_MAX_TAGS_PER_ITEM = 10
PORTFOLIO_EXECUTION_TIMEOUT = 30          # seconds
PORTFOLIO_EXECUTIONS_PER_HOUR = 30
PORTFOLIO_AUTOSAVE_INTERVAL = 30000       # milliseconds (frontend)

# GitHub
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI')
GITHUB_DEFAULT_REPO_NAME = 'analytiq-portfolio'
```

---

## 13. IMPLEMENTATION PLAN

### Phase 1: Portfolio + Projects + Editor (Target: 7-10 days)

**Database & Backend (Days 1-3):**
- [ ] Migration: `011_create_portfolio_tables.sql`
- [ ] Repository: `repositories/portfolio_repository.py`
- [ ] Service: `services/portfolio_service.py`
- [ ] Service: `services/portfolio_execution_service.py` (freeform code execution)
- [ ] Blueprint: `blueprints/portfolio.py` (all private + public routes)
- [ ] Slug generation utility (from name, uniqueness check, sanitization)
- [ ] AI assistant routes: wire into existing Gemini API service using the MAIN code assistant (not hint assistant), with project-aware system prompt
- [ ] AI conversation storage: link to portfolio_item_id in existing messages/conversation model

**Frontend (Days 3-6):**
- [ ] Add "Portfolio" between "My Classes" and "Code" in main nav header (student views)
- [ ] Portfolio dashboard template (profile header, action bar, project grid)
- [ ] "Start New Project" → project editor with code editor, AI assistant panel, output panel
- [ ] AI assistant panel in project editor (reuse practice playground chat component, right sidebar)
- [ ] "Add from Class" → exercise import modal (list completed exercises with checkboxes)
- [ ] "Add External Link" → simple form
- [ ] Item card component (reusable across dashboard and public page)
- [ ] Drag-to-reorder or manual ordering
- [ ] Pin/hide/edit/delete controls per item

**Public Page (Days 5-7):**
- [ ] Public portfolio template (`/portfolio/<slug>`)
- [ ] "{Name}'s Portfolio" branding
- [ ] Code display with highlight.js
- [ ] Click-to-expand project detail
- [ ] OG meta tags for social sharing
- [ ] View counter
- [ ] Mobile responsive

**Polish (Days 7-8):**
- [ ] Auto-save in project editor (30-sec debounce)
- [ ] "Saved" / "Unsaved" indicator
- [ ] Portfolio settings page (customization: accent color, layout, bio)
- [ ] Empty states ("No projects yet — start your first one!")

### Phase 2: GitHub Integration (Target: 4-5 days)

- [ ] Register GitHub OAuth App
- [ ] GitHub OAuth flow (connect/disconnect)
- [ ] Token encryption + storage
- [ ] Repo creation on first connect
- [ ] File generation with headers + README
- [ ] Sync trigger (manual + auto on publish)
- [ ] Sync status UI (dashboard badge, last synced timestamp)
- [ ] Error handling (expired token, rate limits, deleted repo)
- [ ] Celery task for async sync (if enabled)

### Phase 3: Institutional Features (Future — after paying customers)

- [ ] Professor view: "X students have active portfolios"
- [ ] Class portfolio showcase (opt-in: students can feature portfolio on class page)
- [ ] Institution-branded portfolio pages
- [ ] Bulk GitHub setup for a class
- [ ] Portfolio PDF export for career fairs

---

## 14. FILES TO CREATE

```
migrations/
    011_create_portfolio_tables.sql

repositories/
    portfolio_repository.py

services/
    portfolio_service.py
    portfolio_execution_service.py

blueprints/
    portfolio.py

templates/portfolio/
    dashboard.html
    settings.html
    project_editor.html
    import_exercises.html
    public.html
```

---

## 15. TESTING CHECKLIST

### Portfolio Profile
- [ ] Create portfolio with auto-generated slug from name
- [ ] Duplicate slug is rejected with clear error
- [ ] Edit slug, title, bio, headline, accent color, layout
- [ ] Toggle public/private
- [ ] Delete portfolio removes all items

### Portfolio Items
- [ ] Import class exercise (pulls title, language, code, score, source info)
- [ ] Add personal project via editor
- [ ] Add external link
- [ ] Reorder items
- [ ] Pin/unpin items
- [ ] Hide/show items
- [ ] Edit item details (title, description, tags, show_score)
- [ ] Delete item

### Start New Project
- [ ] Create new project → opens editor
- [ ] Code editor loads with correct language syntax highlighting
- [ ] Run code → shows stdout and stderr correctly
- [ ] Run code → respects 30-second timeout
- [ ] Run code → blocked imports are rejected (os.system, subprocess, etc.)
- [ ] Save code → persists to database
- [ ] Auto-save fires every 30 seconds
- [ ] Publish → project appears in portfolio
- [ ] Draft projects do NOT appear on public page

### AI Code Assistant (in Project Editor)
- [ ] AI assistant panel renders in project editor (collapsible sidebar)
- [ ] Uses the MAIN code assistant, NOT the hint assistant from exercises
- [ ] Student sends message → receives AI response with full code solutions when asked
- [ ] AI response references student's current code (context injection works)
- [ ] AI system prompt includes project language, title, and description
- [ ] AI can write complete functions, debug errors, and suggest architecture (no withholding)
- [ ] Conversation history persists when leaving and returning to project
- [ ] Clear history button works
- [ ] Rate limits enforced (same as main code assistant)
- [ ] Long code content is truncated appropriately before sending to Gemini (within token limits)
- [ ] AI assistant works for all supported languages (Python, SQL, R, JS, Java)

### Public Page
- [ ] Public URL works without auth
- [ ] Displays "{Name}'s Portfolio" as title
- [ ] Only visible + published items shown
- [ ] Scores hidden when show_score = FALSE
- [ ] Code renders with syntax highlighting
- [ ] Click-to-expand works
- [ ] OG tags render correctly (test with LinkedIn post inspector)
- [ ] Private portfolio shows "This portfolio is private"
- [ ] Non-existent slug shows 404
- [ ] View counter increments
- [ ] XSS: injected HTML in bio/description/code is escaped

### GitHub Integration
- [ ] OAuth flow completes, token stored encrypted
- [ ] Repo created on first sync
- [ ] Files committed with correct headers and paths
- [ ] README generated with links
- [ ] Re-sync updates changed files without duplicating
- [ ] New items added after initial sync are included
- [ ] Disconnect removes token, disables sync
- [ ] Expired token prompts re-auth
- [ ] Rate limit handled gracefully

---

## 16. SUCCESS METRICS

- % of students who create a portfolio within 30 days of account creation
- Average items per portfolio
- % using "Start New Project" (personal projects vs class imports)
- AI assistant usage in project editor: messages per project, % of projects that use assistant
- Public portfolio page views per month
- % who connect GitHub
- EF/James Warner response to GitHub feature
- Student engagement lift: do portfolio users complete more exercises?
- Time spent in project editor (proxy for platform stickiness)

---

## 17. CLAUDE CODE HANDOFF

Start with Phase 1. The spec is designed so Phase 1 is fully shippable without GitHub.

**First prompt for Claude Code:**
```
Read the portfolio spec at [path]. Start by creating the database migration 
(011_create_portfolio_tables.sql), then build the repository and service layers. 
Follow the existing patterns in the codebase (parameterized SQL, connection pool, 
service layer for business logic). After the backend is done, add "Portfolio" to the 
main nav header between "My Classes" and "Code" for student users. Then build the 
dashboard template and the project editor with the AI assistant panel. The AI 
assistant must reuse the existing Gemini API integration from the MAIN code 
assistant (the full "Code" page assistant), NOT the hint assistant from exercise 
practice. Same service, same rate limits, but the system prompt should treat 
the student as a developer building their own project — no withholding answers, 
full coding partner. Include the project's language, title, description, and 
current code as context in each request.
```

**Key constraint:** The project editor MUST reuse the existing playground editor component, the existing sandboxed execution infrastructure, AND the existing AI assistant (Gemini API integration). Don't rebuild these — wire into them. The AI assistant in the project editor is the same assistant from the practice playground, just with a different system prompt that's aware of the project context (language, title, description, current code).
