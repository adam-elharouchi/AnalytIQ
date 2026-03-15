# AnalytIQ Documentation

Central documentation for the AnalytIQ project.

## Architecture & System Design

| File | Description |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Repository layout, request lifecycle, database schema, auth flow, deployment |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | High-level vision, personas, tech stack summary |
| [12-Superadmin-Architecture.md](12-Superadmin-Architecture.md) | Evolution of the superadmin role (boolean → dedicated RBAC role) |
| [14-SSO-Tenant-Authentication.md](14-SSO-Tenant-Authentication.md) | Per-tenant OIDC SSO, role model, tenant_admin, JWT changes |

## Security

| File | Description |
|---|---|
| [SECURITY.md](SECURITY.md) | Auth, authorization, passwords, rate limits, headers, CSRF, audit log |
| [ACCESSIBILITY.md](ACCESSIBILITY.md) | WCAG 2.1 AA audit results and compliance checklist |
| [RENDER_ENV_CHECKLIST.md](RENDER_ENV_CHECKLIST.md) | All environment variables, what each does, deployment checklist |

## Features

| File | Description |
|---|---|
| [AI_EXERCISE_GENERATION.md](AI_EXERCISE_GENERATION.md) | Content extraction, Gemini prompt engineering, language detection |
| [OUTPUT_BASED_GRADING.md](OUTPUT_BASED_GRADING.md) | Grading schema (0–100), sandbox security, supported languages, test case structure |

## Operations & Development

| File | Description |
|---|---|
| [testing_qa.md](testing_qa.md) | How to run tests, test structure, DB mocking, CI pipeline |
| [TASKS.md](TASKS.md) | Completed work log from Feb 2026 sprint (99 tasks) |
| [WHATS_NEW.md](WHATS_NEW.md) | Changelog: superadmin, tenants, LTI, SSO, content import |
| [CODEBASE_AUDIT_MARCH_2026.md](CODEBASE_AUDIT_MARCH_2026.md) | March 2026 full audit: endpoints, schema, security gaps, known issues |
