# B27 — Backup Schedule: the Wait-for-Host Fix, What It Doesn't Fix, and the Open Scheduling Question

**Status:** Fix shipped to `scripts/backup_db.sh`, unproven against a live wake event.
**Owner:** Security Engineering. **Date:** 2026-08-20.
**Audience:** Adam. Decision needed on §3.

## 1. What changed in `scripts/backup_db.sh`

Two independent, bounded fixes — neither is an unbounded loop:

**(a) `wait_for_host()` gate before `pg_dump` starts.** Ports the exact pattern
commit `7c299d2` added as `wait_for_smtp()` on the failure-notice path in
`daily_cycle.sh`: poll a TCP connect to `PGHOST:PGPORT` via `python3 socket`,
15s between polls, 300s hard timeout, then fail loudly rather than let a
generic `pg_dump` connection error stand in the log. This needed porting
independently because `backup_db.sh` is a separate script on a separate
launchd job (`com.analytiq.dbbackup`, not `com.analytiq.dailycycle`) — fixing
the notice path in `daily_cycle.sh` touches zero lines of `backup_db.sh`.

**(b) Bounded retry (3 attempts) around the `pg_dump | openssl` pipe itself.**
Each attempt writes to a private temp file (`.tmp-<stamp>.dump.enc`) that is
`mv`'d to the real output name only after that attempt fully succeeds and
passes the existing size sanity check — a killed or partial attempt can never
be mistaken for a finished backup. On final exhaustion, the failure message
re-checks reachability once more so the log states outright whether the host
is up right now (→ "connection dropping mid-dump, not a wake race") or down
(→ "likely a real outage"). This half of the fix was **not** in my original
brief — added after re-reading the actual log; see §2.

Both fixes preserve the success path: a normal run still dumps once, encrypts
once, logs `wrote <size>`, verifies, and sweeps exactly as before. Credential
handling at `:247`/`:251` (`export DATABASE_URL`, read via `os.environ`) is
untouched, per instruction — no credential is read, echoed, or logged by
either new code path.

## 2. Correcting the record — this is not one failure mode, it's two

`reports/STATE.md` §3C.5 describes all known scheduled failures as "racing
the network on wake." Having now read `~/AnalytIQ-backups/backup.log`
directly, that is accurate for only half of them, and the failure count is
four, not three:

| Fire time | Error (verbatim from backup.log) | What it means |
|---|---|---|
| Aug 16 17:31 | `Connection refused` (all 3 pooler IPs) | Never connected — wake race, host not up yet |
| Aug 17 17:34 | `could not translate host name ... Name does not resolve` | Never connected — wake race, DNS not up yet |
| Aug 18 17:30 | `SSL SYSCALL error: EOF detected`, mid the initial catalog query (`SELECT c.tableoid...FROM pg_class`), run died at 17:34:20 (~4m14s in) | **Connected fine, dropped mid-dump** |
| Aug 19 17:32 | `SSL SYSCALL error: EOF detected`, mid `EXECUTE dumpEnumType('16727')`, run died at 17:38:30 (~5m51s in) | **Connected fine, dropped mid-dump** |

The two successful dumps (Aug 18 16:43, Aug 19 15:47 — both hand-run at other
times) each completed in under 3 minutes. The two mid-dump failures ran
4–6 minutes before dying, i.e. past where a healthy run would already be
done. §1(a) (host gate) would have passed cleanly on both Aug 18 and Aug 19 —
the host answered — so it would not have prevented either. That is what §1(b)
(retry) is for. Likely shared root cause across all four: wake-adjacent
network instability (Wi-Fi reassociating, DHCP renewal, VPN coming up)
landing either before the dump starts (Aug 16/17) or inside its ~3-minute
window (Aug 18/19), depending on timing that isn't fully in our control.

## 3. The separate, still-open question: the schedule itself

A `Hour=12, Minute=30` entry that has fired at 17:3x on every one of its four
recorded runs is a scheduling defect, not a network one — §1 and §2 fix what
happens *after* the job fires late; neither touches *why* it fires late.

`ANALYTIQ_AGENT_ORCHESTRATION.md` §6 documents the identical failure mode for
the main cycle (`com.analytiq.dailycycle`) and its fix: launchd resolves
`StartCalendarInterval` in whatever timezone was current at bootstrap and
never re-resolves it, and does not reliably catch up a trigger missed to
sleep. The fix there was to stop asking launchd to hit a single clock minute
at all — fire hourly and let the script itself decide, in local time, which
hours count (`SLOTS="8 13 19"` in `daily_cycle.sh`). The installed
`deployment/com.analytiq.dbbackup.plist` already names this exact remedy in
its own comment (lines 16–22, written 2026-08-13): *"If that bites more than
once, give this job the same treatment as `scripts/daily_cycle.sh`: an hourly
tick plus a slot check the script evaluates against local time."* It has now
bitten four times.

**Recommendation: adopt it** — hourly `StartCalendarInterval` (`Minute=0`)
plus a `SLOTS="12"`-style check inside `backup_db.sh`, mirroring
`daily_cycle.sh`'s pattern exactly (one attempted-marker per day so an hourly
tick doesn't turn one failing day into 24 dump attempts). It is timezone-proof
and picks a slot missed to sleep up at the very next tick instead of waiting
until the next calendar day.

**This is Adam's call, not mine, and I have not made this change.** It means
editing and re-bootstrapping an installed, currently-running plist
(`launchctl bootout` + `bootstrap`) that is the only thing standing between
this database and total data loss on the days everything else is broken — a
mistake in that edit is a materially worse outcome than a late backup.
Tradeoff worth weighing before approving: an hourly tick produces 23 silent
no-op firings a day (harmless, same as `daily_cycle.sh` already does) in
exchange for removing the timezone/sleep fragility entirely.

## 4. What remains unproven — stated plainly

**I have not verified this fix works.** The only real test is a scheduled
fire against a machine that was actually asleep and just woke — that cannot
be produced from this headless session, and I did not claim otherwise. What
I can state: the code now waits for reachability before dumping, retries the
dump itself up to 3 times with a promote-only-on-success temp file, and
names the failure class in the log. What I cannot state: that this actually
prevents a fifth failure. **Do not report B27 as closed.** The next honest
checkpoint is the next real scheduled fire — read `backup.log` and
`launchctl print gui/501/com.analytiq.dbbackup` (`runs`, `last exit`) after
it, specifically for whether it succeeded, and if not, whether the new log
lines correctly identify which of the two failure classes occurred.

Separately: I could not execute `bash -n` (or any invocation) against
`scripts/backup_db.sh` in this session — the permission layer denies running
this script in any form, including a syntax-only check, consistent with the
"no credential access of any kind" boundary on this mission, since the script
sources `~/.analytiq_env` when actually run. Verification here is by manual
line-by-line review against the proven-working reference (`wait_for_smtp` in
`daily_cycle.sh`, already live via `7c299d2`), not by execution. That is a
weaker form of verification than running it, and it should be treated as
such.

## 5. Test suite

There is no test suite covering `scripts/backup_db.sh` or `scripts/daily_cycle.sh`.
Searched `tests/unit/`, `tests/integration/`, `tests/e2e/` (49 Python files
total) and `scripts/` for any reference to either script by name — zero
matches; every existing test targets the Flask app. Neither `bats` nor
`shellcheck` is installed on this machine. There is nothing to run, and
nothing was reported as passing that wasn't actually run.
