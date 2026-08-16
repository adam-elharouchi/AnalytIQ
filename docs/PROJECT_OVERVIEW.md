# AnalytIQ - The Comprehensive Blueprint

*This document serves as the absolute, definitive, and exhaustive breakdown of the AnalytIQ platform, covering every facet of its purpose, architecture, user journeys, data flow, integrations, and deployment strategy.*

---

## 🌟 1. Executive Summary & Vision

### What is AnalytIQ?
AnalytIQ is a modern, AI-augmented Learning Management System (LMS) and interactive coding environment. It bridges the gap between passive consumption of educational material (reading slides) and active, hands-on learning (writing and debugging code). Built with a striking dark aesthetic featuring glassmorphism and animated accents, it provides a premium user experience that feels less like a traditional academic portal and more like a modern developer tool.

### Who is it For? (Core Personas)
1. **The Student:** Wants a unified space to view lectures, practice coding immediately contextually relevant to the material, track their progress, and get instant, non-judgmental help from an AI tutor when stuck.
2. **The Professor (Educator):** Wants zero friction in creating coursework. They simply upload their existing PDF slide decks; AnalytIQ's AI autonomously parses the content and generates quizzes, coding exercises, and lesson summaries. They also require robust analytics to identify struggling students.
3. **The Institution (Admin):** Needs the platform to integrate seamlessly into their existing ecosystem (Canvas, Moodle, Blackboard) via strict LTI 1.3 standards, ensuring SSO (Single Sign-On) and secure grade pass-back without managing separate rosters.

---

## 🏗️ 2. System Architecture & The "How It Works" Flow

AnalytIQ uses a **Flask Blueprint API backend** + a **server-rendered Jinja2 + vanilla-JS frontend**. Every page is a Jinja2 template served by Flask; interactivity is layered on with vanilla-JS modules (`static/js/`) that call the JSON API.

### The Request Lifecycle (A Deep Dive)
1. **Client Interaction:** A user clicks a button (e.g., "Submit Code"). A vanilla-JS page module calls the shared `authFetch` wrapper (`static/js/api-helper.js`).
2. **Token Injection:** `apiClient` reads the JWT from `localStorage` and attaches it as `Authorization: Bearer <token>` to every request.
3. **Network Transit & CORS:** The browser fires a preflight `OPTIONS` request. `core/factory.py` handles CORS globally via a `before_request` hook.
4. **Backend Gateway (`app.py` → `core/factory.py`):**
   - **Rate Limiting:** `Flask-Limiter` checks (via Redis or Memory) if the user has exceeded their endpoint quota (preventing DDoS or AI abuse).
   - **CSRF Check:** Not applicable to the API surface. Authentication is header-only (`Authorization: Bearer`), never cookie-based, so no mutating endpoint is CSRF-exploitable; `WTF_CSRF_CHECK_DEFAULT` is `False` and every mutating route carries `@csrf_exempt`. `Flask-WTF` is initialised only so `generate_csrf()` / `GET /api/csrf-token` remain available to any future form-submit route. See `docs/security/JWT_CSRF_MITIGATION.md`.
   - **Error Tracking:** `Sentry SDK` attaches a unique `request_id` context to the transaction.
5. **Blueprint Routing:** The request hits a specific Flask Blueprint (e.g., `blueprints/exercises.py → submit_exercise()`).
6. **Authentication Validation (`@require_auth`):** Decodes the JWT, verifies the signature against `config.SECRET_KEY`, checks expiration, and sets `g.user_id`, `g.user_role`, `g.tenant_id`.
7. **Database Transaction (`repositories/`):**
   - A connection is pulled from the `psycopg2.pool.ThreadedConnectionPool` in `core/database.py`.
   - Raw, parameterized SQL executes against PostgreSQL (preventing SQL injection).
   - All query logic lives in `repositories/` — blueprints contain no raw SQL.
8. **Heavy Processing (The AI Fork):**
   - *If the request requires complex AI (e.g., parsing a 50-page PDF):* The backend enqueues a Celery task via Redis. The user receives a `task_id` (HTTP 202 Accepted) and the frontend polls `GET /api/tasks/<task_id>` until complete.
   - *If it's a fast task (like grading code):* The backend synchronously calls the Gemini API, formats the response, and returns JSON.
9. **Client Response:** The page module receives the JSON response and updates the affected DOM nodes.

---

## 🛠️ 3. The Exhaustive Tech Stack

### 🖥️ Frontend layer (The Visual Interface)
AnalytIQ is a **server-rendered Jinja2 application** with vanilla-JS progressive enhancement.
Every page is a Jinja2 template that extends `base.html`; there is no SPA framework and no
client-side build step. Flask's catch-all route (`core/factory.py → serve_frontend`) maps a
clean URL to a `.html` template.

*   **HTML5 / Jinja2:** `landing.html`, the student/professor portal pages (`student-classes.html`,
    `student-class.html`, `chapter-view.html`, `professor-dashboard.html`, `professor-class.html`,
    `upload-assistant.html`, `code-assistant.html`), the auth shells, the LTI templates, and the
    legal/informational pages (`contact.html`, `privacy.html`, `terms.html`) all render server-side.
*   **CSS3 (Custom Styling):** No Bootstrap or Tailwind. Built from scratch with CSS Variables
    (`:root`), Flexbox, Grid, and glassmorphism panels in `static/css/styles.css`.
*   **JS modules** (`static/js/api-helper.js`, `auth.js`, `ui-states.js`, `offline-detector.js`,
    the per-page `student-*.js` / `professor-*.js` modules, etc.) are loaded by the Jinja base
    template. They call the JSON API through the shared `authFetch` wrapper in `api-helper.js`,
    which injects the JWT Bearer header and handles 401 expiry.

### 🧠 Backend Layer (The Brain)
*   **Python 3.x:** The core programming language, chosen for its vast data-science/AI ecosystem and readable syntax.
*   **Flask (3.0.0):** The web server framework. It handles HTTP routing, request parsing, and response generation.
    *   **Blueprints:** Used extensively to split the app into logical modules:
        *   `auth.py`: Login, registration, password hashing (Bcrypt), JWT issuing.
        *   `users.py`: Profile fetching, settings updates.
        *   `classes.py`: CRUD operations for university courses.
        *   `chapters.py`: Managing modules/modules within a class.
        *   `exercises.py`: Code challenge evaluations and progress tracking.
        *   `ai.py`: The gateway to Google Gemini (chat bots, hints).
        *   `lti.py`: Handles complex OAuth2/OIDC flows for LMS integrations.
*   **Middleware & Security:**
    *   `Flask-Limiter`: Prevents endpoint abuse.
    *   `Flask-WTF`: Initialised for CSRF token *issuance* only (`GET /api/csrf-token`). No route is validated against it today — see `docs/security/JWT_CSRF_MITIGATION.md` for why header-only JWT auth closes the CSRF surface without it.
    *   `PyJWT`: Cryptographically signs user sessions (stateless auth).
    *   `Sentry-SDK`: Catches unhandled exceptions, sanitizes Personal Identifiable Information (PII), and alerts developers in real-time.

### 🗄️ Database & Storage Layer (The Memory)
*   **PostgreSQL:** The primary relational database. Chosen for ACID compliance, robust foreign-key constraints, and complex querying capabilities.
    *   **Architecture:** Raw SQL via `psycopg2` (no ORM). `core/database.py` manages a `ThreadedConnectionPool` (min 1, max N connections). All queries live in the `repositories/` layer.
    *   **Core Tables Overview:**
        *   `users`: `user_id` (UUID), email, password_hash (bcrypt), role, tenant_id.
        *   `classes`: ID, professor_id (FK), name, description, class_id (join code).
        *   `class_enrollments`: Junction table linking `users` (students) to `classes`.
        *   `class_chapters`: ID, class_id (FK), title, sequence_order, pdf_url.
        *   `class_exercises`: ID, chapter_id (FK), title, description, difficulty, solution_code, test_cases.
        *   `exercise_progress`: Tracks per-student submission scores and timestamps.
*   **Supabase Storage / Cloud Storage:** Used exclusively as an S3-compatible Blob store. When a professor uploads a PDF lecture, the binary file is streamed to a bucket, and a public/signed URL string is saved to the `chapters` table.

### 🤖 AI Integration (The Core Differentiator)
*   **Google Gemini API (`gemini-1.5-flash` & `gemini-1.5-pro`):**
    *   **The AI Coding Assistant (`code-assistant.html`):** Uses strict prompt engineering to act as a "Socratic Tutor." It is instructed *never* to give the direct answer but to guide the student towards writing the correct logic.
    *   **Autonomous Content Generation (`exercise_generator.py`):** When a PDF is uploaded, `pdf_processor.py` extracts the raw text. This text is fed into a massive, highly-structured prompt to Gemini, utilizing "Structured JSON Output" mode to guarantee the AI returns a valid, parseable JSON array of relevant coding questions and multiple-choice quizzes based *only* on the slide content.

### ⚡ Background Tasks (The Workhorses)
*   **Celery:** A distributed task queue. It takes heavy, long-running Python functions (like sending bulk emails, crunching analytics, or processing 100-page PDFs through an LLM) out of the main HTTP request/response cycle, preventing the web server from freezing or timing out.
*   **Redis:** Acts as the "Message Broker." Flask sends a message ("Hey celery, process PDF ID #45") to Redis. A background Celery Worker constantly monitors Redis, picks up the message, executes the heavy Python code, and updates a status table when finished.

---

## 🛣️ 4. Comprehensive User Journeys

### The Student Journey
1. **Onboarding:** Registers via `POST /api/users/signup`, inputs a unique class `join_code` provided by their professor.
2. **The Dashboard (`student-classes.html`):** Land on a grid of enrolled classes showing progress bars (calculated by joining `exercises` against `exercise_completions`).
3. **The Chapter View (`chapter-view.html`):** An immersive, split-screen layout. The left pane renders the assigned PDF (via an embedded object or PDF.js). The right pane dynamically lists reading summaries, automatically generated quizzes, and coding challenges associated with that specific chapter.
4. **The Practice Playground (`practice-playground.html`):**
   - Click a code challenge.
   - The user types logic into the syntax-highlighted editor.
   - They can click "Ask AI for Hint." The frontend packages their *current code state* + *the question text* and sends it to the `/api/ai/hint` endpoint.
   - They submit code. The backend evaluates it (either via strict string matching, regex logic checks, or an AI grader for complex logic) and persists the completion status.

### The Professor Journey
1. **Class Creation:** Creates a class (`professor-dashboard.html`); a unique alphanumeric `join_code` is generated.
2. **The Upload Assistant (`upload-assistant.html`):** The crown jewel of the educator platform.
   - Drag and drop a PDF lecture (e.g., "Introduction to Python Data Structures.pdf").
   - Define extraction parameters (e.g., "Generate 3 coding questions and 2 quizzes").
   - The file uploads to Blob storage. The backend fires the Celery worker.
   - A loading spinner tracks the background job status.
   - The AI returns structured JSON. The frontend presents a confirmation table allowing the professor to edit, approve, or reject the AI's generated questions.
3. **Analytics Tracking (`professor-class.html`):** A granular dashboard showing tables of the student roster, visualizing who has completed which exercises, identifying bottlenecks (e.g., "80% of students failed Exercise #4"), and presenting leaderboards mapped to UI components.

---

## 🔌 5. Infrastructure, LTI 1.3, & DevOps

### LTI 1.3 Integration (Learning Tools Interoperability)
AnalytIQ is not a walled garden; it is designed for enterprise university adoption.
*   **The Problem:** Universities won't buy software if students have to create new accounts and professors have to manually copy grades over.
*   **The Standard:** LTI 1.3 utilizes OpenID Connect (OIDC) and OAuth 2.0.
*   **The Flow (`lti.py` & `lti-*` templates):**
    1. A student clicks an "AnalytIQ Week 1 Assignment" link inside Canvas.
    2. Canvas sends an OIDC login initiation to `/api/lti/login`.
    3. AnalytIQ redirects back to Canvas for authentication.
    4. Canvas POSTs a massive, cryptographically-signed JWT (the `id_token`) to `/api/lti/launch`.
    5. AnalytIQ validates the signature against the university's public keys (JWKS).
    6. AnalytIQ reads the token: "Ah, this is John Doe, role: Learner, accessing Course ID: 101."
    7. AnalytIQ automatically provisions an account in the background (SSO) and drops them directly into the specific assignment (`target_link_uri`).
    8. Upon completion, AnalytIQ utilizes the LTI Advantage Assignment and Grade Services (AGS) APIs to push the grade score (0.0 to 1.0) directly into the Canvas Gradebook.

### Deployment & CI/CD Strategy
*   **Hosting Context:** Entirely serverless/managed infrastructure.
*   **Application Server:** **Render (Web Services)** running Gunicorn (a Python WSGI HTTP Server). Gunicorn manages multiple worker processes (gevent/sync) to handle concurrent web traffic.
*   **Database Host:** **Supabase (Managed PostgreSQL)**. Provides replication and a SQL editor; scheduled backups are not enabled on the current plan. First-party backups are handled by `scripts/backup_db.sh` (added 2026-08-13; see `docs/RUNBOOK.md` §3).
*   **Cache/Queue Host:** **Render (Managed Redis)**. Handles session caching, rate-limit counters, and the Celery broker queue.
*   **Continuous Integration (CI):** GitHub Actions. On every commit/PR:
    1. Lints the Python code (`flake8`/`black`).
    2. Runs the `pytest` suite (targeting >80% coverage).
    3. Mock dependencies (like the database and Gemini API) are used to test complex logic (e.g., "Does the auth middleware correctly reject an expired token?").
    4. Upon passing, code merges to main and triggers an automated deployment hook on Render, seamlessly replacing the active container.

---

## 📁 6. The Complete File & Directory Map

```text
/AnalytIQ
│
├── ⚙️ ROOT CONFIGURATION & APPLICATION ENTRY
│   ├── app.py                     # create_app() entry point; delegates startup to core/factory.py.
│   ├── config.py                  # Single source of truth for all env vars. config_security_warnings() logs non-fatal warnings at startup (core/factory.py:87); validate_config() is defined but not called by app code today (tests only).
│   ├── Procfile                   # Boot commands for Render: web (gunicorn) + worker (celery).
│   ├── requirements.txt           # Python dependency lockfile (Flask, psycopg2-binary, pyjwt, celery, etc.).
│   └── tests/                     # pytest suite: unit/ (mock DB) + integration/ (live DB + Redis).
│
├── 🧩 /core/ (INFRASTRUCTURE — imported across blueprints)
│   ├── factory.py                 # Flask app startup helpers: setup_logging, register_blueprints, etc.
│   ├── database.py                # ThreadedConnectionPool, get_db_connection().
│   ├── auth.py                    # JWT helpers, bcrypt, @require_auth / @require_role decorators.
│   ├── extensions.py              # Flask-Limiter + csrf_exempt (avoids circular imports).
│   ├── cache.py                   # Redis cache helpers (get_cached, set_cached, cache_response decorator).
│   ├── storage.py                 # Supabase Storage client.
│   ├── audit.py                   # FERPA audit_log table + audit() helper.
│   └── errors.py                  # Typed error classes (ApiError, NotFoundError, …).
│
├── 🛣️ /blueprints/ (API ROUTES — one file per domain)
│   ├── auth.py                    # POST /api/users/signup|signin|forgot-password|reset-password.
│   ├── users.py                   # /api/users/profile|settings|password|delete|conversations.
│   ├── classes.py                 # /api/classes/** (CRUD, enrollment, leaderboard).
│   ├── chapters.py                # /api/chapters/** (CRUD, PDF upload, exercise generation).
│   ├── exercises.py               # /api/exercises/** + progress + leaderboard.
│   ├── ai.py                      # POST /api/ai/chat (Gemini proxy, rate-limited, payload-capped).
│   ├── lti.py                     # LTI 1.3 launch + AGS grade passback.
│   ├── sso.py                     # OIDC SSO login flow + admin provider management.
│   ├── tenant_admin.py            # /api/tenant-admin/** (tenant-scoped admin).
│   ├── superadmin.py              # /api/superadmin/** (platform-wide admin).
│   └── health.py                  # GET /api/health, /api/health/detail, /api/csrf-token, /api/tasks/<id>.
│
├── 🗃️ /repositories/ (SQL ONLY — no business logic)
│   ├── auth_repository.py         # User lookup, insert, email-exists, tenant matching.
│   ├── class_repository.py        # Class CRUD, enrollment, leaderboard queries.
│   ├── chapter_repository.py      # Chapter CRUD, PDF metadata.
│   ├── sso_repository.py          # OIDC provider config (Fernet-encrypted client_secret).
│   └── (+ more per domain)
│
├── ⚙️ /services/ (BUSINESS LOGIC)
│   ├── exercise_generator.py      # Gemini REST call → validated JSON exercise list.
│   ├── content_extractor.py       # PyPDF2 / docx / csv / ipynb text extraction.
│   └── code_runner.py             # Sandboxed code execution.
│
├── 🔄 /workers/ (CELERY ASYNC TASKS)
│   ├── celery_app.py              # Celery app factory + task routing + beat schedule.
│   └── tasks.py                   # Task definitions with exponential-backoff retry logic.
│
├── 🎨 /templates/ (THE VIEW LAYER - Server Rendered HTML/Jinja)
│   ├── base.html                  # THE MASTER TEMPLATE: Contains the `<head>`, global navbars, footer, and `{% block content %}`. All other pages `extend` this.
│   ├── index.html                 # Marketing Landing Page: High-performance animations, feature breakdowns.
│   ├── login.html / reset*.html   # Standard Auth UI shells.
│   ├── profile.html               # User settings and theming preference dropdowns.
│   ├── contact.html               # Static informational page.
│   ├── privacy.html / terms.*     # Legal and compliance documentation (GDPR, FERPA statements).
│   │
│   ├── 👨‍🎓 STUDENT PORTAL VIEWS
│   │   ├── student-classes.html   # The grid dashboard of enrolled courses with progress tracking.
│   │   ├── student-class.html     # The interior of a specific course, listing chapters sequentially.
│   │   └── chapter-view.html      # The immersive learning split-screen (PDF left, exercises right).
│   │
│   ├── 👨‍🏫 PROFESSOR PORTAL VIEWS
│   │   ├── professor-dashboard.html# The hub. Create new classes, view aggregate student health across all courses.
│   │   ├── professor-class.html   # Deep dive into a specific roster, gradebook leaderboards, and module editing.
│   │   └── upload-assistant.html  # The drag-and-drop PDF ingestion and AI-generation review workflow interface.
│   │
│   ├── 🛠️ INTERACTIVE TOOL VIEWS
│   │   ├── practice-playground.html# The sandbox. Embedded code editor, console output simulator, and floating AI hint widget.
│   │   └── code-assistant.html    # A full-width ChatGPT-style interface for general coding queries.
│   │
│   └── 🔗 LTI INTEGRATION VIEWS
│       ├── lti-setup.html         # Form to generate Consumer Keys and Shared Secrets for LMS Admins.
│       ├── lti-launch.html        # An interstitial "Loading..." screen validating the OAuth handshake.
│       ├── lti-deep-link.html     # The UI inside Canvas where a professor selects *which* AnalytIQ assignment to link.
│       └── lti-launch-error       # Graceful degradation UI if the OAuth signature fails.
│
├── 🖌️ /css/ (THE STYLE ARCHITECTURE)
│   ├── style.css                  # Base resets, typography, and utility classes.
│   ├── dashboard.css              # Grid layouts specific to the portal interfaces.
│   └── local-dev-dark-theme.css   # **THE HERO THEME**: Contains all the Middle-Eastern inspired, high-contrast, glassmorphism CSS Variables, gradients, and hover state animations.
│
├── ⚙️ /js/ (THE CLIENT EXECUTORS)
│   ├── api-helper.js              # **CRITICAL**: The centralized `fetch` wrapper. It automatically injects the JWT Header, checks for 401 Expirations, caches GET requests identically, and handles network timeouts.
│   ├── auth.js                    # Binds to the login/register forms, manages `localStorage` session creation and wiping on logout.
│   ├── home-animation.js          # IntersectionObservers and scroll-trigger animations for the `index.html` marketing page.
│   ├── code-assistant.js          # Manages the chat history arrays, binds enter-key submission, auto-scrolls the chat window, and handles markdown-to-HTML rendering of the AI's response.
│   ├── student-*.js               # Event bindings specific to student interactions (e.g., submitting an exercise).
│   ├── professor-*.js             # Analytics chart rendering (e.g., Chart.js initializers) and handling the PDF upload multi-part form data pipeline.
│   └── upload-workflow.js         # The complex state-machine handling the transition from "PDF Uploading" -> "AI Generating (polling)" -> "Approval Table Rendered."
│
└── 📚 /docs/ (THE KNOWLEDGE BASE)
    ├── PROJECT_OVERVIEW.md        # (You are here). The master document.
    ├── ARCHITECTURE.md            # Deep dive into the database schema and scaling heuristics.
    ├── ACCESSIBILITY.md           # WCAG/A11y compliance notes and keyboard navigation standards.
    ├── SECURITY.md                # Threat models, CSRF handling logic, and penetration testing guidelines.
    └── knowledge_base/            # Auto-generated granular breakdowns of specific functions split across enumerated folders (e.g., 01-Security-Authentication.md).
```
