# Site Copy Proposal — myanalytiq.com — 2026-08

**Prepared:** 2026-08-16
**Corrected:** 2026-08-20 (headless cycle) — §2 rewritten against the live page; see the
correction note at the top of §2 for what changed and why. Everything else in this file is
unchanged from 2026-08-16 and has NOT been re-verified against the live page this session
except where flagged inline below.
**Status:** PROPOSAL ONLY. Not applied to any template. Adam reviews and approves; Adam (or whoever he delegates the actual edit to) pushes it live. Scheduled for his approval Wed Aug 19 per `PART1_EXECUTION_PLAN.md:38` — that date has passed without a recorded approval; still pending.
**Source template used:** `templates/landing.html` (confirmed — this is the only landing page template in `templates/`; `templates/index.html` exists separately and was not the target). Line numbers in §1 and §2 were read on 2026-08-16 and are now approximately **13-14 lines stale** relative to the current file — the page changed between then and now (commit `fdde917` rewrote the proof bar; see §2). Line numbers in §4 onward still land correctly as of a spot-check on 2026-08-20 (Problem section starts at line 717 today, matching this doc's citation). **Do not use §1's line numbers to locate the hero-trust text — use `marketing/B26_LANDING_FIX.md`, which cites the verified current line (649).**
**Positioning source:** `marketing/MESSAGING.md` — read that first. This document applies its priority order (professor time savings → testimonials → student outcomes) to the actual page structure.
**Guardrail carried through every section below:** no usage numbers, no adoption/growth claims, no unsupported "5 hours a week" as a stated fact, no claim without a cited source.
**Evidence gate note:** `research/EVIDENCE.md` — the file `.claude/agents/research-academic.md` item 3 names as the evidence gate for every public claim — **does not exist in this repository as of 2026-08-20** (confirmed by direct search, same finding `marketing/MESSAGING.md` §8.1 already recorded on 2026-08-16). Until it exists, every verifiable-fact claim below still has to cite its source inline, per the same section.

---

## 0. What changes at a glance

| Priority (per MESSAGING.md) | Where it lives today | What changes |
|---|---|---|
| 1. Professor time savings | Hero (currently line 628–695; stale by ~14 lines, see header note) — currently leads with speed ("under 60 seconds"), not time savings | Hero headline and sub rewritten to lead with time savings; speed becomes supporting proof, not the lead. **The hero-trust line (currently line 649) also still carries B26's unevidenced "100% organic adoption" — see `marketing/B26_LANDING_FIX.md` for that fix specifically; it is out of scope for the headline rewrite below and must not be treated as fixed by it.** |
| — | Proof bar (currently lines 697–714) — **[CORRECTED 2026-08-20] no longer shows private usage numbers.** `fdde917` already replaced the four private stat cards with qualitative copy, independently of this document's original recommendation below. See §2 for what's live today and its evidence status. | **Already done — no further action needed on the proof bar itself.** §2 below is corrected to describe the current state instead of a stale "before." |
| 2. Testimonials | **Does not exist as a section today** | New section proposed, inserted after the proof bar. **Gated** — see §3 below, do not ship until a testimonial is in hand |
| 3. Student outcomes | Implicit in Problem (717–748) and Features (790–834) sections | Reframed as explicit "what changes for your students" language, still qualitative, no stats |
| (unchanged) | How It Works (750–788), Compare table (836–883), Pricing (885–969), CTA (971–989), Footer (991–999) | No content changes recommended — already accurate per `PACKET_CLAIM_GAPS.md`'s closed rows (SAML/FERPA wording already corrected 2026-08-12/13). Two small copy nits noted below. |

**Recommended rollout sequencing:** Ship the Hero + Proof Bar + Problem/Features reframing on Aug 19 — all of it is ready now and needs no testimonial. Hold the new Testimonials section until a quote lands, then add it as a fast follow-up deploy (it doesn't require touching anything else on the page).

---

## 1. HERO — `templates/landing.html:614–682` (as read 2026-08-16; **now stale by ~14 lines — the current line for the hero-trust text below is 649, verified 2026-08-20, not 630-ish as this range would imply**)

**[FLAG, 2026-08-20 — not rewritten, cross-referenced instead]** This section's content still
matches the live page (checked directly), but its line numbers drifted after `fdde917` touched
the proof bar below it, and B26 (`reports/STATE.md` §5) tracks the "100% organic adoption" half
of the hero-trust line quoted just below as its own numbered blocker with a dedicated,
Adam-facing fix document. Treat `marketing/B26_LANDING_FIX.md` as authoritative for that
specific line going forward — it verifies the current line number (649), offers two options
instead of this section's single "After," and was written to ship independently of the full
hero rewrite proposed here. This section's own hero-headline rewrite (Option A/B below) still
stands as a separate, broader proposal and has not been re-verified this session beyond the
"Before" quote matching what's live today.

### Before (current live copy)

```html
<div class="hero-eyebrow">The Executable Syllabus</div>
<h1 class="hero-h1">
  Your syllabus.<br>
  <em>Interactive labs.</em><br>
  In under 60 seconds.
</h1>
<p class="hero-sub">
  Upload your course PDF. AnalytIQ generates hands-on coding exercises
  aligned to <em>your</em> content &mdash; not generic curriculum. Students practice
  exactly what you teach.
</p>
...
<div class="hero-trust">
  <div class="trust-dot"></div>
  Live at Hult International Business School &middot; 100% organic adoption
</div>
```

**Problem with this as-is:** leads with speed/product mechanism, not professor time savings (violates priority order #1). "100% organic adoption" is a growth/adoption claim with no traceable source — flag per `MESSAGING.md` §6, remove regardless of which hero copy ships.

### After — Option A (ships today, no testimonial required, RECOMMENDED for Aug 19)

```html
<div class="hero-eyebrow">Built for the professor, not the platform</div>
<h1 class="hero-h1">
  Stop building practice sets<br>by hand.<br>
  <em>Get your week back.</em>
</h1>
<p class="hero-sub">
  Upload your syllabus. AnalytIQ turns it into auto-graded, interactive coding
  exercises aligned to <em>your</em> content in under 60 seconds &mdash; no more
  nights spent writing problem sets or grading them one by one.
</p>
...
<div class="hero-trust">
  <div class="trust-dot"></div>
  Live at Hult International Business School &middot; Canvas + Moodle, LTI 1.3
</div>
```

Evidence for every clause: "auto-graded" → `templates/landing.html:804-806` feature card, verified real (unit-tested grading, `blueprints/exercises.py`). "Under 60 seconds" → approved proof point, already live. "Live at Hult... LTI 1.3" → verified, `PACKET_CLAIM_GAPS.md` "Verified as accurate" section (real AGS grade-passback code). No hours-saved number stated as fact — the whole point of "get your week back" is that it names the *benefit category* without asserting a specific figure.

### After — Option B (stronger, but NOT ready — holds for a testimonial)

```html
<div class="hero-eyebrow">Built for the professor, not the platform</div>
<h1 class="hero-h1">
  Get your <em>5 hours a week</em><br>back.
</h1>
<p class="hero-sub">
  "[Direct quote from a named professor citing hours saved per week]"
  &mdash; [Professor Name], [Title], [Institution]
</p>
```

`[UNSUPPORTED — do not publish]` until a named, permissioned testimonial supplies this number in their own words. Currently zero testimonials in hand (`reports/sales-outreach/TESTIMONIAL_TRACKER.md`). **Do not ship Option B before that quote exists — this is a hard guardrail, not a style preference.**

**Needs Adam:** choose Option A for Aug 19, and revisit Option B the moment a testimonial with an hours-saved estimate lands.

---

## 2. PROOF BAR — `templates/landing.html:697–714` (verified current line numbers, 2026-08-20)

**[CORRECTION, 2026-08-20] This entire section was written against the pre-`fdde917` page and
was stale.** The version below (dated 2026-08-16) described the proof bar as still showing raw
private usage numbers. That is no longer true — `fdde917` already replaced it, independently of
this document, before this session started. Rewritten below to describe **what's actually live
on the page today**, per `reports/STATE.md` §3C.4: "It survived `fdde917` (which stripped only
the numeric proof bar)" — i.e., the proof bar itself was fixed; the still-open problem (B26) is
a *different* line, in the Hero section, not here. See `marketing/B26_LANDING_FIX.md` for that.

### Currently live (read directly from `templates/landing.html:698–714` on 2026-08-20)

```html
<div class="proof-label">Built for your classroom</div>
<div class="proof-stats">
  <div class="proof-claim">Canvas &amp; Moodle ready<span>LTI 1.3</span></div>
  <div class="proof-divider"></div>
  <div class="proof-claim">Refund through week 4<span>No lock-in</span></div>
  <div class="proof-divider"></div>
  <div class="proof-claim">Practice built from your own chapters<span>Upload a PDF</span></div>
</div>
<div class="proof-divider"></div>
<div class="proof-school">
  <div class="school-dot"></div>
  Active at Hult International Business School
</div>
```

### Evidence status of each claim, checked this session

| Claim | Status | Source |
|---|---|---|
| "Canvas & Moodle ready · LTI 1.3" | Evidenced | Real AGS grade-passback code, `blueprints/lti.py:899-941`; `reports/security-engineer/PACKET_CLAIM_GAPS.md` "Verified as accurate"; approved proof point, `marketing/MESSAGING.md` §5 |
| "Refund through week 4 · No lock-in" | Evidenced — this is a real, currently-offered policy, not a usage stat | `sales/ORDER_FORM.md:50-53`, `sales/STRIPE_INVOICE_TEMPLATE.md:45-59`, `sales/MASTER_TEMPLATE.md:37,62` all state the identical no-questions week-4 refund guarantee. Not a claim that needs proving true or false in the evidentiary sense (no metric attached) — it is a commitment Adam has made in every sales draft, so the site copy matches sales terms. **Flag, not a fix:** none of those sales files carry the attorney-review note despite being contract-adjacent language (`sales/STRIPE_INVOICE_TEMPLATE.md:75` does flag "Attorney review of the refund-guarantee language" as still needed) — that review gap is pre-existing and outside this session's scope, noted here only so it isn't lost. |
| "Practice built from your own chapters · Upload a PDF" | Evidenced — product mechanism, not a stat | Matches the real upload → generate flow described in the hero demo card and `docs/DEMO_READINESS.md`; same category as the approved "demo speed" proof point |
| "Active at Hult International Business School" | Evidenced | Same source as the Canvas/Moodle/LTI row above |

**No further action needed on the proof bar itself — it is clean.** This corrects the 2026-08-16
recommendation below, which is now moot as a live-site fix but is kept (not deleted) for the
record, since it correctly diagnosed the *old* violation and its diagnosis stands as history.

### [SUPERSEDED, kept for record] 2026-08-16 "Before / After" recommendation

The original "Before" this document described was:

```html
<div class="proof-label">Live Traction</div>
<div class="proof-stats">
  <div class="proof-stat"><div class="proof-n">33</div><div class="proof-l">Users</div></div>
  <div class="proof-stat"><div class="proof-n">3</div><div class="proof-l">Professors</div></div>
  <div class="proof-stat"><div class="proof-n">2</div><div class="proof-l">Pilot Classes</div></div>
  <div class="proof-stat"><div class="proof-n">$0</div><div class="proof-l">Marketing Spend</div></div>
</div>
...
<div class="proof-school"><div class="school-dot"></div>Active at Hult International Business School</div>
```

That was a live guardrail violation at the time (the exact PRIVATE baseline numbers from
`reports/metrics-engineer/CANONICAL_NUMBERS.md`, shown to every visitor) and the proposed
"After" was:

```html
<div class="proof-label">Where It's Live</div>
<div class="proof-stats">
  <div class="proof-stat-text">Live at Hult International Business School</div>
  <div class="proof-divider"></div>
  <div class="proof-stat-text">Canvas + Moodle &middot; LTI 1.3</div>
  <div class="proof-divider"></div>
  <div class="proof-stat-text">Abstracts accepted &mdash; EDULEARN26</div>
</div>
```

**This is not what shipped.** Whoever implemented `fdde917` wrote different copy (the "Currently
live" block above) that achieves the same guardrail goal (no private numbers) by a different
route. Both are evidenced; the live version is simply what's real now. One thing the original
proposal had that the shipped version lacks: **EDULEARN26 acceptance is not represented anywhere
on the current live page.** That's a legitimate open opportunity, not a violation — flagged to
`marketing/B26_LANDING_FIX.md` as a candidate for the separate B26 hero-line fix, and noted here
as a possible fast-follow addition to this proof bar if Adam wants it back in this row instead.

**Needs Adam:** nothing urgent on the proof bar — it's already compliant. If EDULEARN26
acceptance is wanted on the page at all, decide where (this proof bar, re-adding a 4th
`proof-claim`, vs. the Hero trust line per `marketing/B26_LANDING_FIX.md` Option (b)) rather than
both, to avoid repeating the same proof point twice on one page.

---

## 3. NEW SECTION — Testimonials (does not exist today) — priority #2

**Status: BLOCKED. Do not add this section to the live page until at least one named, permissioned testimonial exists.** Currently zero (`reports/sales-outreach/TESTIMONIAL_TRACKER.md`, last updated 2026-08-13, all three "Reply / Testimonial received / Permission confirmed" columns still blank).

Proposed placement: immediately after the Proof Bar (§2), before the Problem section (§4) — this puts priority #2 physically second on the page, right after the hero/proof-bar carries priority #1.

Proposed markup (for whoever implements once quotes exist):

```html
<section class="section" id="testimonials">
  <div class="section-inner">
    <div class="section-eyebrow">From the Professors Using It</div>
    <h2 class="section-h2">They didn't ask for<br><em>another platform.</em></h2>
    <div class="problem-grid"> <!-- reuse the existing 2-col card grid pattern for a 3-quote layout, or extend to a 3-col grid -->
      <div class="problem-card">
        <div class="pc-body">"[Quote — 2-3 sentences, in the professor's own words, may include their own hours-saved estimate]"</div>
        <div style="margin-top:16px;font-weight:600;">[Professor Name]</div>
        <div style="font-size:13px;color:var(--muted);">[Title], [Institution]</div>
      </div>
      <!-- repeat for quote 2, quote 3 -->
    </div>
  </div>
</section>
```

**Rules for whoever fills this in (per `MESSAGING.md` §6):** name + title only with explicit confirmed permission. No usage numbers, even if the professor volunteers one in casual conversation — only what's in the permissioned quote text itself. If a professor's quote includes an hours-saved estimate, that becomes the evidence source for Option B in §1 above — flag it back to this file and to `MESSAGING.md`.

**Needs Adam:** nothing yet — this section has no action for Adam until a testimonial exists. Tracked as blocked in the session report below.

---

## 4. PROBLEM SECTION — `templates/landing.html:717–748` — reinforces positioning line

### Before

```html
<div class="section-eyebrow">The Problem</div>
<h2 class="section-h2">Generic platforms teach<br><em>their</em> content. Not yours.</h2>
<p class="section-lead">
  Datacamp, Coursera, and every platform like them were built for mass-market learners.
  They have no idea what you taught in Week 4, which datasets you used, or how you
  explained regression. Students are left to bridge the gap on their own.
</p>
```

The "AnalytIQ" card in this section already says "The Alignment Layer" as its tag (`:739`) — this is good, it already echoes the canonical positioning line. Recommend making the connection explicit rather than implicit.

### After (minor edit — add the canonical line verbatim)

```html
<div class="section-eyebrow">The Problem</div>
<h2 class="section-h2">Generic platforms teach<br><em>their</em> content. Not yours.</h2>
<p class="section-lead">
  Datacamp, Coursera, and every platform like them were built for mass-market learners.
  They have no idea what you taught in Week 4, which datasets you used, or how you
  explained regression. Students are left to bridge the gap on their own &mdash;
  and professors are left doing double work: teaching the course, then rebuilding
  practice material for a platform that doesn't know what they taught.
</p>
```

And in the highlighted "AnalytIQ" card (`:737-746`), keep "The Alignment Layer" tag as-is and add one sentence that states the canonical line directly:

```html
<div class="pc-body" style="color:rgba(255,255,255,0.6)">
  AnalytIQ is the alignment layer between your syllabus and student practice.
  Exercises generated from <em>your</em> syllabus, locked to your pedagogy.
  Students practice exactly the logic, syntax, and datasets you introduced in class.
  The AI tutor answers questions using your course material as its only context.
</div>
```

This is a one-sentence insert, low-risk, reinforces `MESSAGING.md` §1 without changing the section's structure or claims (everything else in this card is already accurate, unchanged).

---

## 5. FEATURES SECTION — `templates/landing.html:790–834` — priority #3 (student outcomes), reframed qualitatively

No structural change recommended — the six feature cards are accurate (verified: sandboxed execution, automated grading, AI tutor, dashboard, LTI 1.3, leaderboards all match real code per `PACKET_CLAIM_GAPS.md`'s "Verified as accurate" notes). The change is in framing: this section is where "student outcomes" (priority #3) lives today, and the copy should describe *what changes for the student*, not just list features.

### Before (Automated Grading card, `:802-807` — representative example)

```html
<div class="feat-h">Automated Grading</div>
<div class="feat-p">Output-based unit testing grades student work on actual results, not string matching. Catches copying, rewards real understanding.</div>
```

### After (same card, outcome-framed, still evidence-based — no stats added)

```html
<div class="feat-h">Automated Grading</div>
<div class="feat-p">Students get a real grade the moment they submit &mdash; not a week later. Output-based unit testing checks actual results, not string matching, so partial credit and real understanding are both caught correctly.</div>
```

Apply the same treatment (student-facing outcome sentence first, mechanism second) to the "Context-Locked AI Tutor" and "Student Analytics Dashboard" cards — both already describe real, verified behavior; only the framing order changes, no new claims added.

**No numeric outcome claim (pass rates, retention, grade improvement) is added anywhere in this section** — none exist yet (`research-academic`'s fall outcomes study hasn't run). This section stays feature/mechanism description, framed toward the student's experience, which is the honest ceiling of what "student outcomes" content can say until real study data exists.

---

## 6. Sections with no recommended content change

These were checked against `PACKET_CLAIM_GAPS.md`'s closed rows and found already correct — no action needed:

- **How It Works** (`:750–788`) — accurate, matches real product flow (upload → generate → students practice + professor dashboard). No time-savings-specific language to add without a number to cite; leaving as-is.
- **Comparison table** (`:836–883`) — accurate, verified line-by-line against real code in earlier security passes (LTI 1.3, grade passback, alignment claims all real).
- **Pricing** (`:885–969`) — already corrected 2026-08-12/13 per `PACKET_CLAIM_GAPS.md` rows 17–18: SAML now reads "SSO integration (OAuth2/OIDC; SAML available on request)" (`:949`) and FERPA now reads "FERPA compliance documentation (provided at contract signing)" (`:951`). Both are accurate as currently written — do not revert.
- **CTA** (`:971–989`) and **Footer** (`:991–999`) — no claims requiring evidence review.

---

## 7. Summary of what Adam is being asked to approve on Aug 19

1. **[CORRECTED 2026-08-20 — no longer urgent, already resolved]** ~~remove the four private usage-number stat cards from the proof bar (§2)~~. This shipped independently in `fdde917` before this session. **The actual live urgent item now is B26** — `templates/landing.html:649`'s "100% organic adoption" in the Hero trust line, a different line from the one this item originally described. See `marketing/B26_LANDING_FIX.md` for the ready-to-apply diff (two options) — that is the item that should ship as soon as possible, not this one.
2. **Hero rewrite** — Option A (§1), ships now with no number claim; Option B held for later once a testimonial supplies "5 hours a week" or a similar figure in their own words. **Flag:** §1's proposed Option A hero-trust text ("Live at Hult International Business School · Canvas + Moodle, LTI 1.3") would now be redundant with the live proof bar (§2 below already carries "Canvas & Moodle ready · LTI 1.3" independently) — if Adam approves the full hero rewrite, reconcile the trust-line wording with whichever B26 option (`marketing/B26_LANDING_FIX.md`) he picks, rather than shipping both.
3. **[CORRECTED 2026-08-20 — already live, not a pending action]** ~~Proof bar replacement copy (§2) — three qualitative proof points, no numbers~~. The live proof bar already has three qualitative proof points, no numbers (§2). Nothing to approve here.
4. **One-sentence positioning insert** in the Problem section (§4) — low-risk, adds the canonical line verbatim. Not re-verified against the live page this session (§4's content matched what I read on 2026-08-20, so it remains a live, unshipped proposal).
5. **Feature-card copy reframing** (§5) — outcome-first sentence ordering, same underlying claims, no new stats. The "Before" quote in §5 was re-read directly against the live file this session (`templates/landing.html:804`) and matches word for word; still an unshipped proposal.
6. **Testimonials section** (§3) — approved in principle, but **blocked from shipping** until a named quote exists. Not part of the Aug 19 deploy. Still zero testimonials in hand as of this session (no new evidence checked; `reports/sales-outreach/TESTIMONIAL_TRACKER.md` was not re-read this session — flagged, not silently assumed unchanged).

Nothing above requires a new claim that lacks a cited source. Everything in §6 (How It Works, Compare, Pricing, CTA, Footer) is recommended unchanged; Pricing's SAML/FERPA wording was spot-checked against the live file this session (`templates/landing.html:948,950`) and still matches.
