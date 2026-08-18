PRIVATE — internal drafting file. DRAFT ONLY. Adam personalizes and presses send on every individual email; nothing here is sent automatically.

# Follow-Up Sequence — Professor Outreach

**Prepared:** 2026-08-16, by sales-outreach agent.
**Applies to:** every prospect in `sales/PIPELINE.csv` who received the initial email (`sales/MASTER_TEMPLATE.md`) and has not replied.
**Cadence:** Follow-up #1 on day 4 after the initial send, Follow-up #2 on day 9, break-up note on day 16. Dates are relative to each prospect's own send date — track per-row in `sales/PIPELINE.csv`'s `next_date` column, not a single calendar date for the whole batch.
**Hard constraint honored:** no usage numbers anywhere below. Approved external proof points only: testimonials, "live at Hult on Canvas + Moodle LTI 1.3," demo speed, the compliance packet, EDULEARN26 acceptances.

---

## Follow-up #1 — day 4

Short. Reply in the same thread as the initial email (don't start a new one). No new proof point yet — this is a bump, not a re-pitch.

**Subject:** `Re: {{original subject line}}`

**Body:**

> {{Name}} — following up in case this got buried. Still happy to show you the {{COURSE_NAME}} fit in 15 minutes, whenever works.
>
> If now's not a good time this semester, no worries at all — just say the word and I'll check back later in the term instead of this thread.
>
> Best,
> Adam

**Notes for Adam:**
- Keep it under 4 sentences. The point of day 4 is visibility, not persuasion.
- If they replied with anything other than a flat no, this prospect moves to "call booked" or "in conversation" in `sales/PIPELINE.csv`'s `status` column — do not send follow-up #2 to anyone who has responded.

---

## Follow-up #2 — day 9 (adds a new proof point)

This one earns its send by adding something the first two emails didn't say. Do not just repeat the original pitch with more urgency — that reads as pressure, not new information.

**Subject:** `One more thing on {{COURSE_NAME}}`

**Body:**

> {{Name}} — one thing I didn't mention last time: {{NEW PROOF POINT — pick exactly one, see options below}}.
>
> Still open if you want to see it live — 15 minutes, whenever works for you. And if the timing's just not right this semester, tell me and I'll stop following up.
>
> Best,
> Adam

**New-proof-point options (pick one per prospect, do not stack multiple):**

1. **If a real testimonial quote is in hand by day 9:** `"[2-3 sentence quote]" — [Name], [Title], [School]` — the single strongest option once available. Source: `reports/sales-outreach/TESTIMONIAL_TRACKER.md`.
2. **If no testimonial yet:** `AnalytIQ's teaching approach has abstracts accepted for presentation at EDULEARN26` (generic phrasing only — see caveat in `sales/MASTER_TEMPLATE.md`'s "Optional third proof line" section; do not add paper count or topic detail, none is verified in this repo).
3. **Alternative if EDULEARN26 was already used in the original send to this prospect:** demo-speed framing — `going from an uploaded syllabus to graded, analyzed practice exercises takes about a minute in a live demo, if that's useful context for how fast this would be to actually try`.

**Do not use as a "new" proof point in this slot** (already spent in the original email, per `sales/MASTER_TEMPLATE.md`): "live at Hult on Canvas + Moodle LTI 1.3," the $2,500 offer, or the week-4 refund guarantee — those were already stated in the initial send and repeating them isn't new information.

**Compliance-packet line — flagged, not included by default:** the mission's approved-proof-points list includes "the compliance packet" as an option. As of 2026-08-16 no customer-ready compliance/security one-pager exists in this repo — only an internal claim-vs-reality audit (`reports/security-engineer/PACKET_CLAIM_GAPS.md`), which is explicitly marked "never publish or paste into external-facing drafts" and is not itself the packet. **Do not offer "a compliance packet" in any outreach email until `legal-compliance` produces an actual external-facing document and Adam confirms it's ready to send.** Needs Adam decision — see session report.

---

## Break-up note — day 16

Genuinely permission-based, not a guilt trip. The goal is a clean close that leaves the door open, not a last hard sell.

**Subject:** `Re: {{original subject line}}` (same thread)

**Body:**

> {{Name}} — I'll stop following up after this one. If the timing's not right this semester, totally understand — teaching schedules don't leave a lot of room in August.
>
> If it's useful later (spring semester, or mid-year if something changes), just reply anytime and I'll pick this back up — no need to re-explain anything.
>
> Either way, thanks for reading this far.
>
> Adam

**Notes for Adam:**
- No new proof point here — the break-up note's job is a graceful exit, not one more pitch.
- On send, update `sales/PIPELINE.csv`: `status` → `"no response, sequence complete"`, `next_action` → `"revisit spring semester (January window) per PART1_EXECUTION_PLAN.md rolling task"`, `next_date` → a January placeholder.
- If this prospect ever replies after the break-up note, treat it as a fresh inbound lead — skip straight to booking the 15-minute call, don't restart the sequence.

---

## Sequence-wide rules

1. Every send in this sequence is a **reply in the original thread**, not a new email — subject lines above are written as `Re:` for that reason.
2. Stop the sequence immediately on any reply (positive, negative, or a redirect to someone else) — log it in `sales/PIPELINE.csv` and move to the appropriate next action, don't mechanically continue to the next scheduled day.
3. No usage numbers, no acqui-hire language, no walk-away number in any of the above — verified clean against `reports/metrics-engineer/CANONICAL_NUMBERS.md` policy before this file was written.
4. Adam presses send on every message in this sequence. No agent sends anything.
