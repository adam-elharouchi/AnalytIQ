#!/usr/bin/env bash
#
# Encrypted, verified, off-provider backup of the AnalytIQ production database.
#
# WHY THIS EXISTS: on 2026-08-12 Adam checked the Supabase dashboard and found
# NO scheduled backups and no point-in-time recovery on the current plan. The
# recovery point objective was therefore total — losing the database meant
# losing every class, submission, grade and the fall-semester dataset the exit
# story depends on. See docs/RUNBOOK.md section 3.
#
# DESIGN NOTES
#
#   pg_dump runs in Docker, not on the host. There is no pg_dump on this Mac
#   and no Homebrew to install one, but Docker is already a dependency (see
#   docker-compose.yml). It is also the better answer: pg_dump refuses to dump
#   from a server newer than itself, and Supabase upgrades Postgres without
#   asking us. Bumping PG_IMAGE is a one-line fix; re-installing a host
#   toolchain is not. If a host pg_dump ever exists it is used in preference.
#
#   Credentials never enter argv. A connection URI passed as an argument is
#   visible to every user on the machine via `ps`. The URI is parsed into
#   components and the password travels in PGPASSWORD, exported into the
#   container by name (`--env PGPASSWORD`) so the value itself is never written
#   on a command line.
#
#   Custom format (-Fc), not plain SQL. It compresses, restores selectively,
#   and — the point here — `pg_restore --list` can read its table of contents,
#   which is how each backup is verified before the old ones are swept.
#
#   Every run verifies. A dump that has never been read back is a file, not a
#   backup. Each run decrypts its own output and lists the archive contents; if
#   that fails the run fails loudly and old backups are NOT deleted.
#
# USAGE
#   ./scripts/backup_db.sh              # dump, encrypt, verify, sweep old
#   ./scripts/backup_db.sh --list       # show what backups exist
#   ./scripts/backup_db.sh --verify-only FILE
#   ./scripts/backup_db.sh --restore-cmd FILE   # print the restore recipe
#
# CONFIG (all optional except the passphrase)
#   BACKUP_PASSPHRASE  REQUIRED. Put it in ~/.analytiq_env next to the SMTP
#                      creds. LOSING IT MAKES EVERY BACKUP UNREADABLE — store a
#                      copy in a password manager, not only on this machine.
#   BACKUP_DIR         default ~/AnalytIQ-backups (deliberately outside the repo)
#   RETAIN_DAYS        default 14
#   PG_IMAGE           default postgres:17-alpine
#   DATABASE_URL       read from the environment, else from the repo .env
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$HOME/AnalytIQ-backups}"
RETAIN_DAYS="${RETAIN_DAYS:-14}"
# Pinned by digest, not by the mutable :17-alpine tag, so a silently-republished
# tag cannot change what runs against the database. Resolved 2026-08-16; update
# deliberately when a newer Postgres patch release is wanted.
PG_IMAGE="${PG_IMAGE:-postgres:17-alpine@sha256:18cfe3ef5e6815560c98237d6216d1e5119702fb0f3894c8785dd58b8bbe5d73}"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$BACKUP_DIR/backup.log"

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$*" | tee -a "$LOG" >&2; }
die() { log "FAILED: $*"; notify_failure "$*"; exit 1; }

# --- failure notification ----------------------------------------------------
# Authorized by Adam on the 2026-08-18 decision sheet, card 5. This is a SECOND
# exception to guardrail 5.1 ("no agent sends any external communication"), and it
# is deliberately built to the same discipline as the first one: a deterministic
# script rather than an agent free-forming a send, to Adam's own hardcoded address,
# capped at one notice per day.
#
# Why it exists: this job ran once on 2026-08-16, then failed on Aug 16 and Aug 17
# and told nobody. `launchctl` recorded exit status 1 and nothing else did. A backup
# that fails silently is worse than no backup, because it looks handled — the same
# failure shape, and the same fix, as the digest's own failure notice.
BACKUP_ALERT_TO="adamelharouchi5@gmail.com"   # HARDCODED. Agents may not modify this line.

notify_failure() {
  local reason="${1:-unknown}"
  local notified="$BACKUP_DIR/.notified-$(date +%F)"
  if [ -f "$notified" ]; then
    log "  failure notice already sent today — not repeating"
    return 0
  fi
  if [ -z "${DIGEST_SMTP_USER:-}" ] || [ -z "${DIGEST_SMTP_PASS:-}" ]; then
    log "  cannot send failure notice — SMTP credentials not present in ~/.analytiq_env"
    return 0
  fi
  # Credentials are read from the environment inside python and never echoed.
  if BACKUP_ALERT_REASON="$reason" \
     BACKUP_ALERT_TO="$BACKUP_ALERT_TO" \
     BACKUP_ALERT_LOG="$LOG" \
     BACKUP_ALERT_DIR="$BACKUP_DIR" \
     python3 -c '
import os, ssl, smtplib, datetime, pathlib
from email.mime.text import MIMEText

to      = os.environ["BACKUP_ALERT_TO"]
reason  = os.environ["BACKUP_ALERT_REASON"]
logpath = pathlib.Path(os.environ["BACKUP_ALERT_LOG"])
bdir    = pathlib.Path(os.environ["BACKUP_ALERT_DIR"])
user    = os.environ["DIGEST_SMTP_USER"]
pw      = os.environ["DIGEST_SMTP_PASS"]
today   = datetime.date.today()

dumps = sorted(bdir.glob("analytiq-*.dump.enc"))
if dumps:
    newest = max(dumps, key=lambda f: f.stat().st_mtime)
    age = (datetime.datetime.now() - datetime.datetime.fromtimestamp(newest.stat().st_mtime)).days
    hold = f"{len(dumps)} backup(s) on hand; newest is {newest.name}, {age} day(s) old."
else:
    hold = "THERE IS NO BACKUP ON HAND AT ALL."

tail = ""
if logpath.exists():
    tail = "\n".join(logpath.read_text(errors="replace").splitlines()[-20:])

body = (
    f"AnalytIQ database backup FAILED on {today:%A %B %d, %Y}.\n\n"
    f"Reason: {reason}\n\n"
    f"{hold}\n\n"
    f"This job is scheduled once a day at 12:30 local. If the Mac is asleep at that\n"
    f"time launchd defers the run until it next wakes, which is how the Aug 16 and\n"
    f"Aug 17 attempts ended up firing at 17:31 and 17:34 with no network.\n\n"
    f"To run one by hand:\n"
    f"    cd ~/Documents/GitHub/AnalytIQ/\"AnalytIQ Repo\"\n"
    f"    ./scripts/backup_db.sh\n"
)
if tail:
    body += f"\n--- last 20 lines of {logpath} ---\n{tail}\n"

msg = MIMEText(body, "plain", "utf-8")
msg["Subject"] = f"AnalytIQ — {today:%b %d} — DATABASE BACKUP FAILED"
msg["From"] = user
msg["To"] = to

ctx = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=30) as s:
    s.login(user, pw)
    s.sendmail(user, [to], msg.as_string())
'; then
    touch "$notified"
    log "  failure notice sent"
  else
    log "  failure notice could not be sent (see error above) — not stamping, next run retries"
  fi
}

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

# --- credentials -------------------------------------------------------------
# Sourced, never echoed. ~/.analytiq_env is the established home for secrets on
# this machine (orchestration doc section 7.1) and is outside the repo.
if [ -f "$HOME/.analytiq_env" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.analytiq_env"
fi

if [ -z "${DATABASE_URL:-}" ] && [ -f "$REPO/.env" ]; then
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$REPO/.env" | head -1 | cut -d= -f2- | tr -d '"'"'"'')"
fi

# --- subcommands that need no database ---------------------------------------
case "${1:-}" in
  --list)
    printf '%-38s %10s  %s\n' "BACKUP" "SIZE" "TAKEN"
    shopt -s nullglob
    for f in "$BACKUP_DIR"/analytiq-*.dump.enc; do
      printf '%-38s %10s  %s\n' "$(basename "$f")" \
        "$(du -h "$f" | cut -f1)" "$(date -r "$f" '+%Y-%m-%d %H:%M')"
    done
    exit 0
    ;;
  --restore-cmd)
    [ -n "${2:-}" ] || die "--restore-cmd needs a backup file"
    cat <<RECIPE
Restore recipe for $(basename "$2")

  1. Decrypt (you will be prompted for BACKUP_PASSPHRASE):
       openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \\
         -in "$2" -out /tmp/analytiq-restore.dump

  2. Inspect before you touch anything — confirm it is the data you expect:
       docker run --rm -v /tmp:/t $PG_IMAGE pg_restore --list /t/analytiq-restore.dump | head -40

  3. Restore into a SCRATCH database first. Never restore straight over
     production; a bad restore is worse than the outage it was meant to fix.
       docker run --rm -v /tmp:/t --env PGPASSWORD $PG_IMAGE \\
         pg_restore -h HOST -U USER -d SCRATCH_DB --clean --if-exists /t/analytiq-restore.dump

  4. Only once the scratch copy is verified, repeat step 3 against the real
     target, and record the elapsed time in docs/RUNBOOK.md as the measured RTO.

  5. Shred the plaintext when finished:
       rm -P /tmp/analytiq-restore.dump
RECIPE
    exit 0
    ;;
esac

[ -n "${BACKUP_PASSPHRASE:-}" ] || die "BACKUP_PASSPHRASE is not set. Add it to ~/.analytiq_env. Without it there is no encryption key and no backup."
[ "${#BACKUP_PASSPHRASE}" -ge 16 ] || die "BACKUP_PASSPHRASE is shorter than 16 characters. This is the only thing standing between a stolen backup file and every student record in it."

# Files that must not survive this script. verify_archive()'s RETURN trap already
# covers the normal path; this covers INT/TERM, where a decrypted plaintext dump of
# every student record could otherwise be left in /tmp.
CLEANUP_PATHS=()
cleanup_tmp() {
  [ "${#CLEANUP_PATHS[@]}" -gt 0 ] && rm -f -- "${CLEANUP_PATHS[@]}" 2>/dev/null
  return 0
}
trap cleanup_tmp EXIT INT TERM

# --- verify-only path --------------------------------------------------------
verify_archive() {
  local enc="$1" plain
  plain="$(mktemp -t analytiq-verify)"
  CLEANUP_PATHS+=("$plain")
  # shellcheck disable=SC2064
  trap "rm -f -- '$plain'" RETURN

  openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
    -pass env:BACKUP_PASSPHRASE -in "$enc" -out "$plain" \
    || { log "  decrypt failed"; return 1; }

  local toc
  toc="$(docker run --rm -v "$(dirname "$plain")":/v "$PG_IMAGE" \
          pg_restore --list "/v/$(basename "$plain")" 2>/dev/null | grep -c 'TABLE DATA' || true)"

  if [ "${toc:-0}" -lt 1 ]; then
    log "  archive decrypted but contains no TABLE DATA entries — treating as corrupt"
    return 1
  fi
  log "  verified: archive readable, $toc tables with data"
  return 0
}

if [ "${1:-}" = "--verify-only" ]; then
  [ -n "${2:-}" ] || die "--verify-only needs a backup file"
  log "verifying $2"
  verify_archive "$2" && { log "OK"; exit 0; } || die "verification failed"
fi

# --- parse the connection URI ------------------------------------------------
[ -n "${DATABASE_URL:-}" ] || die "DATABASE_URL is not set (checked the environment and $REPO/.env)"

export DATABASE_URL

eval "$(python3 - <<'PY'
import os, sys, urllib.parse as u
p = u.urlparse(os.environ["DATABASE_URL"])
if not p.hostname:
    sys.exit("could not parse DATABASE_URL")
def q(s): return "'" + str(s).replace("'", "'\\''") + "'"
print(f"PGHOST={q(p.hostname)}")
print(f"PGPORT={q(p.port or 5432)}")
print(f"PGUSER={q(u.unquote(p.username or ''))}")
print(f"PGDATABASE={q((p.path or '/postgres').lstrip('/') or 'postgres')}")
print(f"PGPASSWORD={q(u.unquote(p.password or ''))}")
PY
)" || die "could not parse DATABASE_URL"
export PGHOST PGPORT PGUSER PGDATABASE PGPASSWORD

case "$PGHOST" in
  localhost|127.0.0.1|*.local)
    log "NOTE: DATABASE_URL points at $PGHOST — this is a LOCAL database, not production."
    log "      Backing it up anyway, but this is almost certainly not what you want scheduled."
    ;;
esac

OUT="$BACKUP_DIR/analytiq-$STAMP.dump.enc"
log "starting backup of $PGDATABASE at $PGHOST -> $(basename "$OUT")"

# --- dump + encrypt in one stream --------------------------------------------
# Piped, so the plaintext dump never lands on disk. set -o pipefail means a
# pg_dump failure fails the run rather than yielding an encrypted empty file.
if command -v pg_dump >/dev/null 2>&1; then
  log "  using host pg_dump ($(pg_dump --version | awk '{print $NF}'))"
  DUMP=(pg_dump --format=custom --no-owner --no-acl --compress=6)
else
  log "  using $PG_IMAGE (no host pg_dump)"
  # A container's "localhost" is the container, not the Mac. Remote hosts
  # (Supabase, the real case) work on default bridge networking and need no
  # special handling; only a local database does. --network host is deliberately
  # not used — it is a no-op for reaching the host on Docker Desktop for macOS.
  case "$PGHOST" in
    localhost|127.0.0.1)
      log "  remapping $PGHOST -> host.docker.internal for the container"
      export PGHOST=host.docker.internal
      ;;
  esac
  DUMP=(docker run --rm
        --env PGHOST --env PGPORT --env PGUSER --env PGDATABASE --env PGPASSWORD
        "$PG_IMAGE" pg_dump --format=custom --no-owner --no-acl --compress=6)
fi

if ! "${DUMP[@]}" 2>>"$LOG" \
     | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt \
         -pass env:BACKUP_PASSPHRASE -out "$OUT"; then
  rm -f -- "$OUT"
  die "pg_dump failed — no backup written. Check $LOG. If the error mentions a server version mismatch, raise PG_IMAGE to match Supabase's Postgres version."
fi

chmod 600 "$OUT"
SIZE=$(du -h "$OUT" | cut -f1)
BYTES=$(wc -c < "$OUT" | tr -d ' ')
[ "$BYTES" -gt 4096 ] || { rm -f -- "$OUT"; die "backup is only $BYTES bytes — implausibly small, treating as failed"; }
log "  wrote $SIZE"

# --- verify before trusting it -----------------------------------------------
if ! verify_archive "$OUT"; then
  log "VERIFICATION FAILED — keeping the file for inspection and NOT sweeping old backups."
  notify_failure "archive written but failed verification — kept at $OUT for inspection"
  exit 1
fi

# --- retention sweep ---------------------------------------------------------
# Only reached when this run produced a verified backup, so a run of failures
# can never age out the last good copy.
SWEPT=$(find "$BACKUP_DIR" -maxdepth 1 -name 'analytiq-*.dump.enc' -type f -mtime "+$RETAIN_DAYS" -print -delete | wc -l | tr -d ' ')
[ "$SWEPT" -gt 0 ] && log "  swept $SWEPT backup(s) older than $RETAIN_DAYS days"

KEPT=$(find "$BACKUP_DIR" -maxdepth 1 -name 'analytiq-*.dump.enc' -type f | wc -l | tr -d ' ')
log "done — $KEPT backup(s) on hand in $BACKUP_DIR"
