PRIVATE — internal only. This file cites canonical usage numbers, private engineering
measurements, and internal-only audit findings (per `ANALYTIQ_AGENT_ORCHESTRATION.md` §8).
Never publish or paste this file, or any number/quote from it, into an external-facing draft.
The file's *conclusions* (verdicts) are what other agents act on; the private evidence backing
a SUPPORTED verdict stays in here, not in the asset that cites it.

# AnalytIQ — Public Claims Evidence Register

**Created:** 2026-08-22 (headless cycle). This file did not exist before today — see B30
in `reports/STATE.md`. Its absence is the direct upstream cause of B26 (`templates/landing.html:649`
publishing "100% organic adoption" for weeks with no one catching it).
**Owner:** `research-academic` agent.
**Status:** First full sweep. Not exhaustive of every sentence in every document — exhaustive of
every claim-shaped assertion of fact on the surfaces named in this session's brief:
`templates/`, `marketing/`, `sales/`, plus the compliance-adjacent claims in `templates/privacy.html`
and `templates/terms.html` that `reports/security-engineer/PACKET_CLAIM_GAPS.md` already carries
in more depth (cross-referenced here, not re-derived, per the mission brief's instruction to
cross-reference rather than duplicate work).

---

## How to use this file (read before shipping any public claim)

1. **Before any claim ships** — on the live site, in a sales email, a LinkedIn post, a paper, a
   one-pager, a buyer memo, anything a person outside AnalytIQ will read — it must have a row in
   this file with a verdict of `SUPPORTED`. `WEAK` claims may ship only with the qualifying
   language this file specifies attached. `UNSUPPORTED` claims **do not ship**, full stop, until
   evidence is found or the claim is rewritten to match what evidence actually supports.
2. **Adding a row:** quote the claim verbatim, cite exactly where it appears (`file:line`), open
   the evidence yourself and cite what you actually found (a file:line, a named artifact, a test
   result) — never assert evidence you did not open. If you searched and found nothing, the
   evidence column says `none found` and the verdict is `UNSUPPORTED` — that is a valid, useful
   finding, not a failure to complete the row.
3. **An `UNSUPPORTED` verdict blocks publication.** If the claim is already live (like B26), it
   gets flagged to the orchestrator immediately, not queued — every day it stays live is a day a
   buyer's engineer, a professor, or a journalist can catch it before Adam does.
4. **Usage numbers are a special case.** A number can be true, sourced, and still barred from
   external use — see `ANALYTIQ_AGENT_ORCHESTRATION.md` §8. Those rows get
   `SUPPORTED — but PRIVATE, barred from external use by §8`, a fourth de facto verdict that
   still means "does not ship," just for a different reason than `UNSUPPORTED`. Do not confuse
   the two when reporting to Adam — one means "not true/not proven," the other means "true but
   the numbers policy forbids saying it yet."
5. **Re-check, don't inherit.** Code changes. A row marked `SUPPORTED` in August can go stale by
   October. Anyone citing a row from this file for a new asset should spot-check the underlying
   file:line still says what this file claims it says, the same discipline `STATE.md`'s update
   rules (d) and (o) apply to blockers and capabilities.
6. **This file is the gate; `marketing` and `sales-outreach` answer to it** (per
   `.claude/agents/research-academic.md` item 3). If those agents' own drafts (`MESSAGING.md`,
   `SITE_COPY_2026-08.md`, sales templates) already did solid inline evidence-citing work — several
   have — this file cross-references them rather than re-deriving from scratch, but the verdict
   recorded here is authoritative when the two disagree.

---

## Summary — what needs Adam's decision right now

| # | Claim | Verdict | Why it matters |
|---|---|---|---|
| 2 | "100% organic adoption" (`landing.html:649`) | **UNSUPPORTED** | B26. Live on the site today. Two ready diffs in `marketing/B26_LANDING_FIX.md`. |
| 15 | "No hallucination" (`landing.html:810`) | **UNSUPPORTED** | Live on the site today. New finding — no prior sweep caught it. |
| 16 | "drive student engagement and completion rates" / "Increases completion" tag (`landing.html:828-829`) | **UNSUPPORTED** | Live on the site today. New finding — an outcomes claim in the Features section, the exact category `MESSAGING.md` §6 bars until the fall study runs. |
| 21 | "AnalytIQ is already live and being used at Hult — organically... without anyone at EF asking them to" (`sales/EF_HODGES_FORCING_EMAIL.md`) | **UNSUPPORTED** | Not yet sent (per `sales/EF_HODGES_FORCING_EMAIL.md`'s own "Needs Adam" list) but queued for a real external recipient (Stephen Hodges/EF), overdue since Aug 15/18. Same root cause as B26 — traces to the same unevidenced source. |
| 7 | "In under 60 seconds" (hero, demo card, how-it-works, comparison table — 4 places) | **WEAK — needs qualification** | The site's single most-repeated claim. The only measurement on file explicitly excludes the one step ("Gemini round-trip") the claim is actually about. |
| 10 | "Canvas, Blackboard, and Moodle" (`landing.html:822-823`) | **WEAK — needs qualification** | Named Blackboard has zero live customer and zero Blackboard-specific setup evidence, unlike Canvas + Moodle. |
| 19 | "Encryption at rest" (`privacy.html`) | **UNSUPPORTED** (per this file's strict rule; `security-engineer` calls it "unverified," not "false") | 2-minute Supabase dashboard check would resolve it, same pattern as the B7 check Adam already did once. |
| 25 | "abstracts... accepted to EDULEARN26" (marketing/sales drafts, not yet live) | **WEAK — needs qualification** | Sole source is the agent's own mission brief, not a primary acceptance artifact. Likely true; unverified in-repo. |

Full detail for every row below.

---

## 1. `templates/landing.html` — the live public site (Render serves this directly)

| # | Claim (verbatim) | Where | Evidence | Evidence strength | Verdict |
|---|---|---|---|---|---|
| 1 | "Live at Hult International Business School" | `landing.html:649` (hero trust line), `:711` (proof bar, "Active at...") | Real AGS grade-passback code implementing LTI 1.3 launch + grade sync: `blueprints/lti.py:899-941`. Independently confirmed accurate in `reports/security-engineer/PACKET_CLAIM_GAPS.md` "Verified as accurate" section. Approved proof point, `marketing/MESSAGING.md` §5. | Code, verified directly this session (read `blueprints/lti.py` header + cross-checked security-engineer's prior line-citation). | **SUPPORTED** |
| 2 | "100% organic adoption" | `landing.html:649` (hero trust line, same sentence as #1) | **none found.** Not in `reports/metrics-engineer/CANONICAL_NUMBERS.md`, not in `marketing/MESSAGING.md`'s approved proof-point list (§6 explicitly bans "any other adoption/growth claim" naming this exact phrase). No survey, no professor statement, no measurement of "organic" vs. any other adoption channel exists anywhere in this repo. | none found | **UNSUPPORTED — remove or replace.** This is **B26** — see `marketing/B26_LANDING_FIX.md` for two ready-to-apply diffs (delete the clause, or replace with "Abstracts accepted, EDULEARN26"; recommends deletion). Not applied to any file this session, per this session's guardrails — Adam approves and pushes. |
| 3 | "Canvas & Moodle ready · LTI 1.3" | `landing.html:702` (proof bar) | Same LTI evidence as #1; both LMSs are the ones actually live at Hult. | Code, verified directly. | **SUPPORTED** |
| 4 | "Refund through week 4 · No lock-in" | `landing.html:704` (proof bar) | Not a fact-of-the-world claim — a policy commitment Adam has made identically in every sales draft: `sales/ORDER_FORM.md:50-54`, `sales/STRIPE_INVOICE_TEMPLATE.md:44-59`, `sales/MASTER_TEMPLATE.md:37,62`. Consistent across all four documents, no discrepancy found. | Cross-referenced across 4 internal drafts, consistent. | **SUPPORTED — as policy.** Flag (not a verdict downgrade): the refund-guarantee language itself has not had attorney review (`sales/STRIPE_INVOICE_TEMPLATE.md:75` already notes this). |
| 5 | "Practice built from your own chapters · Upload a PDF" | `landing.html:706` (proof bar) | Matches the real upload→generate flow: `services/exercise_generator.py` (Gemini prompt pipeline), `services/content_extractor.py:15` (`_SUPPORTED_EXTENSIONS`). | Code, verified directly. | **SUPPORTED** |
| 6 | "Multi-format import... Supports PDF, DOCX, CSV, Jupyter notebooks, and web URLs" | `landing.html:761-763` (Step 01 card) | `services/content_extractor.py:15` — `_SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".csv", ".ipynb", ".docx"}`, with dedicated extraction functions for each. Web-URL import is real: `blueprints/content_import.py` (`POST /api/classes/<id>/chapters/import`, plus OpenStax/LibreTexts/OER-Commons search routes). | Code, verified directly (read both files this session). | **SUPPORTED** |
| 7 | "In under 60 seconds" (four occurrences: hero H1 `:636`, demo-card result `:689`, How-It-Works step 2 `:771`, comparison table "Setup time" `:877`) | `landing.html:636,689,771,877` | `docs/DEMO_READINESS.md` §4 records a real measured loop: **1.261 seconds**, measured by Adam 2026-08-12. **But that measurement explicitly excludes the one step the claim is actually about**: the loop measured is sign-in → view already-seeded class/exercises → grade one exercise via local code execution → view analytics. The doc's own text: *"no Gemini call is on this path; a live demo that generates exercises from an uploaded PDF will include a Gemini round-trip (~3-6s per chunk) that this measurement does not cover."* The hero copy's literal claim ("Upload your course PDF. AnalytIQ generates... exercises... in under 60 seconds") is about that exact uncovered step. Additionally the 1.261s figure ran against local Docker Postgres, explicitly noted as excluding Supabase network latency and cold-start. Separately, `services/exercise_generator.py:396,480` does instrument real `generation_time_ms` per generation into `exercise_generation_events`, but no aggregate/average of that field has ever been pulled — not in `CANONICAL_NUMBERS.md`, and no session has had DB access to query it (§0.1 of that file, multiple sessions running). The "~3-6s per chunk" figure quoted in `DEMO_READINESS.md` itself has no cited source — grepped for it elsewhere in the repo, found nowhere else, so it reads as an estimate, not a measurement. | Code + one real (but scope-mismatched) measurement + one uncited estimate. | **WEAK — needs qualification.** The mechanism is real (upload → Gemini generates exercises, code is real and runs), but the specific "under 60 seconds" benchmark for the actual claimed step has never been measured end-to-end, on production or off. Recommend one of: (a) run the real measurement (needs a live `GEMINI_API_KEY` + DB access — an interactive session, not headless) and cite the real number; (b) drop the specific "60 seconds" figure until measured; (c) qualify as "typically under a minute" without presenting it as a verified benchmark. This claim appears 4 times on one page — fixing it once (the underlying evidence) fixes all 4 occurrences at once. |
| 8 | "5–8 unit-tested exercises" / "5–8 unit tests per exercise" | `landing.html:773` (step badge), `:805` (feature tag) | `services/exercise_generator.py:240` — Gemini prompt literally instructs: *"Analyze the chapter below and generate 5 to 8 short, focused coding exercises."* `:323` — *"Generate 5–8 test cases per exercise."* Also documented in `docs/AI_EXERCISE_GENERATION.md:5,100` and `docs/OUTPUT_BASED_GRADING.md:22`. | Code, verified directly (the exact prompt string, not just a doc description of it). | **SUPPORTED**, with a minor caveat: this is an instruction given to an LLM, not a hard-enforced output constraint — no clamping/validation code was found guaranteeing the model never returns 4 or 9. Not enough to downgrade the verdict (it's the designed and documented behavior), but worth knowing if a buyer's engineer counts exercises on a live generation and gets 9. |
| 9 | "Output-based unit testing grades student work on actual results, not string matching. Catches copying, rewards real understanding." (Automated Grading feature) | `landing.html:803-804` | `docs/OUTPUT_BASED_GRADING.md` (grading schema: 80% correctness via test cases, 20% code quality; replaced the prior Levenshtein/string-similarity system). `services/code_runner.py` runs submitted code in a sandbox against real test cases. | Code + doc, verified directly. | **SUPPORTED** |
| 10 | "Plugs directly into Canvas, Blackboard, and Moodle via LTI 1.3." + tag "Canvas · Moodle · Blackboard" (LMS Integration feature) | `landing.html:822-823` | The LTI 1.3 implementation is generic/standards-based — `blueprints/lti.py:2` module header literally reads "LTI 1.3 Blueprint — LMS integration (Canvas, Blackboard, Moodle, D2L, etc.)" — and real AGS grade-passback code exists (`:899-941`, same evidence as #1). **But** there is no live Blackboard customer (Hult runs Canvas + Moodle only, confirmed everywhere else in this repo, e.g. `CANONICAL_NUMBERS.md`, `MESSAGING.md`), no Blackboard-specific setup guide (`docs/LTI-Canvas-Setup-Guide.md` exists; no Blackboard equivalent), and no evidence any session has actually launched AnalytIQ from a real Blackboard instance. | Code (generic capability, real) but zero live-integration or Blackboard-specific test evidence. | **WEAK — needs qualification.** The underlying protocol claim is defensible (a spec-compliant LTI 1.3 tool should work with any LTI 1.3 platform, Blackboard included), but naming Blackboard alongside Canvas and Moodle with equal visual weight implies parity with two systems that are actually live and verified at a real customer. Recommend distinguishing in copy: "Live and verified: Canvas + Moodle (Hult). Standards-compliant with any LTI 1.3 platform, including Blackboard and D2L, on request" — or simply drop "Blackboard" from the always-visible tag until a real Blackboard launch happens. |
| 11 | "The AI assistant only answers questions using your course material as context." + tag "Syllabus-bound hints" (Context-Locked AI Tutor feature) | `landing.html:809-811` | `static/js/ai-agent.js:538-564` (`buildPlaygroundSystemPrompt()`) — the system prompt explicitly restricts the model: *"You MUST focus your hints ONLY on the CURRENT EXERCISE... ALWAYS focus hints on the CURRENT EXERCISE."* The prompt is built from the class's own chapter/exercise content, not generic curriculum. | Code, verified directly (read the actual prompt-construction function). | **SUPPORTED** |
| 12 | "No hallucination." (same Context-Locked AI Tutor feature, same sentence as #11) | `landing.html:810` | **none found.** Grepped the entire repo for "hallucin" — the only hit anywhere is this one line on the landing page itself. No evaluation, no test suite, no measurement of the AI tutor's hallucination rate exists. Constraining a model's *topic* via a system prompt (which #11 does substantiate) does not eliminate hallucination *within* that topic — this is a distinct, stronger, unfalsifiable-in-the-positive claim that no LLM product can truthfully make absent an actual eval. | none found | **UNSUPPORTED — remove or replace.** New finding — no prior session flagged this. Recommend deleting the sentence outright (the "syllabus-bound" framing in the rest of the card already carries the real, evidenced differentiator) rather than trying to qualify "no hallucination" into something true — there is no qualified version of "no hallucination" that both means something and is checkable. |
| 13 | "Student code runs in an isolated sandbox — no setup, no install, no IT involvement. Works in any browser." (Sandboxed Code Execution feature) | `landing.html:797-798` | `services/code_runner.py` (subprocess isolation, `RLIMIT_AS`/`RLIMIT_FSIZE`/`RLIMIT_NPROC`, blocked Python imports, no interactive stdin). `docs/SANDBOX_CONTAINER.md`. Independently verified accurate in `reports/security-engineer/PACKET_CLAIM_GAPS.md` row 6 note: "everything else checked line-for-line against the code and found accurate, including the isolation defence table, fail-closed behaviour." | Code + independent prior security audit, both checked. | **SUPPORTED** |
| 14 | "See who's struggling, which exercises have high fail rates, and overall class progress — all in real time, per student." (Student Analytics Dashboard feature) | `landing.html:815-816` | Real per-class/per-student progress endpoints and views exist: `blueprints/classes.py`, `templates/professor-class.html`, `templates/professor-dashboard.html`. "Real time" here means on-demand fresh query, not push/streaming — no evidence of latency benchmarking, but this is standard usage of the phrase for a queried dashboard and not the kind of claim a reasonable reader would expect to be literally millisecond-live. | Code, verified directly; "real time" read as ordinary dashboard usage, not a benchmarked SLA. | **SUPPORTED** |
| 15 | "Optional competitive leaderboards drive student engagement and completion rates without any extra work on your end." + tag "Increases completion" (Gamified Leaderboards feature) | `landing.html:827-829` | The leaderboard *feature itself* is real code (`blueprints/exercises.py`, `blueprints/classes.py`, `repositories/exercise_repository.py`, `static/js/student-class.js`). **But** the causal claim — that leaderboards *drive* engagement and *increase* completion — has no supporting data anywhere: no A/B test, no before/after comparison, no fall-semester outcomes study (that study hasn't run yet — this agent's own mission item 2). This is exactly the category `marketing/MESSAGING.md` §6 explicitly bans: *"No fabricated or estimated learning-outcomes statistics — no claimed pass-rate lift, retention lift, or grade improvement, until the fall outcomes study produces real data."* Completion rate is a learning-outcomes statistic; this claim asserts leaderboards cause a lift in it. | Feature: code, verified real. Causal/outcome claim: none found. | **UNSUPPORTED — remove or replace.** New finding — no prior sweep caught it, likely because it's phrased as a feature benefit rather than an obvious statistic. Recommend rewriting to describe the mechanism only (e.g., "Optional competitive leaderboards, if you want them, for classes where that fits your teaching style") and dropping "drive... completion rates" and the "Increases completion" tag entirely until the fall outcomes study can actually measure it. |
| 16 | Comparison table: "LMS grade passback... LTI 1.3 native" | `landing.html:872` | Same evidence as #1/#10. | Code, verified directly. | **SUPPORTED** |
| 17 | Comparison table: "Setup time... Under 60 seconds" | `landing.html:877` | Same evidence gap as #7. | See #7. | **WEAK — needs qualification** (same underlying issue as #7; fix once, fixes both). |
| 18 | Pricing: "SSO integration (OAuth2/OIDC; SAML available on request)" | `landing.html:948` | `blueprints/sso.py:15-16` — module docstring: "SAML 2.0 is intentionally deferred... The provider_type column accepts 'saml' for future use." Only OAuth2/OIDC actually works. This exact wording was the fix applied in `reports/security-engineer/PACKET_CLAIM_GAPS.md` row 17 (closed, commit `e477368`) — re-verified this session by reading the current line, matches. | Code, verified directly this session + cross-referenced closed audit row. | **SUPPORTED** (as currently worded — do not revert to an unqualified "SSO/SAML" claim). |
| 19 | Pricing: "FERPA compliance documentation (provided at contract signing)" | `landing.html:950` | No such document exists yet anywhere in this repo (`find . -iname "*ferpa*"` returns only the FERPA prose already inside `privacy.html`/`terms.html` themselves, per `PACKET_CLAIM_GAPS.md` row 18, re-checked this session). The wording is a forward promise ("provided at... signing"), not a claim that a document exists today — that distinction is exactly what row 18's fix corrected (closed, commit `e477368`). | Cross-referenced closed audit row; re-verified current wording this session. | **SUPPORTED — as a forward commitment.** Operational flag, not a verdict issue: no Institutional-tier deal should close until `legal-compliance` actually produces this document — someone has to be ready to deliver on the promise the moment it's accepted. |
| 20 | Footer: "Built in Boston" | `landing.html:996` | Not independently investigated this session (low stakes, not a product/outcomes/security claim). Consistent with `terms.html:181` ("governed by the laws of the Commonwealth of Massachusetts") and the `.org`/`.com` contact addresses used throughout. | Indirect consistency only, not directly verified. | **SUPPORTED** (low-confidence, low-stakes; flagging the shallow check rather than treating it as fully closed). |

---

## 2. `templates/privacy.html` and `templates/terms.html` — live legal pages

**This section cross-references `reports/security-engineer/PACKET_CLAIM_GAPS.md` rather than
re-deriving its work** — that file already ran a dedicated "live legal/compliance page sweep"
(2026-08-11, rows 15-19) and a "post-commit verification pass" (2026-08-13) confirming which
fixes actually shipped to the live templates. This session re-read the current
`templates/privacy.html` and `templates/terms.html` directly and confirmed the cited line numbers
and wording still match what the audit describes as closed. One new verdict is recorded below
(row 22, encryption at rest) because `PACKET_CLAIM_GAPS.md` deliberately left it unscored
("ambiguous, not a gap") — this file's stricter rule (§"How to use this file" item 2: no evidence
found means UNSUPPORTED) reaches a different, more actionable conclusion.

| # | Claim (verbatim) | Where | Evidence | Evidence strength | Verdict |
|---|---|---|---|---|---|
| 21 | "AI Feature Data:... store your prompts and the AI's responses as part of your persistent chat history... deleted when you delete the conversation or your account. This data is not retained for training..." | `privacy.html:91-94`, `terms.html:151-152` | `repositories/user_repository.py:258-273` (`replace_conversation_messages` — real persistent storage, confirmed by direct code read in `PACKET_CLAIM_GAPS.md` row 15, closed via commit `e477368`). Re-read `privacy.html:91-94` and `terms.html:151-152` this session — wording matches the closed-row description exactly. | Code + cross-referenced closed audit row, re-verified current wording this session. | **SUPPORTED** |
| 22 | "Encryption at rest" | `privacy.html:169` | `reports/security-engineer/PACKET_CLAIM_GAPS.md`'s own "Unverified — evidence needed" section: this is a Supabase/AWS infrastructure property the application code cannot configure or prove; the one Render-dashboard check Adam personally did (2026-08-12, the B7 check) covered `CSP_ENFORCE`/`CORS_ORIGINS`/`FEATURE_CSRF` only, explicitly **not** encryption-at-rest. No later session recorded checking it either. | none found (an infra setting, checkable only via the Supabase project dashboard, never actually checked) | **UNSUPPORTED — remove or replace**, per this file's rule that "not confirmable from the repo" still means "no evidence found" and does not get to default to true. This is almost certainly resolvable in under 5 minutes — the exact same kind of dashboard check that closed the B7 items on 2026-08-12 (Supabase dashboard → Database settings → confirm encryption-at-rest is on, which is the default on most managed-Postgres tiers). Recommend Adam do that check before this line either stays or gets pulled, rather than leaving a live legal document asserting an unconfirmed security control indefinitely. |
| 23 | "We do not currently use a dedicated product-analytics or usage-tracking tool. We use Sentry for error and performance monitoring only..." | `privacy.html:150-153` | Zero-hit grep across the codebase for `posthog\|mixpanel\|amplitude\|segment.com\|hotjar\|fullstory\|gtag\|google-analytics` (per `PACKET_CLAIM_GAPS.md` row 16, closed commit `e477368`). Sentry integration is real and scoped (`core/sentry.py`, `send_default_pii=False`). Sentry itself is disclosed at `privacy.html:113` (row 19, also closed). | Code (negative-grep + positive Sentry confirmation), cross-referenced closed audit rows. | **SUPPORTED** |
| 24 | "AnalytIQ operates from the United States and hosts data on infrastructure located in the United States." / "hosted on infrastructure located in the United States" | `privacy.html:182`, `terms.html:155` | `reports/security-engineer/PACKET_CLAIM_GAPS.md` "Runtime config verification (B7)" — Adam personally read the Render dashboard on 2026-08-12 and recorded hosting region as Virginia (US East). | Adam's direct dashboard read, recorded by a prior agent session, not independently re-checked this session (no Render access from this session). | **SUPPORTED** |
| 25 | "System and audit logs... are retained indefinitely in our database; we do not currently operate an automated log-purge process." | `privacy.html:162-163` | `migrations/006_core_tables.sql:21-30` — `audit_log` has no TTL/expiry column; no purge job found anywhere in the codebase (per `PACKET_CLAIM_GAPS.md` row 9, closed commit `e477368` — the doc was rewritten to state this honestly rather than the prior, false "default Supabase retention periods" claim). | Code (schema + negative grep for purge logic), cross-referenced closed audit row. | **SUPPORTED** |
| 26 | FERPA "school official"/"legitimate educational interest" characterization | `privacy.html:131-137`, `terms.html:138-142` | Standard legal characterization for an EdTech vendor operating under an institution's direction; not contradicted by any code-level finding in `PACKET_CLAIM_GAPS.md`'s sweep. This is a legal conclusion, not an engineering fact — it depends on the actual contractual relationship with Hult, which this agent cannot verify. | Not independently verifiable by this agent; no contradicting evidence found. | **SUPPORTED — with the standing note:** "Requires licensed professional review — this is preparation, not advice" applies to this characterization, as it does to every legal claim in this repo. `legal-compliance` owns final sign-off, not this file. |

**Not re-audited this session** (already closed and unchanged per `PACKET_CLAIM_GAPS.md`'s
"Post-commit verification pass," spot-checked for wording only, not re-derived): rows 1, 6, 10, 17,
18, 19 of that file. **Still open in that file, carried forward here without a new verdict** since
they are `security-engineer`'s scope, not re-derived by this session: CSP "enforced" qualification
(rows 2, B7 section), CSRF token validation (row 1, `docs/security/JWT_CSRF_MITIGATION.md`),
`validate_config()` "fails fast" claims (row 20), stale backup-capability doc claim (row 21) —
none of these appear on `templates/` (the externally-served surface), so they don't get their own
row in this register, but they remain open findings a reader of the compliance packet needs.

---

## 3. `marketing/` — drafts, not yet live

None of these are published (no LinkedIn post has gone out per `PART1_EXECUTION_PLAN.md`'s Aug 24
target being in the future as of this session; the site-copy proposal is unapplied). Rows below
exist so the claims are checked **before** they ship, per this file's stated purpose.

| # | Claim (verbatim) | Where | Evidence | Evidence strength | Verdict |
|---|---|---|---|---|---|
| 27 | "two abstracts I co-authored [with Anusha]... have been accepted to EDULEARN26" | `marketing/LINKEDIN_DRAFTS.md` Post 2 (draft, not posted) | Sole source anywhere in this repo: `.claude/agents/research-academic.md:10` — this agent's own mission brief, which *states* the acceptance as a premise for the papers-drafting task rather than *evidencing* it. Grepped the entire repo for "EDULEARN" (case-insensitive): every hit is either this brief, or another document (marketing/sales drafts) citing this brief in turn — a circular citation chain, not a primary source. No confirmation email, acceptance letter, conference-portal screenshot, or any other artifact exists anywhere in this repo. No prior `reports/research-academic/` session exists either (this is the first). | none found beyond a circular citation to the task brief itself | **WEAK — needs qualification.** This almost certainly reflects something true that Adam told the orchestration process directly (the same pattern as the testimonial-send claims in `reports/sales-outreach/TESTIMONIAL_TRACKER.md`, which are explicitly labeled "Adam's self-report, not independently verified" rather than either confirmed or rejected) — but unlike the testimonial tracker, nothing in this repo labels the EDULEARN26 claim that way; it is stated flatly as fact everywhere it appears. Recommend: (a) Adam confirms this is still accurate as of today, and (b) the actual acceptance artifact (forwarded email, portal screenshot, whatever exists) gets saved into this repo — e.g. `research/EDULEARN26_ACCEPTANCE.md` or a scanned copy — so future citations trace to a primary source instead of to this file's own mission brief. Safe to keep saying "abstracts accepted" in the interim (low risk this is simply false), but flagged rather than silently treated as fully sourced. |
| 28 | "Every professor I've talked to who teaches anything code- or data-adjacent has some version of the same week..." (Post 3, time-savings thesis) | `marketing/LINKEDIN_DRAFTS.md` Post 3 | This is framed as Adam's own observation/reasoning, not a measured claim — it does not assert a statistic, a testimonial, or a specific hours-saved figure. The underlying product mechanism it describes (upload → auto-generated, auto-graded exercises) is the same one evidenced at rows 5, 6, 8, 9 above. | Opinion/reasoning post; underlying mechanism claims already evidenced elsewhere in this table. | **SUPPORTED — as an opinion post, not a factual claim.** No action needed. |
| 29 | Post 1 (Boston AI Summer Bootcamp story) | `marketing/LINKEDIN_DRAFTS.md` Post 1 | **Status: SKELETON, no factual content drafted yet** — every substantive sentence is a bracketed placeholder pending facts only Adam has. Nothing to evidence yet. | N/A — no claim exists yet | **N/A — not evaluated; re-check once Adam fills in real content.** |
| 30 | Post 4 (professor testimonial) | `marketing/LINKEDIN_DRAFTS.md` Post 4 | **Status: BLOCKED**, template only. `reports/sales-outreach/TESTIMONIAL_TRACKER.md` confirms zero testimonials received, zero permissions confirmed, as of 2026-08-13 (last update on file). | N/A — no claim exists yet | **N/A — blocked, correctly not shipped.** Do not post until a named, permissioned quote exists. |
| 31 | `marketing/MESSAGING.md`'s own approved-proof-points and never-say lists (§5, §6) | `marketing/MESSAGING.md` | This is a governance document, not itself a public claim — but its accuracy matters because other agents treat it as authoritative. Spot-checked this session: its citations to `PACKET_CLAIM_GAPS.md`, `CANONICAL_NUMBERS.md`, and `templates/landing.html` line numbers were verified against the current files and found accurate (e.g. §5's LTI-1.3 citation, §6's SAML/FERPA citations). | Governance doc, spot-checked against current source files. | **Reliable as of this session** — safe for other agents to keep citing, with the normal re-check discipline (item 5 above) applied over time. |

---

## 4. `sales/` — drafts, some queued to send imminently

None of these have been confirmed sent as of this session (per `reports/STATE.md` 2026-08-20 §3D.1,
the two ready-to-send follow-ups — Pan, Giansiracusa — were still unsent and one day overdue at
last check; the EF/Hodges email is separately overdue). The original pre-blitz outreach to these
five prospects (referenced in `sales/PIPELINE.csv` as "contacted, original outreach, pre-blitz")
**already went out and its content is not in this repo** — it cannot be audited here; flagged as a
gap, not silently assumed clean.

| # | Claim (verbatim) | Where | Evidence | Evidence strength | Verdict |
|---|---|---|---|---|---|
| 32 | "It's live today at Hult International Business School, integrated with both Canvas and Moodle through LTI 1.3" | `sales/MASTER_TEMPLATE.md`, `sales/FOLLOWUP_SEQUENCE.md`, `sales/SEND_PACKET_2026-08-19.md`, `sales/FOLLOWUPS_2026-08-18.md` (multiple identical occurrences) | Same evidence as row 1/3 above. | Code, verified directly. | **SUPPORTED** |
| 33 | "$2,500 flat... no-questions week-4 refund" (multiple sales documents) | Same files as #32, plus `sales/ORDER_FORM.md`, `sales/STRIPE_INVOICE_TEMPLATE.md` | Same as row 4 above — internally consistent policy commitment across every sales draft. | Cross-referenced, consistent. | **SUPPORTED — as policy**, same attorney-review flag as row 4. |
| 34 | "AnalytIQ's teaching approach has abstracts accepted for presentation at EDULEARN26" | `sales/MASTER_TEMPLATE.md` (optional third proof line), `sales/FOLLOWUP_SEQUENCE.md`, `sales/SEND_PACKET_2026-08-19.md` (5 occurrences), `sales/FOLLOWUPS_2026-08-18.md` | Same evidence gap as row 27 above — same root source. | Same as row 27. | **WEAK — needs qualification.** Same recommendation as row 27: confirm current accuracy and save a primary artifact. These are drafts, not yet sent, so there is time to fix this before it reaches a real recipient. |
| 35 | "going from an uploaded syllabus to a graded, analyzed set of practice exercises takes about a minute" / "~a minute" (demo-speed proof line, several sales documents) | `sales/MASTER_TEMPLATE.md` Version B, `sales/FOLLOWUP_SEQUENCE.md` option 3, `sales/SEND_PACKET_2026-08-19.md` | Same evidence gap as row 7 above — the only measurement on file excludes the Gemini generation step this claim describes. | Same as row 7. | **WEAK — needs qualification.** Same fix as row 7 resolves this too — it is the same underlying claim in looser wording. |
| 36 | "AnalytIQ is already live and being used at Hult — organically, by faculty who found it useful enough to keep using without anyone at EF asking them to." | `sales/EF_HODGES_FORCING_EMAIL.md` (draft body) | The file's own "What this session could and could not verify" section names its **only** source for this sentence: `templates/landing.html:634-636, "100% organic adoption"` — i.e., this draft derived an external-facing claim from row 2's already-unsupported claim, one level removed. No independent evidence of *why* faculty adopted it (organically vs. administratively encouraged vs. any other channel) exists anywhere in this repo. | none found (derived from another unsupported claim) | **UNSUPPORTED — remove or replace.** This is the same underlying defect as B26, surfacing in a second location the original B26 fix does not touch (fixing `landing.html:649` does nothing for this email). This draft is queued for a real, high-stakes external recipient (Stephen Hodges at EF) and is already overdue — recommend fixing this **before** it fixes B26 on the site, if the two can't both happen today, since this one is closer to actually being sent. Recommended replacement: drop "organically... without anyone at EF asking them to" and state only what's evidenced — e.g., "AnalytIQ is already live at Hult, integrated with both Canvas and Moodle via LTI 1.3." The rest of the email's ask (a decision from EF) does not depend on the adoption-motivation framing at all. |
| 37 | "the compliance packet" as an approved proof point | Referenced as an option in `.claude/agents/sales-outreach.md`'s mission brief and `sales/FOLLOW_UP_SEQUENCE.md`'s "Compliance-packet line" note | No customer-ready compliance/security one-pager exists anywhere in this repo — only the internal `reports/security-engineer/PACKET_CLAIM_GAPS.md` audit, which is explicitly marked "never publish or paste into external-facing drafts." Confirmed absent this session (`Glob` for `*PACKET*`/`*compliance*` finds only internal audit files and the legal-compliance agent brief). | none found (no external artifact exists) | **Correctly not in use** — `sales/FOLLOWUP_SEQUENCE.md` already flags this itself and no sales draft actually offers it. No action needed beyond confirming (done here) that no draft has started using it. Flagged so a future session doesn't accidentally start citing "the compliance packet" as if it exists. |

---

## 5. Numbers policy compliance check (this session)

Swept every file touched or read this session for usage figures, per
`ANALYTIQ_AGENT_ORCHESTRATION.md` §8 and the standing numbers ban. **No usage statistic from
`reports/metrics-engineer/CANONICAL_NUMBERS.md` appears in any external-facing draft** —
`templates/landing.html`'s proof bar carries qualitative claims only (rows 1-6 above), and every
`marketing/`/`sales/` draft read this session was already clean per its own internal numbers-ban
checklist (spot-checked, not just trusted). This file itself cites private numbers where relevant
(row 7's discussion of unmeasured generation-time data) — that is expected and permitted per this
file's own PRIVATE marking at the top; the discipline is that those numbers stay in *this* file,
never copy out of it into an external asset.

---

## 6. Gaps in this sweep — what a future session should still check

1. **Original pre-blitz outreach emails** to the five current pipeline prospects are not in this
   repo and were never audited by any agent — they predate the sales-outreach agent's file-based
   drafting. If Adam has copies, they should be checked against this file's verdicts.
2. **`docs/*.md`** (architecture, security, compliance docs) were cross-referenced via
   `PACKET_CLAIM_GAPS.md` but not independently re-swept end-to-end this session — that file itself
   states `docs/CODEBASE_AUDIT_MARCH_2026.md`'s ~900 remaining lines were never fully re-verified.
   These are internal/diligence documents, not live public pages, so they are lower priority for
   *this* register (which is scoped to public claims) but will matter the moment a buyer's
   engineer receives them in a data room.
3. **No compliance packet exists yet** to audit (row 37) — when `legal-compliance` produces one,
   it needs a full pass through this file before it goes to any buyer.
4. **The two EDULEARN26 full papers** (this agent's mission item 1, not done this session — see
   the session report) will themselves need every canonical-metric citation cleared through this
   file and through Adam before submission, per the mission brief's explicit instruction ("clear
   every number with the orchestrator first").
