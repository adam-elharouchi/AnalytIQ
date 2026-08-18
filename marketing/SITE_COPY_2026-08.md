# Site Copy Proposal — myanalytiq.com — 2026-08

**Prepared:** 2026-08-16
**Status:** PROPOSAL ONLY. Not applied to any template. Adam reviews and approves; Adam (or whoever he delegates the actual edit to) pushes it live. Scheduled for his approval Wed Aug 19 per `PART1_EXECUTION_PLAN.md:38`.
**Source template used:** `templates/landing.html` (confirmed — this is the only landing page template in `templates/`; `templates/index.html` exists separately and was not the target). All line numbers below refer to `templates/landing.html` as read on 2026-08-16.
**Positioning source:** `marketing/MESSAGING.md` — read that first. This document applies its priority order (professor time savings → testimonials → student outcomes) to the actual page structure.
**Guardrail carried through every section below:** no usage numbers, no adoption/growth claims, no unsupported "5 hours a week" as a stated fact, no claim without a cited source.

---

## 0. What changes at a glance

| Priority (per MESSAGING.md) | Where it lives today | What changes |
|---|---|---|
| 1. Professor time savings | Hero (lines 618–638) — currently leads with speed ("under 60 seconds"), not time savings | Hero headline and sub rewritten to lead with time savings; speed becomes supporting proof, not the lead |
| — | Proof bar (lines 685–715) — currently shows **private usage numbers** | **Numbers removed entirely** (hard guardrail violation as-is). Replaced with the three approved proof points |
| 2. Testimonials | **Does not exist as a section today** | New section proposed, inserted after the proof bar. **Gated** — see §3 below, do not ship until a testimonial is in hand |
| 3. Student outcomes | Implicit in Problem (717–748) and Features (790–834) sections | Reframed as explicit "what changes for your students" language, still qualitative, no stats |
| (unchanged) | How It Works (750–788), Compare table (836–883), Pricing (885–969), CTA (971–989), Footer (991–999) | No content changes recommended — already accurate per `PACKET_CLAIM_GAPS.md`'s closed rows (SAML/FERPA wording already corrected 2026-08-12/13). Two small copy nits noted below. |

**Recommended rollout sequencing:** Ship the Hero + Proof Bar + Problem/Features reframing on Aug 19 — all of it is ready now and needs no testimonial. Hold the new Testimonials section until a quote lands, then add it as a fast follow-up deploy (it doesn't require touching anything else on the page).

---

## 1. HERO — `templates/landing.html:614–682`

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

## 2. PROOF BAR — `templates/landing.html:684–715`

### Before (current live copy — contains PRIVATE data, must not stay live)

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

**This is a live guardrail violation today** — these are the exact PRIVATE baseline numbers from `reports/metrics-engineer/CANONICAL_NUMBERS.md` (33 ≈ related to the 31/40 user-count issue documented there), shown to every site visitor. This should be corrected regardless of anything else in this document, independent of the Aug 19 timeline — flagging it here as the most urgent single fix in this whole proposal.

### After

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

(`.proof-n`/`.proof-l` styling swapped for a simpler text treatment since these are no longer numbers — a developer implementing this should reuse `.proof-school`'s text styling for the three items rather than the big-serif-number `.proof-n` style, which was built for digits.)

Every clause sourced: Hult live + LTI 1.3 (verified, see §1). EDULEARN26 abstracts accepted (`.claude/agents/research-academic.md:10` — "the accepted abstracts"; full papers targeted Nov 15, not yet drafted, so say "abstracts accepted," not "papers published").

**Needs Adam:** confirm removal of the four private-number stat cells. This is the one change in this document that should not wait for the Aug 19 window if it can ship sooner — it's an active guardrail breach on the live site today.

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

1. **Urgent, independent of Aug 19 timing:** remove the four private usage-number stat cards from the proof bar (§2). Recommend this ships as soon as possible rather than waiting.
2. **Hero rewrite** — Option A (§1), ships now with no number claim; Option B held for later once a testimonial supplies "5 hours a week" or a similar figure in their own words.
3. **Proof bar replacement copy** (§2) — three qualitative proof points, no numbers.
4. **One-sentence positioning insert** in the Problem section (§4) — low-risk, adds the canonical line verbatim.
5. **Feature-card copy reframing** (§5) — outcome-first sentence ordering, same underlying claims, no new stats.
6. **Testimonials section** (§3) — approved in principle, but **blocked from shipping** until a named quote exists. Not part of the Aug 19 deploy.

Nothing above requires a new claim that lacks a cited source. Everything in §6 (How It Works, Compare, Pricing, CTA, Footer) is recommended unchanged.
