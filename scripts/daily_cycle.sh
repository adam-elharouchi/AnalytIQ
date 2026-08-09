#!/bin/bash
# AnalytIQ daily orchestrator cycle. Launched by launchd
# (~/Library/LaunchAgents/com.analytiq.dailycycle.plist) at 08:00, with catch-up
# attempts at 13:00 and 19:00 local time. Run by hand any time with:
#   ./scripts/daily_cycle.sh          # respects today's completion stamp
#   FORCE=1 ./scripts/daily_cycle.sh  # runs even if today already completed
#
# Idempotency: the completion stamp is written ONLY after the digest actually
# sends, and send_digest.py refuses to send a digest that wasn't written today.
# So a run that is missed (laptop asleep at 08:00) or that fails partway is
# retried at the next trigger, while a successful run makes the later triggers
# cheap no-ops. See Sections 6 and 7 of ANALYTIQ_AGENT_ORCHESTRATION.md.
set -euo pipefail

# Derived, not hardcoded, so a move or a second clone doesn't silently break the
# job in a way that leaves no trace in reports/cron/.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

# `claude` lives in ~/.local/bin, which is not on launchd's default PATH.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

mkdir -p reports/cron
LOG="reports/cron/$(date +%F).log"
STAMP="reports/cron/.completed-$(date +%F)"
LOCK="reports/cron/.lock"

if [ -f "$STAMP" ] && [ "${FORCE:-0}" != "1" ]; then
  echo "=== $(date): today's cycle already completed — skipping (FORCE=1 to override) ===" >> "$LOG"
  exit 0
fi

# Mutex: a hand-run cycle overlapping a scheduled one would put two orchestrators
# on the same reports/ files. Break locks older than 2h (killed run left it behind).
if [ -d "$LOCK" ] && [ -z "$(find "$LOCK" -maxdepth 0 -mmin -120 2>/dev/null)" ]; then
  echo "=== $(date): breaking stale lock ===" >> "$LOG"
  rmdir "$LOCK" 2>/dev/null || true
fi
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "=== $(date): another cycle is already running — exiting ===" >> "$LOG"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

echo "=== AnalytIQ daily cycle $(date) ===" >> "$LOG"

# Headless orchestrator run. acceptEdits allows file writes only; anything
# requiring broader permissions gets queued for Adam instead of executed.
# NOTE: SMTP credentials are deliberately NOT sourced here. This process is an
# autonomous agent whose output is appended to a repo-local log; per guardrail 3
# ("no agent handles credentials") they are scoped to the digest subshell below.
claude -p "You are the Orchestrator. Read ANALYTIQ_AGENT_ORCHESTRATION.md, reports/STATE.md, and PART1_EXECUTION_PLAN.md. Run today's cycle per the Master Timeline. Delegate to subagents as needed. Finish by updating reports/STATE.md and writing reports/ADAM_DAILY.md in the required digest format (Section 7.2)." \
  --permission-mode acceptEdits \
  >> "$LOG" 2>&1 || echo "ORCHESTRATOR RUN FAILED $(date)" >> "$LOG"

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
  echo "DIGEST NOT SENT $(date) — no stamp written; next trigger will retry" >> "$LOG"
fi
