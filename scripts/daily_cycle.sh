#!/bin/bash
# AnalytIQ daily orchestrator cycle. Launched by launchd
# (~/Library/LaunchAgents/com.analytiq.dailycycle.plist) at the top of every
# hour; this script decides which hours it actually acts on. Run by hand with:
#   ./scripts/daily_cycle.sh          # respects the slot and the completion stamp
#   FORCE=1 ./scripts/daily_cycle.sh  # runs now, whatever the hour or the stamp
#
# Why an hourly tick and SLOTS below, instead of three calendar entries: launchd
# computes fire times in the timezone that was in force when the job was loaded
# and never revisits that decision. Loaded in Boston and carried to Casablanca,
# the 08:00/13:00/19:00 entries fired at 13:00/18:00/00:00 local for four days
# (B1) — the 08:00 slot silently became the midnight one, which is how two of
# those days were lost to a sleeping laptop. An hourly tick has no timezone to
# get wrong (every zone in use here is a whole-hour offset), and SLOTS is read
# against local `date`, which is always right. It also fixes the second half of
# B1: a slot missed because the Mac was asleep is picked up at the first tick
# after it wakes, rather than waiting five hours for the next calendar entry.
#
# Idempotency: the completion stamp is written ONLY after the digest actually
# sends, and send_digest.py refuses to send a digest that wasn't written today.
# So a run that is missed or that fails partway is retried at the next slot,
# while a successful run makes the later slots cheap no-ops. See Sections 6 and 7
# of ANALYTIQ_AGENT_ORCHESTRATION.md.
set -euo pipefail

# Derived, not hardcoded, so a move or a second clone doesn't silently break the
# job in a way that leaves no trace in reports/cron/.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

# `claude` lives in ~/.local/bin, which is not on launchd's default PATH.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

mkdir -p reports/cron
DATE="$(date +%F)"
LOG="reports/cron/$DATE.log"
STAMP="reports/cron/.completed-$DATE"
LOCK="reports/cron/.lock"

# The local hours at which a cycle may start, ascending.
SLOTS="8 13 19"
HOUR=$((10#$(date +%H)))
ATTEMPTED=""

if [ "${FORCE:-0}" != "1" ]; then
  # The most recent slot that has already come round today, if any.
  SLOT=""
  for s in $SLOTS; do
    if [ "$HOUR" -ge "$s" ]; then SLOT="$s"; fi
  done
  # Before the first slot there is nothing to do and nothing worth saying: this
  # script now wakes 24 times a day and only three of those are interesting.
  if [ -z "$SLOT" ]; then exit 0; fi

  # One attempt per slot, so a failing cycle retries three times a day rather
  # than twenty-four. The marker is spent further down, by a run that actually
  # reaches the orchestrator — a tick that turns back because another cycle holds
  # the lock has not used the slot up, and the next tick may still try.
  ATTEMPTED="reports/cron/.attempted-$DATE-$SLOT"
  if [ -f "$ATTEMPTED" ]; then exit 0; fi

  if [ -f "$STAMP" ]; then
    # Marked here too, so this says itself once per slot instead of once an hour.
    # It is the only routine evidence in the log that launchd is still firing at
    # all, which is worth three lines a day.
    touch "$ATTEMPTED"
    echo "=== $(date): today's cycle already completed — skipping (FORCE=1 to override) ===" >> "$LOG"
    exit 0
  fi
fi

# Mutex: a hand-run cycle overlapping a scheduled one would put two orchestrators
# on the same reports/ files. The lock now records its pid and is judged on
# whether that process is alive, because with the retries below a healthy run can
# legitimately outlast the two-hour age rule this used to rely on — which would
# have meant breaking the lock on a cycle that was working fine.
if [ -d "$LOCK" ]; then
  LOCK_PID="$(cat "$LOCK/pid" 2>/dev/null || true)"
  if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null &&
     ps -p "$LOCK_PID" -o command= 2>/dev/null | grep -q daily_cycle.sh; then
    echo "=== $(date): another cycle (pid $LOCK_PID) is already running — exiting ===" >> "$LOG"
    exit 0
  fi
  # A lock with no pid file was taken by a pre-retry version of this script; fall
  # back to the old age rule so the changeover can't break a live one.
  if [ -z "$LOCK_PID" ] && [ -n "$(find "$LOCK" -maxdepth 0 -mmin -120 2>/dev/null)" ]; then
    echo "=== $(date): another cycle is already running — exiting ===" >> "$LOG"
    exit 0
  fi
  echo "=== $(date): breaking stale lock (pid ${LOCK_PID:-unknown} is not running) ===" >> "$LOG"
  rm -rf "$LOCK" 2>/dev/null || true
fi
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "=== $(date): another cycle is already running — exiting ===" >> "$LOG"
  exit 0
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK" 2>/dev/null || true' EXIT

# The slot is spent now: this run owns the lock and is about to start work. Doing
# it here rather than after the run means a cycle killed mid-flight (lid closed)
# doesn't re-fire every hour for the rest of the day; the next slot still gets it.
if [ -n "$ATTEMPTED" ]; then touch "$ATTEMPTED"; fi

echo "=== AnalytIQ daily cycle $(date) ===" >> "$LOG"

# Headless orchestrator run. acceptEdits allows file writes only; anything
# requiring broader permissions gets queued for Adam instead of executed.
# NOTE: SMTP credentials are deliberately NOT sourced here. This process is an
# autonomous agent whose output is appended to a repo-local log; per guardrail 3
# ("no agent handles credentials") they are scoped to the digest subshell below.
PROMPT="You are the Orchestrator. Read ANALYTIQ_AGENT_ORCHESTRATION.md, reports/STATE.md, and PART1_EXECUTION_PLAN.md. Run today's cycle per the Master Timeline. Delegate to subagents as needed. Finish by updating reports/STATE.md and writing reports/ADAM_DAILY.md in the required digest format (Section 7.2). Then publish today's decision sheet as an Artifact per Section 7.4 — one card per open decision, options drawn from the underlying agent reports rather than from the digest summary — and write its URL as the last line of reports/DECISION_SHEET_URL. send_digest.py links whatever is in that file, but ignores it unless it was written today."
RESUME_PROMPT="Your previous run was cut off part-way by a network error, not by anything you did wrong. Check what you had already finished — reports/STATE.md, reports/ADAM_DAILY.md, reports/DECISION_SHEET_URL and the agent reports under reports/ — and carry on from there rather than starting over. Finish the cycle: reports/STATE.md updated, reports/ADAM_DAILY.md written in the Section 7.2 digest format, and today's decision sheet published with its URL as the last line of reports/DECISION_SHEET_URL."

# Success is judged the way send_digest.py judges it — a brief whose mtime is
# today — and not by exit status. A run that wrote the digest and then dropped
# its connection has done the job; one that exited 0 without writing a brief
# has not, and is worth another attempt.
digest_is_todays() {
  [ -f reports/ADAM_DAILY.md ] && [ "$(date -r reports/ADAM_DAILY.md +%F)" = "$DATE" ]
}

# Six cycles between Aug 10 and Aug 13 died mid-run on transient API errors
# (ENOTFOUND, ECONNRESET, "connection closed mid-response"), each throwing away
# up to 90 minutes of work and leaving the day to the next slot five hours later.
# Retry in place instead: the second attempt resumes the same session so the work
# already done isn't repeated, and the third starts clean in case the session
# itself is what is wedged.
SESSION_ID="$(uuidgen | tr 'A-Z' 'a-z')"
ORCH_OK=0
for attempt in 1 2 3; do
  case "$attempt" in
    1)
      claude -p "$PROMPT" --session-id "$SESSION_ID" \
        --permission-mode acceptEdits >> "$LOG" 2>&1 || true
      ;;
    2)
      echo "=== $(date): attempt 1 produced no digest — resuming session $SESSION_ID ===" >> "$LOG"
      claude -p "$RESUME_PROMPT" --resume "$SESSION_ID" \
        --permission-mode acceptEdits >> "$LOG" 2>&1 || true
      ;;
    3)
      SESSION_ID="$(uuidgen | tr 'A-Z' 'a-z')"
      echo "=== $(date): resume produced no digest either — restarting clean as $SESSION_ID ===" >> "$LOG"
      claude -p "$PROMPT" --session-id "$SESSION_ID" \
        --permission-mode acceptEdits >> "$LOG" 2>&1 || true
      ;;
  esac
  if digest_is_todays; then
    ORCH_OK=1
    break
  fi
  echo "ORCHESTRATOR ATTEMPT $attempt FAILED $(date)" >> "$LOG"
  # Short backoff: these failures are network-shaped, and the ones seen so far
  # cleared in minutes. Long enough to outlast a blip, short enough that three
  # attempts still fit inside a slot.
  if [ "$attempt" -lt 3 ]; then sleep $((attempt * 120)); fi
done
if [ "$ORCH_OK" = "0" ]; then
  echo "ORCHESTRATOR RUN FAILED $(date) — 3 attempts, no digest written today" >> "$LOG"
fi

# Deterministic email step — a script, not an agent. Credentials live only inside
# this subshell, so they are never present in the agent's environment above.
# The stamp is written only on a confirmed send of a digest dated today.
if (
  set -euo pipefail
  if [ ! -f "$HOME/.analytiq_env" ]; then
    echo "ERROR: ~/.analytiq_env not found — cannot send digest"
    exit 1
  fi
  perm="$(stat -f %Lp "$HOME/.analytiq_env" 2>/dev/null || echo unknown)"
  if [ "$perm" != "600" ]; then
    echo "WARNING: ~/.analytiq_env is mode $perm — should be 600 (chmod 600 ~/.analytiq_env)"
  fi
  # shellcheck source=/dev/null
  source "$HOME/.analytiq_env"
  python3 scripts/send_digest.py
) >> "$LOG" 2>&1; then
  touch "$STAMP"
  echo "=== cycle completed, digest sent $(date) ===" >> "$LOG"
else
  echo "DIGEST NOT SENT $(date) — no stamp written; next slot will retry" >> "$LOG"
  # A failed cycle must not be silent. Without this, the freshness gate suppresses
  # the stale digest and the day simply produces no email at all — which is exactly
  # how Aug 10-11 2026 went unnoticed for two days. send_digest.py caps this at one
  # notice per day, so the later slots don't re-mail the same failure.
  # Same subshell discipline as the send above: credentials stay out of the agent's
  # environment and exist only for the duration of this call.
  if [ "$ORCH_OK" = "0" ]; then
    REASON="orchestrator run failed on all 3 attempts — see log tail below"
  else
    REASON="orchestrator wrote today's brief but the digest still did not send — see log tail below"
  fi
  (
    set -euo pipefail
    [ -f "$HOME/.analytiq_env" ] || { echo "cannot send failure notice — ~/.analytiq_env missing"; exit 1; }
    # shellcheck source=/dev/null
    source "$HOME/.analytiq_env"
    python3 scripts/send_digest.py --failure-notice "$REASON" "$LOG"
  ) >> "$LOG" 2>&1 || echo "FAILURE NOTICE COULD NOT BE SENT $(date)" >> "$LOG"
fi
