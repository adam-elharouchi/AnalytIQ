# What Was Added — AnalytIQ Feature Guide

> Simple reference for everything shipped in the recent build sprint.
> Covers: Superadmin, LMS Integration, External Content Import, and platform improvements.

---

## 1. Superadmin Role

### What it is
A special admin role that can see and control the entire platform — all users, all classes, all tenants. Think of it as a "god mode" for the platform owner.

### How you get it
**Automatic.** Any account registered with an `@myanalytiq.org` email address is automatically assigned the `superadmin` role at signup. No manual steps needed.

> Example: `adam@myanalytiq.org` → superadmin on first login.

You can also manually promote any existing user via the dashboard (change role button).

### What the dashboard does

Go to `/superadmin-dashboard.html` after logging in with a `@myanalytiq.org` account.

| Section | What you can do |
|---|---|
| **Platform Analytics** | Total users, new signups (7d/30d), active users, classes, chapters, exercises, completions, daily registration chart, top audit actions |
| **Tenant Management** | Create/enable/disable tenants (institutions). Each tenant shows user + class counts |
| **Global User Search** | Search all users by name/email. Filter by role (student/professor/superadmin) or status (active/disabled). See which tenant they belong to |
| **User Actions** | Enable or disable accounts, change roles, force password reset, export a user's data as JSON (GDPR), permanently delete a user |
| **Class Management** | See every class on the platform. Transfer a class to a different professor. Delete a class |
| **Impersonation** | Log in as any non-admin user to debug or support them — opens in an iframe modal, click "Exit" to return to your session |
| **Contact Submissions** | Read all messages submitted via the contact form. Mark them as read/resolved/archived |
| **Audit Log** | Full timestamped trail of every sensitive action on the platform (create user, disable user, impersonate, delete class, etc.) |
| **Announcements** | Write banners that appear on every page for all users, specific roles, or with expiry dates |
| **Platform Config** | Toggle maintenance mode on/off, set a maintenance message, open/close new registrations |
| **IP Blocklist** | Block specific IP addresses platform-wide |

### Do you need to do anything?
- Make sure your admin email ends in `@myanalytiq.org`
- The `superadmin_dashboard.html` page must be deployed — it is in the `templates/` folder
- The DB needs the tables: `tenants`, `audit_log`, `announcements`, `platform_config`, `ip_blocklist` — these are created by the migration runner on startup

---

## 2. Tenants

### What it is
A "tenant" represents an institution (e.g. Hult University, MIT). Users and classes can be grouped under a tenant. Useful if you ever want to offer AnalytIQ to multiple schools.

### How it works
- Tenants are created by a superadmin from the dashboard
- Users and classes have an optional `tenant_id` column
- Deleting a tenant does NOT delete users/classes — it just removes the grouping
- LMS platforms (Canvas, Blackboard, etc.) are linked to tenants via `lti_issuer`

### Do you need to do anything?
Not immediately. Tenants are optional — users and classes work fine without one. Only relevant if you onboard a second institution.

---

## 3. LMS Integration (LTI 1.3)

### What it is
Lets professors connect AnalytIQ to their university's Learning Management System (Canvas, Blackboard, Moodle, D2L, Google Classroom). Students can then launch AnalytIQ directly from inside their LMS without creating a separate account.

### How it works end-to-end
1. Professor goes to the "LMS Setup" tab on their dashboard
2. They copy AnalytIQ's JWKS URL, login URL, and launch URL into their LMS's "External Tool" settings
3. They register the LMS in AnalytIQ by entering the LMS's issuer URL, client ID, and token URLs
4. Students click the tool link inside the LMS → they are automatically logged into AnalytIQ (account created if first time)
5. Professor can click "Sync from LMS" on the Students tab to pull the full roster from the LMS automatically
6. Grades can be passed back from AnalytIQ exercises to the LMS gradebook (per-class toggle)

### Deep Linking
When a professor adds AnalytIQ as a tool in the LMS, they can pick a specific chapter to link directly. Students clicking that link land on exactly that chapter.

### Do you need to do anything?
- Run `python scripts/generate_lti_keys.py` once to create the RSA key pair (needed for LTI JWT signing)
- Add the generated keys as env vars: `LTI_PRIVATE_KEY` and `LTI_PUBLIC_KEY`
- The LTI tables (`lti_configurations`, `lti_sessions`) are created by the migration runner

> If you are not connecting to a university LMS right now, you can ignore this entirely.

---

## 4. External Content Import

### What it is
Professors can now import chapter content from the web instead of only uploading PDF files. A 5-tab "Import from Web" modal appears next to the "Upload Chapter" button.

### The 5 sources

| Tab | What it does |
|---|---|
| **Paste URL** | Enter any public webpage URL. AnalytIQ fetches it, strips ads/nav, extracts the main content, and stores it as a chapter |
| **PyPI Docs** | Enter a Python package name (e.g. `pandas`). AnalytIQ fetches its README/documentation from PyPI and stores it |
| **OpenStax** | Browse ~250 free OpenStax textbooks by subject. Pick a book → pick a chapter → import it |
| **LibreTexts** | Search across 12 LibreTexts subject libraries (chemistry, physics, math, etc.) |
| **OER Commons** | Search the OER Commons open-resource catalogue |

### What happens after import
- The content is stored as HTML in the chapter's `pdf_data` field
- The existing AI exercise generation pipeline runs on it the same way it does for PDFs
- Students see the content and exercises exactly like any other chapter

### Do you need to do anything?
Nothing extra — it uses existing infrastructure. BeautifulSoup is already in `requirements.txt`. The "Import from Web" button appears automatically on the professor's class page.

---

## 5. Audit Log

### What it is
Every sensitive action on the platform is recorded in the `audit_log` table with: who did it, what they did, what resource was affected, when, and from what IP.

### What gets logged
User signup, password reset, profile update, password change, user delete, exercise submission, class create/delete, enroll/unenroll, chapter create/delete, exercise delete, tenant create/update, user disable/enable, impersonation, force-reset, role change, class transfer.

### Where to see it
Superadmin dashboard → Audit Log tab. Filterable by action type, actor, resource type, and date range.

### Do you need to do anything?
Nothing. It runs automatically. The `audit_log` table is created on startup.

---

## 6. Announcements & Maintenance Mode

### Announcements
Superadmins can create banners (info / warning / danger / success) that appear on every page. They can be targeted to specific roles (e.g. only professors) and set to expire automatically.

Every page calls `/api/platform/status` on load and renders any active banners.

### Maintenance Mode
From the Platform Config panel, flip `maintenance_mode = true` and optionally set a `maintenance_message`. The frontend reads this on load and can display a maintenance notice.

### Do you need to do anything?
The `announcements` and `platform_config` tables are created automatically. No extra setup.

---

## 7. Other Platform Improvements (quick summary)

These were also shipped but are mostly invisible — they just make the platform better:

| Feature | What changed |
|---|---|
| **Blueprint architecture** | `app.py` went from 5,391 lines to 412. Code is now split into 7 domain blueprints and 5 repositories |
| **Caching** | 8 endpoints now cache per-user. Write operations clear the relevant cache automatically |
| **AI rate limiting** | 20 requests/min + 100/hr per user on the AI chat endpoint |
| **AI circuit breaker** | If Gemini fails 5 times in a row, requests are blocked for 60 seconds before retrying |
| **Offline banner** | A red "You are offline" banner appears if the user loses internet |
| **Request tracing** | Every request gets a unique ID in logs and the `X-Request-ID` response header |
| **Autosave in playground** | Exercise code is auto-saved to localStorage every 500ms. Restored on page reload |
| **Confirm modals** | Browser `confirm()` dialogs replaced with styled modals (keyboard accessible) |
| **Design tokens** | All colours are now CSS variables — one file to change the whole look |
| **Password rules** | Minimum 8 characters, maximum 72 characters enforced at signup |
| **Leaderboard auth** | Leaderboard endpoints now require login. Emails removed from responses |
| **File upload types** | Chapters now accept `.pdf`, `.ipynb`, `.docx`, `.csv`, and `.txt` |
| **Jinja2 templates** | All 17 HTML pages share a single `base.html` (consistent header/footer/scripts) |
| **GDPR export** | Superadmin can download all data for any user as a JSON file |

---

## Quick Reference: Who Gets What Role

| Email domain | Role assigned at signup |
|---|---|
| `@myanalytiq.org` | **Superadmin** |
| `@hult.edu` | Professor |
| `@faculty.hult.edu` | Professor |
| `@student.hult.edu` | Student |
| Anything else | Student |

Superadmins can manually change any user's role via the dashboard at any time.

---

## Checklist: Things You May Need to Do

- [ ] Sign up (or convert an existing account) with an `@myanalytiq.org` email to get superadmin access
- [ ] Run `python scripts/generate_lti_keys.py` and add `LTI_PRIVATE_KEY` / `LTI_PUBLIC_KEY` env vars if you plan to use LMS integration
- [ ] On Render, trigger a redeploy so the migration runner creates the new DB tables (`tenants`, `audit_log`, `announcements`, `platform_config`, `ip_blocklist`, `lti_*`)
- [ ] Visit `/api/superadmin/analytics` or the superadmin dashboard to confirm it works after deploy
