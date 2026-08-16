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
#
# Every long-running step below is bounded, and that is not decoration. On
# 2026-08-14 an orchestrator attempt ran for THIRTY-SIX HOURS before failing.
# Nothing stopped it, and because the lock is judged on pid liveness, every tick
# for the next two days found a live process and stood down: Aug 15 produced no
# log file at all, and Adam heard nothing for two days. Bounds, in the order they
# apply: ATTEMPT_CAP kills a single attempt, MAX_RUN lets the *next* tick kill a
# whole cycle that outlasted it, and the failure notice retries rather than
# dying on one refused SMTP connection.
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

# What separates a wedged run from a busy one is silence, not elapsed time. The
# first version of this bound used elapsed time and would have been wrong: the
# 2026-08-16 cycle ran 4h23m while writing agent reports every few minutes, and a
# 75-minute cap would have killed productive work three times and called the day
# failed. The Aug 14 run, by contrast, wrote nothing at all for 36 hours.
# So: an attempt is killed after this long with no new file anywhere under
# reports/ (excluding reports/cron/, which only this script writes).
IDLE_CAP=5400
# Whole-cycle ceiling, retries and backoff included. Past it the cycle stops
# trying and goes to the digest step, so a bad day still ends in a failure notice
# rather than running into tomorrow.
RUN_DEADLINE=21600
# Lock bound for the NEXT tick: only trips if a cycle blew past its own deadline,
# i.e. the bounds above failed. Standing down forever is what cost Aug 15.
MAX_RUN=25200

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
# on the same reports/ files. The lock records its pid and is judged on whether
# that process is alive — but liveness alone is not enough, because a wedged run
# is alive too. MAX_RUN is the second half of that judgement.
if [ -d "$LOCK" ]; then
  LOCK_PID="$(cat "$LOCK/pid" 2>/dev/null || true)"
  if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null &&
     ps -p "$LOCK_PID" -o command= 2>/dev/null | grep -q daily_cycle.sh; then
    if [ -z "$(find "$LOCK" -maxdepth 0 -mmin -$((MAX_RUN / 60)) 2>/dev/null)" ]; then
      # Alive, and has been for longer than any real cycle takes. This is the
      # Aug 14 case: standing down here is how two days went dark.
      echo "=== $(date): cycle pid $LOCK_PID has held the lock over $((MAX_RUN / 3600))h — killing it and taking the slot ===" >> "$LOG"
      pkill -TERM -P "$LOCK_PID" 2>/dev/null || true
      kill -TERM "$LOCK_PID" 2>/dev/null || true
      sleep 10
      pkill -KILL -P "$LOCK_PID" 2>/dev/null || true
      kill -KILL "$LOCK_PID" 2>/dev/null || true
      rm -rf "$LOCK" 2>/dev/null || true
    else
      echo "=== $(date): another cycle (pid $LOCK_PID) is already running — exiting ===" >> "$LOG"
      exit 0
    fi
  else
    # A lock with no pid file was taken by a pre-retry version of this script;
    # fall back to the old age rule so the changeover can't break a live one.
    if [ -z "$LOCK_PID" ] && [ -n "$(find "$LOCK" -maxdepth 0 -mmin -120 2>/dev/null)" ]; then
      echo "=== $(date): another cycle is already running — exiting ===" >> "$LOG"
      exit 0
    fi
    echo "=== $(date): breaking stale lock (pid ${LOCK_PID:-unknown} is not running) ===" >> "$LOG"
    rm -rf "$LOCK" 2>/dev/null || true
  fi
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
RESUME_PROMPT="Your previous run was cut off part-way, either by a network error or by exceeding its time limit. Neither is a fault of yours. Check what you had already finished — reports/STATE.md, reports/ADAM_DAILY.md, reports/DECISION_SHEET_URL and the agent reports under reports/ — and carry on from there rather than starting over. Prioritise finishing: reports/STATE.md updated, reports/ADAM_DAILY.md written in the Section 7.2 digest format, and today's decision sheet published with its URL as the last line of reports/DECISION_SHEET_URL. A brief digest that sends beats a thorough one that doesn't."

# Success is judged the way send_digest.py judges it — a brief whose mtime is
# today — and not by exit status. A run that wrote the digest and then dropped
# its connection has done the job; one that exited 0 without writing a brief
# has not, and is worth another attempt.
# Deliberately re-reads the date instead of using $DATE, which is pinned when the
# process starts. A cycle that starts on one day and finishes on the next would
# otherwise compare the new brief against the old date and conclude it had failed
# — which is exactly what happened on 2026-08-14: attempt 1 wrote a brief dated
# Aug 15, this check measured it against Aug 14, and two further orchestrator
# sessions were burned re-doing work that was already done. (B21)
digest_is_todays() {
  [ -f reports/ADAM_DAILY.md ] && [ "$(date -r reports/ADAM_DAILY.md +%F)" = "$(date +%F)" ]
}

# A capped attempt. macOS ships no coreutils `timeout`, and a plain timeout would
# be the wrong tool anyway — see IDLE_CAP. This watchdog polls for progress: the
# work runs in the background and is killed only when reports/ has gone quiet for
# IDLE_CAP, or when the whole cycle is out of time. Children are killed too —
# killing the shell alone would orphan `claude` and leave it holding the network.
newest_report_mtime() {
  find reports -type f -not -path "reports/cron/*" -exec stat -f %m {} \; 2>/dev/null |
    sort -rn | head -1
}

run_capped() {
  local idle="$1"; shift
  "$@" >> "$LOG" 2>&1 &
  local work=$!
  (
    while kill -0 "$work" 2>/dev/null; do
      sleep 60
      kill -0 "$work" 2>/dev/null || break
      local now newest reason=""
      now=$(date +%s)
      newest=$(newest_report_mtime)
      if [ -n "$newest" ] && [ $(( now - newest )) -ge "$idle" ]; then
        reason="nothing written under reports/ for $(( (now - newest) / 60 ))m"
      elif [ "$now" -ge "$DEADLINE" ]; then
        reason="cycle deadline reached"
      fi
      if [ -n "$reason" ]; then
        echo "=== $(date): terminating attempt — $reason ===" >> "$LOG"
        pkill -TERM -P "$work" 2>/dev/null || true
        kill -TERM "$work" 2>/dev/null || true
        sleep 20
        pkill -KILL -P "$work" 2>/dev/null || true
        kill -KILL "$work" 2>/dev/null || true
        break
      fi
    done
  ) &
  local watchdog=$!
  local rc=0
  wait "$work" || rc=$?
  kill -TERM "$watchdog" 2>/dev/null || true
  wait "$watchdog" 2>/dev/null || true
  return "$rc"
}

# Six cycles between Aug 10 and Aug 13 died mid-run on transient API errors
# (ENOTFOUND, ECONNRESET, "connection closed mid-response"), each throwing away
# up to 90 minutes of work and leaving the day to the next slot five hours later.
# Retry in place instead: the second attempt resumes the same session so the work
# already done isn't repeated, and the third starts clean in case the session
# itself is what is wedged. Each is capped — an attempt that hangs is the failure
# mode that cost Aug 14 and Aug 15.
SESSION_ID="$(uuidgen | tr 'A-Z' 'a-z')"
DEADLINE=$(( $(date +%s) + RUN_DEADLINE ))
ORCH_OK=0
for attempt in 1 2 3; do
  case "$attempt" in
    1)
      run_capped "$IDLE_CAP" claude -p "$PROMPT" --session-id "$SESSION_ID" \
        --permission-mode acceptEdits || true
      ;;
    2)
      echo "=== $(date): attempt 1 produced no digest — resuming session $SESSION_ID ===" >> "$LOG"
      run_capped "$IDLE_CAP" claude -p "$RESUME_PROMPT" --resume "$SESSION_ID" \
        --permission-mode acceptEdits || true
      ;;
    3)
      SESSION_ID="$(uuidgen | tr 'A-Z' 'a-z')"
      echo "=== $(date): resume produced no digest either — restarting clean as $SESSION_ID ===" >> "$LOG"
      run_capped "$IDLE_CAP" claude -p "$PROMPT" --session-id "$SESSION_ID" \
        --permission-mode acceptEdits || true
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
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    echo "=== $(date): cycle deadline reached — not starting another attempt ===" >> "$LOG"
    break
  fi
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
  # Dated at write time, not at process start, for the same reason as
  # digest_is_todays above: a cycle that sends its digest after midnight has
  # completed *today*, and stamping yesterday would leave today's slots unsuppressed
  # and re-run the whole cycle. Fixing only the check and not the stamp would have
  # been a subtler bug than the one it replaced. (B21)
  touch "reports/cron/.completed-$(date +%F)"
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
  # Retried, because on 2026-08-14 the single attempt hit one ConnectionRefused
  # at 00:28 and gave up — turning a failed cycle into a silent one, which is the
  # failure this whole mechanism exists to prevent.
  NOTICE_SENT=0
  for n in 1 2 3; do
    if (
      set -euo pipefail
      [ -f "$HOME/.analytiq_env" ] || { echo "cannot send failure notice — ~/.analytiq_env missing"; exit 1; }
      # shellcheck source=/dev/null
      source "$HOME/.analytiq_env"
      python3 scripts/send_digest.py --failure-notice "$REASON" "$LOG"
    ) >> "$LOG" 2>&1; then
      NOTICE_SENT=1
      break
    fi
    echo "failure notice attempt $n did not send $(date)" >> "$LOG"
    if [ "$n" -lt 3 ]; then sleep $((n * 180)); fi
  done
  if [ "$NOTICE_SENT" = "0" ]; then
    echo "FAILURE NOTICE COULD NOT BE SENT $(date) — 3 attempts" >> "$LOG"
  fi
fi
