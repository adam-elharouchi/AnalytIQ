# ADR-003: React + TypeScript Frontend (Strangler-Fig Migration)

**Status:** Accepted
**Date:** 2026-03-22

---

## Context

The original frontend was 14 vanilla-JS modules + 14 Jinja2 HTML templates.
While fast to load and simple to understand, it had accumulated significant
maintenance friction:

- No type safety: `authFetch()` returned `any`; shape mismatches caused
  silent runtime errors.
- Auth state in `localStorage` with no lifecycle hooks: stale tokens led to
  confusing 401 loops without helpful redirects.
- Scattered API call patterns: each page had its own inline `fetch` logic with
  no shared error handling.
- No build step meant no dead-code elimination, no TypeScript, and no
  component reuse.

A full rewrite would break the live site and require months of parallel
maintenance. A framework-only approach (e.g., just adding TypeScript to
existing files) would not address the structural problems.

---

## Decision

Adopt a **strangler-fig migration** using **Vite 6 + React 18 + TypeScript**:

1. **Coexistence**: Flask continues serving Jinja2 templates for legacy routes.
   React handles a defined set of routes (`/login`, `/classes`, `/dashboard`,
   `/admin`). Flask's catch-all route checks `_REACT_ROUTES` and serves
   `static/react/index.html` for those paths; all others fall through to
   Jinja2.

2. **Build output**: Vite builds to `static/react/` which Flask serves as
   static files. The React index.html is the SPA shell; React Router v6
   handles client-side navigation within the React boundary.

3. **Typed API client**: `frontend/src/api/client.ts` wraps `fetch` and
   returns `ApiResult<T>` — a discriminated union of `{ok, data, error,
   status}`. All API calls go through this layer; no inline `fetch` in
   components.

4. **Auth context**: `AuthContext` (React context + `useAuth()` hook) manages
   JWT storage, expiry detection, and provides typed `user` / `signIn` /
   `signOut` to all components. Replaces the `AuthManager` class in
   `auth.js`.

5. **Data fetching**: TanStack React Query v5 with 30s `staleTime`. Cache
   invalidation is explicit (not time-based) for mutation side effects.

6. **`PrivateRoute`**: Auth + role guard component that redirects to `/login`
   if unauthenticated, or to the user's home route if role is insufficient.

7. **Lazy loading**: Each page is `React.lazy()`-loaded with `<Suspense>` to
   keep the initial bundle small.

---

## Consequences

**Positive**
- End-to-end type safety from API response shape to rendered UI.
- Auth bugs (stale tokens, missing redirects) are caught at compile time.
- React Query eliminates manual loading/error state management in every
  component.
- Legacy pages keep working unchanged; migration is incremental.
- Production bundle: 202 KB main (65 KB gzip) with lazy-split pages.

**Negative / Trade-offs**
- Contributors must run `make frontend-build` (or `make frontend-dev` during
  development) — a build step is now required.
- Two frontend paradigms exist simultaneously until migration is complete.
  The `_REACT_ROUTES` set in `core/factory.py` must be kept in sync with
  `frontend/src/App.tsx` routes.
- Node.js 20 is required in CI and locally (added to `ci.yml` and `Makefile`).

---

## Alternatives Considered

- **Vue 3 + Composition API** — comparable DX; React chosen for wider
  familiarity and larger component ecosystem.
- **HTMX** — keeps server-side rendering, avoids build step; ruled out because
  it doesn't provide type safety and wouldn't scale to the interactive code
  playground use case.
- **Full Jinja2 + vanilla JS hardening** — no path to type safety; ruled out.
