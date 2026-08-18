PRIVATE — internal drafting file. DRAFT ONLY. Adam personalizes and presses send on every individual email; nothing here is sent automatically.

# Master First-Touch Email Template — Professor Outreach

**Prepared:** 2026-08-16, by sales-outreach agent.
**Structure required (`PART1_EXECUTION_PLAN.md:34`):** subject leads with professor time savings → one line on what it is → testimonial quote → "live at Hult on Canvas + Moodle LTI 1.3" proof line → $2,500/section with week-4 refund guarantee → ask for 15 minutes.
**For Adam's review/approval:** Aug 17, per `PART1_EXECUTION_PLAN.md:34`.
**Hard constraint honored:** no usage numbers of any kind anywhere in this file. Approved external proof points only: testimonials, "live at Hult on Canvas + Moodle LTI 1.3," demo speed, the compliance packet, EDULEARN26 acceptances.

---

## READ THIS FIRST — this template cannot ship as-is Monday

**The testimonial quote slot below is empty.** Three testimonial-request emails went out from the AnalytIQ address on 2026-08-12 (Hult Professor A, Hult Professor B, Anusha — `reports/sales-outreach/TESTIMONIAL_REQUESTS.md`). As of today (2026-08-16), **no reply has been confirmed** — `reports/sales-outreach/TESTIMONIAL_TRACKER.md` shows the reply/testimonial-received/permission-confirmed columns still blank, and no agent can see that mailbox (forwarding was declined). Adam has to check the AnalytIQ inbox himself and report back.

**Do not send Version A (below) with the bracket still in it.** If Monday arrives and no quote is in hand, use **Version B — the no-quote fallback** further down. It is fully compliant with the approved-proof-points list and needs no testimonial to go out. Swap in Version A the moment a real, named, permissioned quote exists.

---

## Version A — with testimonial (use only once a real quote replaces the bracket)

**Subject (pick one — leads with time, not features):**
- Option 1: `Get grading time back for {{COURSE_NAME}} this semester`
- Option 2: `A faster way to grade {{COURSE_NAME}} — 15 minutes?`
- Option 3: `Cutting your {{COURSE_NAME}} grading load this term`

**Body:**

> {{FIRST LINE — personalized to their actual course. Reference something real: an assignment type in the syllabus, a specific topic, a tool they use, a term they teach. Generic openers ("I hope this finds you well") are a failed deliverable — see sales/PIPELINE.csv personalization_hook column for the researched hook per prospect.}}
>
> AnalytIQ turns a professor's own course materials — slides, readings, a syllabus PDF — into auto-graded practice exercises for students, with a dashboard that shows you exactly where the class is struggling before the exam does.
>
> **[TESTIMONIAL QUOTE — PLACEHOLDER, DO NOT SEND WITH THIS BRACKET STILL HERE.** Replace with a real, named quote once permission is confirmed: `"[2-3 sentence quote]"` — [Name], [Title], [School]. Source: `reports/sales-outreach/TESTIMONIAL_TRACKER.md` once filled in.]
>
> It's live today at Hult International Business School, integrated with both Canvas and Moodle through LTI 1.3 — so it drops into the course tools your students already use, no new login for anyone.
>
> A full class license for one section, one semester, is $2,500 flat — and it comes with a no-questions week-4 refund: if it isn't measurably saving you time by week 4, tell me and I'll refund it in full, no argument.
>
> Worth 15 minutes on a call? I can show you the whole loop — upload to graded exercises — live, and you can judge for yourself whether it's a fit for {{COURSE_NAME}}.
>
> Best,
> Adam El Harouchi
> {{contact info}}

---

## Version B — no-quote fallback (use this if Monday arrives with no confirmed testimonial)

Same structure, same offer, same guarantee — the testimonial line is replaced with a second, already-true proof line instead of removed outright, so the email still has social proof of a kind, just not a named quote.

**Subject (same three options as above apply):**
- `Get grading time back for {{COURSE_NAME}} this semester`

**Body:**

> {{FIRST LINE — personalized to their actual course, same rule as Version A.}}
>
> AnalytIQ turns a professor's own course materials — slides, readings, a syllabus PDF — into auto-graded practice exercises for students, with a dashboard that shows you exactly where the class is struggling before the exam does.
>
> It's live today at Hult International Business School, integrated with both Canvas and Moodle through LTI 1.3 — no new login, it sits inside the tools your students already use. In a live demo, going from an uploaded syllabus to a graded, analyzed set of practice exercises takes about a minute, not a semester of setup.
>
> A full class license for one section, one semester, is $2,500 flat — with a no-questions week-4 refund: if it isn't measurably saving you time by week 4, tell me and I'll refund it in full, no argument.
>
> Worth 15 minutes on a call? I'll show you the whole loop live and you can judge the fit for {{COURSE_NAME}} yourself.
>
> Best,
> Adam El Harouchi
> {{contact info}}

**Optional third proof line for Version B**, if Adam wants to layer in one more point beyond demo speed (use at most one extra — don't stack all of them, it reads as padding): "AnalytIQ's approach has abstracts accepted for presentation at EDULEARN26" (source: `.claude/agents/research-academic.md` mission brief — accepted abstracts are the stated premise there; no paper count or subject-matter detail is verified in this repo, so keep the sentence exactly this generic, do not add specifics).

---

## What every send must still do (not automated by this template)

1. Fill `{{FIRST LINE}}` and `{{COURSE_NAME}}` with something **real and specific** from `sales/PIPELINE.csv`'s `personalization_hook` column for that prospect. A template with the brackets still showing is not a draft, it's an error.
2. Fill `{{contact info}}` with however Adam wants to sign off (email, phone, Calendly link if one exists — none is set up in this repo as of today).
3. Log the send (date, version used, subject line) in `sales/PIPELINE.csv`'s `status`/`next_action`/`next_date` columns same day, per the mission's tracking requirement.
4. Adam presses send. No agent sends this or any version of it.
