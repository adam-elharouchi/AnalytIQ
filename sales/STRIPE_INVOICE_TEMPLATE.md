PRIVATE — internal drafting file. TEXT ONLY.

# Stripe Invoice Template — $2,500 Single-Class License

**DRAFT — requires attorney review before first signature.** `legal-compliance` owns the customer
agreement itself (the contract terms a customer signs); this file is invoice **text** only — the
line items and language Adam would type into Stripe's invoicing UI by hand.

**This agent never touches payment configuration or credentials.** No Stripe account, API key,
webhook, product ID, or price ID is created, read, or referenced here. Nothing below is wired to
Stripe in any way — it is copy for Adam to paste into an invoice he creates himself, once the
Stripe account is live (`PART1_EXECUTION_PLAN.md:45`: "Sept 1: Stripe account live; invoice
template tested with a $1 self-test").

**Terms sourced from what outreach actually promises** — checked against
`sales/MASTER_TEMPLATE.md` and every email in `sales/SEND_PACKET_2026-08-19.md`: $2,500 flat per
section, per semester, single class license, no-questions week-4 refund. Nothing below invents a
term the outreach hasn't already stated to the customer.

---

## Invoice line item

**Description:**
```
AnalytIQ — Single-Class License, One Section, One Semester
```

**Quantity:** 1
**Unit price:** $2,500.00
**Amount:** $2,500.00

**Optional longer description** (if Stripe's line-item description field allows more detail —
use this instead of the short version above when there's room):
```
AnalytIQ class license: auto-graded practice exercises generated from the professor's own course
materials, one section, one semester. Includes LMS integration (Canvas or Moodle via LTI 1.3),
professor dashboard, and student access for the enrolled section. Covered by the week-4 refund
guarantee described below.
```

## Invoice memo / footer text

```
Refund guarantee: if AnalytIQ is not measurably saving you time by the end of week 4 of the
semester, contact adamelharouchi@myanalytiq.org and this invoice will be refunded in full — no
argument, no conditions beyond the week-4 timing.

Questions about this invoice: adamelharouchi@myanalytiq.org
```

## Payment terms (for the Stripe invoice settings, plain text — not a config value)

- **Amount:** $2,500.00 USD, one-time (not a subscription for the first sale — a single-class,
  single-semester license, matching the offer as pitched).
- **Due:** on receipt, or net 15 — Adam's call at send time; not stated as a fixed term in any
  outreach email, so nothing here binds him to one.
- **Refund window:** through the end of week 4 of the semester the license covers. This is a
  guarantee stated in the sales copy, not a Stripe-native "refund policy" field — attorney review
  should confirm whether it needs to be restated in the customer agreement itself (that document
  is `legal-compliance`'s to draft, not this one).

## What this file deliberately does not contain

- No Stripe product ID, price ID, API key, webhook secret, or account identifier.
- No tax handling, no multi-seat / department-license pricing (out of scope — the offer on the
  table is one section, one semester, $2,500 flat; a department-wide license is a distinct
  conversation per `sales/PIPELINE.csv`'s secondary-audience note in `marketing/MESSAGING.md` §3).
- No usage numbers, testimonial claims, or any other external proof point — an invoice is a
  billing document, not a sales asset, and should not carry marketing language beyond the one
  memo line above.

## Before this is usable

1. Attorney review of the refund-guarantee language and whether it needs to also appear, in
   binding form, in `legal-compliance`'s customer agreement.
2. Stripe account live and tested with a $1 self-test (`PART1_EXECUTION_PLAN.md:45`) — Adam's
   task, not this agent's.
3. Confirm the due-on-receipt vs. net-15 choice before the first real invoice goes out.
