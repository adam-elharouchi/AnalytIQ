# AnalytIQ Messaging — Single Source of Truth

**Owner:** marketing agent
**Created:** 2026-08-16
**Status:** Living document. Every external-facing asset (site copy, one-pager, case studies, LinkedIn posts, sales outreach, papers) must match this file's positioning line, priority order, and never-say list exactly. If a new asset needs different wording, fix the asset — propose the change here first, don't drift silently.

This is the first version of this file. A previous cycle's digest claimed this file was written on 2026-08-15; it was not — no `marketing/` directory existed until this session (2026-08-16). Treat anything referencing an earlier version of this file as false.

---

## 1. Positioning line (verbatim — use everywhere, do not paraphrase)

> **"The alignment layer between a professor's own syllabus and student practice."**

Use this exact sentence, or a direct quote of it, in: the site's Problem section, the one-pager header, every case study's opening line, and any external deck. Do not substitute synonyms ("bridge," "connector," "layer" swapped for something else) — the point is that every asset uses the *same* sentence, so it reads as one company with one idea, not five people's paraphrases.

## 2. One-sentence pitch

> AnalytIQ turns a professor's own syllabus into auto-graded, interactive coding exercises in under 60 seconds — so students practice exactly what was taught, and professors stop building or grading practice material by hand.

Longer version (for About/one-pager use): AnalytIQ is the alignment layer between a professor's own syllabus and student practice. Upload a course PDF; AnalytIQ generates unit-tested coding exercises locked to that professor's own content, notation, and examples — not a generic curriculum. Students get an AI tutor that only knows the course material. Professors get the prep and grading work off their plate and a real-time view of who's struggling.

## 3. Audience

- **Primary (user + champion):** Individual professors at business schools / university departments teaching quantitative or coding-adjacent courses (analytics, statistics, data science, intro programming) who today either (a) build practice problem sets and grade them by hand, or (b) send students to a generic platform (Datacamp, Coursera) that doesn't match what they taught.
- **Secondary (buyer, once a champion exists):** Department chairs / tenant admins evaluating a department-wide license after one professor has used it for a semester.
- **Not the primary copy audience:** Students. They are the end user and every asset should describe their experience, but the copy voice speaks to the professor first — the professor is who reads the site, receives the outreach email, and decides to pilot it.

## 4. Top three benefit claims — required priority order

Every asset (site, one-pager, case studies, LinkedIn) must lead in this order. Don't reorder for variety; the whole point of Phase 2 is consistent positioning.

1. **Professor time savings — always first.** The prep and grading work AnalytIQ removes from a professor's week. Headline framing target: *"Get hours back every week."*
   **Evidence status:** `[UNSUPPORTED — do not publish as a stated fact]`. **"5 hours a week back" is a positioning target drawn from informal professor feedback during the pilot, not a measured metric.** It has not been said by name by any professor with permission to quote them (see `reports/sales-outreach/TESTIMONIAL_TRACKER.md` — zero testimonials received as of 2026-08-16). It may **only** appear in copy once it is inside a named, permissioned professor quote, in their own words. Until then, all time-savings copy must describe the *mechanism* (upload → auto-generated, auto-graded exercises) rather than assert a specific number of hours saved.
2. **Testimonials — second.** Named professors, quoted, with explicit permission to use name + title. **Currently zero in hand** — this entire priority tier is blocked until at least one lands. See `reports/sales-outreach/TESTIMONIAL_TRACKER.md`.
3. **Student outcomes — third.** Framed as *product description* (what a student experiences: exercises aligned to their own professor's material and notation, immediate auto-grading, an AI tutor bound to course content only) — **not** as a measured-results claim. No pass-rate, retention, completion, or grade-improvement statistic may be used; the fall-semester outcomes study (`research-academic` agent mission) hasn't run yet.

## 5. Approved external proof points — the only ones allowed

Nothing outside this list may be used as evidence in an external asset:

- **Named professor testimonials**, with explicit permission for name + title. (Zero in hand as of 2026-08-16.)
- **"Live at Hult International Business School on Canvas + Moodle via LTI 1.3."** Verified: `templates/landing.html` LMS-integration claims are substantiated by real AGS grade-passback code (`blueprints/lti.py:899-941`, per `reports/security-engineer/PACKET_CLAIM_GAPS.md` "Verified as accurate" section).
- **Demo speed** — "under 60 seconds" from PDF upload to generated, unit-tested exercises. Already live on the site (hero demo card, comparison table). Do not attach a more specific number (e.g., "1.26 seconds") — that figure is an internal engineering measurement (`docs/DEMO_READINESS.md`, local Docker Postgres, no network latency, no live Gemini call in that specific run) and is not the number the public claim should use.
- **The compliance packet** — once assembled. **Not usable yet.** `reports/security-engineer/PACKET_CLAIM_GAPS.md` tracks open gaps (CSP enforcement is qualified/partial, CSRF tokens are not validated, encryption-at-rest is unverified, FERPA compliance is documentation-only "provided at contract signing," not a certification). Do not reference "the compliance packet" externally until security-engineer confirms it's closed.
- **EDULEARN26 abstract acceptances.** Two abstracts accepted; full papers targeted for Nov 15 (`.claude/agents/research-academic.md`). Say "abstracts accepted to EDULEARN26" or "papers accepted for EDULEARN26" — do not say "published" or "presented" (nothing has been presented yet) and do not say "peer-reviewed" until the full papers clear review.

## 6. Never-say list — violating any of these pulls the asset

- **No usage numbers of any kind, anywhere, in any external asset.** No user counts, professor counts, class counts, exercise counts, completion counts, WAU/MAU, or vague-but-still-a-number phrasing ("dozens of," "a growing number of," "hundreds of students"). Source of the ban: `reports/metrics-engineer/CANONICAL_NUMBERS.md` — every number in that file is PRIVATE and pre-fall-semester; nothing from it appears externally until fall data replaces it **and Adam explicitly approves that specific export.**
- **No "100% organic adoption" or any other adoption/growth claim** — same category as above, currently live on `templates/landing.html:637` and flagged for removal in `marketing/SITE_COPY_2026-08.md`.
- **No "5 hours a week" (or any specific number of hours) asserted as AnalytIQ's own claim.** Only inside a quoted, named, permissioned testimonial, in the professor's own words.
- **No acqui-hire openness and no walk-away number**, ever, in anything external.
- **No SAML claim.** Only OAuth2/OIDC is implemented; SAML is "available on request" (`templates/landing.html:949`, corrected per `PACKET_CLAIM_GAPS.md` row 17).
- **No unqualified "FERPA compliant."** Only "FERPA compliance documentation provided at contract signing" (`templates/landing.html:951`, `PACKET_CLAIM_GAPS.md` row 18) — there is no standalone FERPA compliance document today.
- **No unqualified "CSP enforced" or clickjacking protection claim.** `frame-ancestors` and most CSP directives ship Report-Only regardless of the `CSP_ENFORCE` flag (`PACKET_CLAIM_GAPS.md` §"Runtime config verification (B7)").
- **No "CSRF tokens are validated."** They are not — JWT header auth is the actual mitigation (`docs/security/JWT_CSRF_MITIGATION.md`).
- **No "encryption at rest" claim.** Unverified infrastructure property; do not assert either way.
- **No "AI chat data is temporary" claim.** It is retained persistently until the user deletes the conversation or account (`templates/privacy.html`, corrected 2026-08-12).
- **No fabricated or estimated learning-outcomes statistics** — no claimed pass-rate lift, retention lift, or grade improvement, until the fall outcomes study produces real data and Adam approves release.
- **No claim published without a traceable source.** `research/EVIDENCE.md` (the evidence gate named in `.claude/agents/research-academic.md`) **does not exist yet** as of 2026-08-16 — confirmed via repo search. Until it exists, every verifiable-fact claim in a marketing asset must cite its source inline (a `reports/` file, a `templates/` line, or this file) so Adam can check it before approving.
- **No "EDULEARN26 published" or "peer-reviewed."** Abstracts are accepted; full papers are not yet drafted (target Nov 15) or reviewed.
- **No immigration, contract, or regulatory-certification claim without the standard note**: "Requires licensed professional review — this is preparation, not advice."

## 7. Source-of-truth files this messaging depends on

| File | What it governs |
|---|---|
| `reports/metrics-engineer/CANONICAL_NUMBERS.md` | Every usage number that exists — all PRIVATE, none external |
| `reports/security-engineer/PACKET_CLAIM_GAPS.md` | What compliance/security claims are currently true vs. not, with file:line evidence |
| `reports/sales-outreach/TESTIMONIAL_TRACKER.md` | Testimonial status — 0 of 3 received as of 2026-08-16 |
| `.claude/agents/research-academic.md` | EDULEARN26 status, fall outcomes study status |
| `research/EVIDENCE.md` | Does not exist yet. Should be the evidence gate for every public claim once `research-academic` creates it. |
| `templates/landing.html` | The live site markup this messaging maps against (see `marketing/SITE_COPY_2026-08.md`) |

## 8. Open flags for Adam (not blocking this file, but every downstream asset inherits them)

1. `research/EVIDENCE.md` doesn't exist. Recommend asking `research-academic` to create it before Phase 2 outreach leans harder on EDULEARN or outcomes claims.
2. Zero testimonials are in hand. The #2 priority claim tier and one of the four LinkedIn drafts are blocked on this alone.
3. "5 hours a week back" cannot be published as AnalytIQ's own claim until a named professor says it. Decide now whether Aug 19's site relaunch ships without a specific number (safe, ready today) or waits for a testimonial to supply one (stronger, but has no committed date).
