# B26 Landing Fix — remove the unevidenced adoption claim at `landing.html:649`

**Prepared:** 2026-08-20 (headless cycle)
**Status:** PROPOSAL ONLY. Not applied to any file. Adam approves and pushes to `main` — this
targets `origin/main`, which is what Render deploys, per Global Rules ("No production
deployment without Adam's explicit per-change approval").
**Blocker this closes:** B26 (`reports/STATE.md` §3C.4 / §5) — "100% organic adoption" is an
unevidenced adoption claim, live on the page Adam is about to point 38 professors at.
**Confirmed by direct read, not inherited:** I read `templates/landing.html:600-750` in the
current working tree myself on 2026-08-20. Line 649 reads exactly what `reports/STATE.md`
recorded for `origin/main` on 2026-08-19. I do not have a `git diff` tool in this session to
independently prove the working tree equals `origin/main` byte-for-byte — noted as a limitation
in the session report — but the string and line number match STATE.md's `origin/main` citation
exactly, so I am confident this is the live text, not a stale local copy.

---

## The problem, precisely

`templates/landing.html:649` currently reads (10-space indent preserved, verbatim):

```
          Live at Hult International Business School &middot; 100% organic adoption
```

**"Live at Hult International Business School"** is evidenced — Hult runs AnalytIQ on Canvas
and Moodle via LTI 1.3, substantiated by real AGS grade-passback code (`blueprints/lti.py:899-941`,
per `reports/security-engineer/PACKET_CLAIM_GAPS.md` "Verified as accurate" section, and
restated as an approved proof point in `marketing/MESSAGING.md` §5). Keep this half.

**"100% organic adoption"** has no traceable source anywhere in this repo. It is not in
`reports/metrics-engineer/CANONICAL_NUMBERS.md`, not in `marketing/MESSAGING.md`'s approved
proof-point list, and `research/EVIDENCE.md` — the file that is supposed to be the evidence
gate for every public claim — **does not exist in this repository** (confirmed by direct
search; `.claude/agents/research-academic.md` item 3 tasks the `research-academic` agent with
creating it, and it has not been created as of this session). `marketing/MESSAGING.md` §6
already lists "100% organic adoption" on the never-say list. This is a straight guardrail
violation, not a judgment call.

---

## The diff — two options for the second half

### Option (a) — delete it, keep the Hult line alone

```diff
--- a/templates/landing.html
+++ b/templates/landing.html
@@ -649 +649 @@
-          Live at Hult International Business School &middot; 100% organic adoption
+          Live at Hult International Business School
```

Nothing added needs a citation — it's a pure subtraction. Zero new risk.

### Option (b) — replace the second half with an evidenced claim

The only approved proof point that is (1) evidenced and (2) not already stated elsewhere on
this exact page is **EDULEARN26 abstract acceptance** (`.claude/agents/research-academic.md:10`,
cross-cited in `marketing/MESSAGING.md` §5 — "Two abstracts accepted; full papers targeted for
Nov 15"). `EDULEARN` does not currently appear anywhere else in `landing.html` (checked by
direct grep of the file), so this would not be redundant with existing copy.

```diff
--- a/templates/landing.html
+++ b/templates/landing.html
@@ -649 +649 @@
-          Live at Hult International Business School &middot; 100% organic adoption
+          Live at Hult International Business School &middot; Abstracts accepted, EDULEARN26
```

Wording constraint per `MESSAGING.md` §5/§6: say "abstracts accepted," never "published" or
"peer-reviewed" — nothing has been presented and the full papers haven't cleared review.

**Two other candidates for (b) were considered and rejected as not worth having:**
- *"Canvas + Moodle, LTI 1.3"* — evidenced, but **already stated at `templates/landing.html:702`**
  in the live proof bar just below ("Canvas &amp; Moodle ready&nbsp;LTI 1.3"). Adding it
  here too is pure redundancy, not new proof. (This was `marketing/SITE_COPY_2026-08.md`'s
  original Aug 16 suggestion for this exact line — see the correction note in that file below;
  it predates the proof bar being independently rewritten, so it's now stale, not wrong.)
- *"Demo speed / under 60 seconds"* — evidenced, but **already the entire hero headline** three
  lines above this trust line ("...In under 60 seconds."). Same redundancy problem.
- *The compliance packet* — `marketing/MESSAGING.md` §5 states explicitly this is "**Not usable
  yet**" (CSP is Report-Only, CSRF tokens aren't validated, encryption-at-rest unverified). Ruled
  out on evidence grounds, not style.
- *A named testimonial* — zero in hand (`reports/sales-outreach/TESTIMONIAL_TRACKER.md`). Ruled
  out — nothing exists to quote.

---

## Recommendation

**Recommend Option (a).** One sentence: a single-glance hero trust line should carry one clean
proof point, "Live at Hult International Business School" already is the strongest one on the
page by itself, and the only non-redundant evidenced alternative (EDULEARN26 acceptance) mixes
a customer-adoption signal with an academic-credibility signal in one breath — a category
mismatch that reads as padding rather than proof, and EDULEARN26 acceptance deserves its own
slot (see the proof-bar correction in `marketing/SITE_COPY_2026-08.md` §2, updated this session)
rather than being squeezed in here to patch a deletion.

If Adam prefers a fuller-looking trust line, Option (b) is ready to apply as-is and is fully
evidenced — it is not a fallback of last resort, just not my first choice.

---

## What I did NOT do

I did not edit `templates/landing.html`. Per Global Rules, Adam approves site changes and
pushes to `main`; this file is the ready-to-apply diff for his decision, nothing more.
