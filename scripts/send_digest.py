#!/usr/bin/env python3
"""Sends reports/ADAM_DAILY.md to Adam. Deterministic. Recipient is HARDCODED —
changing it requires Adam editing this file himself (guardrail #1 exception).

The digest file stays markdown (other agents read it). The EMAIL does not: raw
`**bold**` and `## headings` render as literal punctuation in a mail client, so
this sends multipart/alternative — an HTML part that actually renders, and a
plain-text part with the markers stripped for anything that won't show HTML.

Conversion is stdlib-only on purpose. This runs from launchd under the system
python3, where installing a markdown package is fragile; a self-contained
converter keeps the job dependency-free and deterministic.
"""
import os, re, html, smtplib, ssl, sys, datetime, pathlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

RECIPIENT = "adamelharouchi5@gmail.com"   # HARDCODED. Agents may not modify this line.

# --- styling -----------------------------------------------------------------
# Inline styles only: Gmail and Outlook strip or partially honour <style> blocks.
S = {
    "body": "margin:0;padding:24px 16px;background:#f5f6f8;"
            "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;"
            "font-size:15px;line-height:1.6;color:#1f2328;",
    "card": "max-width:720px;margin:0 auto;background:#ffffff;border:1px solid #d8dce0;"
            "border-radius:10px;padding:28px 32px;",
    "h1": "margin:0 0 4px;font-size:23px;line-height:1.3;font-weight:700;color:#0d1117;",
    "h2": "margin:30px 0 10px;padding-bottom:7px;font-size:17px;font-weight:700;color:#0d1117;"
          "border-bottom:2px solid #e6e8eb;",
    "h3": "margin:22px 0 8px;font-size:15px;font-weight:700;color:#0d1117;",
    "p": "margin:0 0 12px;",
    "ul": "margin:0 0 12px;padding-left:22px;",
    "ol": "margin:0 0 12px;padding-left:22px;",
    "li": "margin:0 0 7px;",
    "code": "background:#f0f2f4;border:1px solid #e0e3e6;border-radius:4px;padding:1px 5px;"
            "font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px;"
            "color:#24292f;",
    "a": "color:#0969da;text-decoration:underline;",
    "hr": "border:0;border-top:1px solid #e6e8eb;margin:22px 0;",
    "quote": "margin:0 0 12px;padding:8px 14px;border-left:3px solid #d0d7de;background:#f8f9fa;color:#57606a;",
    "cta": "margin:0 0 24px;padding:16px 18px;background:#e2f0ee;border:1px solid #1a6b66;"
           "border-radius:8px;",
    "ctalabel": "margin:0 0 8px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;"
                "font-weight:700;color:#1a6b66;",
    "ctabtn": "display:inline-block;padding:10px 18px;background:#1a6b66;color:#ffffff;"
              "border-radius:6px;font-weight:600;font-size:15px;text-decoration:none;",
    "ctanote": "margin:10px 0 0;font-size:13px;color:#42565a;",
    "ctamiss": "margin:0 0 24px;padding:12px 16px;background:#f8f9fa;border:1px dashed #d0d7de;"
               "border-radius:8px;font-size:13px;color:#57606a;",
    "table": "border-collapse:collapse;width:100%;margin:0 0 14px;font-size:14px;",
    "th": "border:1px solid #d8dce0;padding:7px 10px;background:#f0f2f4;text-align:left;font-weight:600;",
    "td": "border:1px solid #d8dce0;padding:7px 10px;vertical-align:top;",
    "foot": "max-width:720px;margin:14px auto 0;font-size:12px;color:#8b949e;text-align:center;",
}

_CODE_TOKEN = "\x00CODE%d\x00"


def _inline(text: str) -> str:
    """Inline markdown -> HTML. Input is raw; output is escaped and marked up."""
    # Pull code spans out first so their contents never get bold/italic treatment.
    spans: list[str] = []

    def _stash(m):
        spans.append(m.group(1))
        return _CODE_TOKEN % (len(spans) - 1)

    text = re.sub(r"`([^`]+)`", _stash, text)
    text = html.escape(text, quote=False)
    # [label](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}" style="{S["a"]}">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)          # bold
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", text)    # italic
    for i, raw in enumerate(spans):
        text = text.replace(
            _CODE_TOKEN % i,
            f'<code style="{S["code"]}">{html.escape(raw, quote=False)}</code>',
        )
    return text


def _plain_inline(text: str) -> str:
    """Strip markdown markers, keeping the words readable."""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text)
    return text


def md_to_html(md: str, banner: str = "") -> str:
    out: list[str] = []
    stack: list[str] = []          # open list tags, innermost last
    para: list[str] = []
    table: list[str] = []

    def close_lists(to_depth=0):
        while len(stack) > to_depth:
            out.append(f"</{stack.pop()}>")

    def flush_para():
        if para:
            out.append(f'<p style="{S["p"]}">{" ".join(para)}</p>')
            para.clear()

    def flush_table():
        if not table:
            return
        rows = [r.strip().strip("|").split("|") for r in table]
        rows = [[c.strip() for c in r] for r in rows]
        # Drop the |---|---| separator row if present.
        body = [r for r in rows[1:] if not all(set(c) <= set("-: ") and c for c in r)]
        out.append(f'<table style="{S["table"]}"><tr>')
        for c in rows[0]:
            out.append(f'<th style="{S["th"]}">{_inline(c)}</th>')
        out.append("</tr>")
        for r in body:
            out.append("<tr>")
            for c in r:
                out.append(f'<td style="{S["td"]}">{_inline(c)}</td>')
            out.append("</tr>")
        out.append("</table>")
        table.clear()

    for line in md.splitlines():
        if line.lstrip().startswith("|") and line.count("|") >= 2:
            flush_para(); close_lists()
            table.append(line)
            continue
        flush_table()

        if not line.strip():
            flush_para(); close_lists()
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush_para(); close_lists()
            lvl = min(len(m.group(1)), 3)
            out.append(f'<h{lvl} style="{S[f"h{lvl}"]}">{_inline(m.group(2))}</h{lvl}>')
            continue

        if re.match(r"^\s*([-*_])\1{2,}\s*$", line):
            flush_para(); close_lists()
            out.append(f'<hr style="{S["hr"]}">')
            continue

        if line.lstrip().startswith(">"):
            flush_para(); close_lists()
            out.append(f'<div style="{S["quote"]}">{_inline(line.lstrip()[1:].strip())}</div>')
            continue

        m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
        if m:
            flush_para()
            indent, marker, content = m.group(1), m.group(2), m.group(3)
            tag = "ul" if marker in "-*+" else "ol"
            depth = len(indent) // 2 + 1          # the digest nests with 2 spaces
            while len(stack) > depth:
                out.append(f"</{stack.pop()}>")
            if len(stack) < depth:
                while len(stack) < depth:
                    stack.append(tag)
                    out.append(f'<{tag} style="{S[tag]}">')
            elif stack and stack[-1] != tag:
                out.append(f"</{stack.pop()}>")
                stack.append(tag)
                out.append(f'<{tag} style="{S[tag]}">')
            out.append(f'<li style="{S["li"]}">{_inline(content)}</li>')
            continue

        # Continuation of a list item, or plain paragraph text.
        if stack:
            out.append(f'<div style="margin:0 0 7px;">{_inline(line.strip())}</div>')
        else:
            para.append(_inline(line.strip()))

    flush_table(); flush_para(); close_lists()
    inner = "\n".join(out)
    return (
        f'<html><body style="{S["body"]}">'
        f'<div style="{S["card"]}">{banner}{inner}</div>'
        f'<div style="{S["foot"]}">AnalytIQ orchestrator · generated from reports/ADAM_DAILY.md</div>'
        f"</body></html>"
    )


def md_to_text(md: str, banner: str = "") -> str:
    lines: list[str] = [banner] if banner else []
    for line in md.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            title = _plain_inline(m.group(2))
            if len(m.group(1)) == 1:
                lines += ["", title, "=" * len(title)]
            else:
                lines += ["", title, "-" * len(title)]
            continue
        if re.match(r"^\s*([-*_])\1{2,}\s*$", line):
            lines.append("-" * 60)
            continue
        m = re.match(r"^(\s*)([-*+])\s+(.*)$", line)
        if m:
            lines.append(f"{m.group(1)}  • {_plain_inline(m.group(3))}")
            continue
        m = re.match(r"^(\s*)(\d+[.)])\s+(.*)$", line)
        if m:
            lines.append(f"{m.group(1)}  {m.group(2)} {_plain_inline(m.group(3))}")
            continue
        lines.append(_plain_inline(line))
    return "\n".join(lines).strip() + "\n"


# --- decision sheet link ------------------------------------------------------
# Adam answers the day's decisions on an interactive sheet rather than by replying
# in prose (his standing request, 2026-08-12: selecting options and submitting in
# one pass gets every decision answered in a single round trip). The orchestrator
# publishes that sheet as an Artifact and drops the URL in reports/DECISION_SHEET_URL;
# this module only reads it. Nothing here can publish — that needs the Claude Code
# session, which is why the URL arrives via a file rather than being generated below.

DECISION_URL_FILE = "reports/DECISION_SHEET_URL"
_URL_RE = re.compile(r"^https://[^\s<>\"]+$")


def decision_sheet_url(repo: pathlib.Path, today: datetime.date) -> tuple:
    """Return (url, problem). Exactly one of the two is non-empty.

    Same freshness discipline as the digest itself, and for the same reason: a
    stale sheet is worse than no sheet. Yesterday's link still resolves and still
    looks current, so Adam would answer yesterday's decisions believing they were
    today's — a silent wrong answer instead of a visible gap.

    DECISION_SHEET_URL in the environment overrides the file and skips the
    freshness check, so a hand-run `python3 scripts/send_digest.py` can attach a
    sheet published moments earlier.
    """
    env = os.environ.get("DECISION_SHEET_URL", "").strip()
    if env:
        if not _URL_RE.match(env):
            return "", "DECISION_SHEET_URL is set but is not a plain https URL — ignoring it."
        return env, ""

    path = repo / DECISION_URL_FILE
    if not path.exists():
        return "", f"No decision sheet was published for today ({DECISION_URL_FILE} is missing)."

    written = datetime.date.fromtimestamp(path.stat().st_mtime)
    if written != today:
        return "", (
            f"The decision sheet on file is from {written}, not today — not linking it, "
            "because a stale sheet lists the wrong decisions."
        )

    url = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            url = line
            break
    if not _URL_RE.match(url or ""):
        return "", f"{DECISION_URL_FILE} does not contain a plain https URL — not linking it."
    return url, ""


def decision_banner_html(url: str, problem: str) -> str:
    if problem:
        return f'<div style="{S["ctamiss"]}">{html.escape(problem)}</div>'
    safe = html.escape(url, quote=True)
    return (
        f'<div style="{S["cta"]}">'
        f'<div style="{S["ctalabel"]}">Decisions needed from you</div>'
        f'<a href="{safe}" style="{S["ctabtn"]}">Open today\'s decision sheet &rarr;</a>'
        f'<p style="{S["ctanote"]}">Every open decision with its real options, in one page. '
        f'Pick, add notes, then submit — it copies your answers for Claude to act on.</p>'
        f"</div>"
    )


def decision_banner_text(url: str, problem: str) -> str:
    if problem:
        return f"[decision sheet] {problem}\n"
    return (
        "DECISIONS NEEDED FROM YOU — answer them here:\n"
        f"  {url}\n"
        "Every open decision with its real options. Pick, add notes, submit.\n"
    )


# --- send --------------------------------------------------------------------
def _credentials() -> tuple:
    try:
        return os.environ["DIGEST_SMTP_USER"], os.environ["DIGEST_SMTP_PASS"]
    except KeyError as missing:
        sys.exit(f"{missing} not set — is ~/.analytiq_env present and sourced?")


def _send(subject: str, plain: str, html_body: str = "") -> None:
    user, pw = _credentials()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = RECIPIENT
    # Least-capable part first: clients render the last part they understand.
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    # timeout is required: a hung TLS handshake with no timeout blocks the launchd
    # job forever, and later triggers then stack processes behind it.
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=30) as s:
        s.login(user, pw)
        s.sendmail(user, [RECIPIENT], msg.as_string())


def send_failure_notice(reason: str, log_path: str = "") -> None:
    """Mail Adam that today's cycle failed and produced no digest.

    Without this, a failed orchestrator run is INDISTINGUISHABLE from a quiet day:
    the freshness gate below correctly suppresses the stale digest, and the result
    is an empty inbox. Aug 10-11 2026 both failed that way and went unnoticed for
    two days. A missing digest must arrive as a message, not as silence.

    Deliberately NOT gated on freshness, and deliberately capped at one notice per
    day: all three triggers failing would otherwise send three identical emails,
    and the catch-up design expects early attempts to fail. First failure of the
    day mails; later ones only log. A later success sends the real digest, which
    supersedes the notice on its own.
    """
    today = datetime.date.today()
    repo = pathlib.Path(__file__).resolve().parent.parent
    notified = repo / "reports" / "cron" / f".notified-{today:%Y-%m-%d}"
    if notified.exists():
        print("Failure notice already sent today — not repeating.")
        return

    tail = ""
    if log_path and pathlib.Path(log_path).exists():
        lines = pathlib.Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "\n".join(lines[-25:])

    body = (
        f"AnalytIQ daily cycle FAILED on {today:%A %B %d, %Y}.\n"
        f"No digest was sent — reports/ADAM_DAILY.md was not regenerated.\n\n"
        f"Reason: {reason}\n\n"
        f"The cycle retries automatically at the next trigger (08:00 / 13:00 / 19:00 local).\n"
        f"To run it by hand now:\n"
        f"    cd {repo}\n"
        f"    FORCE=1 ./scripts/daily_cycle.sh\n"
    )
    if tail:
        body += f"\n--- last 25 lines of {log_path} ---\n{tail}\n"

    _send(f"AnalytIQ Daily — {today:%b %d} — CYCLE FAILED, no digest", body)
    # Stamp only after a confirmed send, so an SMTP failure retries at the next trigger.
    notified.parent.mkdir(parents=True, exist_ok=True)
    notified.touch()
    print("Failure notice sent.")


def main() -> None:
    if "--failure-notice" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--failure-notice"]
        reason = args[0] if args else "orchestrator run failed (no reason given)"
        send_failure_notice(reason, args[1] if len(args) > 1 else "")
        return

    repo = pathlib.Path(__file__).resolve().parent.parent
    digest = repo / "reports" / "ADAM_DAILY.md"
    if not digest.exists():
        sys.exit("No ADAM_DAILY.md found — orchestrator run likely failed.")

# Freshness gate. Nothing ever deletes ADAM_DAILY.md, so without this check a
# failed orchestrator run would re-send YESTERDAY's brief under today's subject
# line — and daily_cycle.sh would read the success and stamp the day complete,
# suppressing its own 13:00/19:00 retries.
    today = datetime.date.today()
    written = datetime.date.fromtimestamp(digest.stat().st_mtime)
    if written != today:
        sys.exit(
            f"ADAM_DAILY.md is stale (written {written}, today is {today}) — refusing "
            "to send. The orchestrator run failed; the next trigger will retry."
        )

    md = digest.read_text(encoding="utf-8")
    url, problem = decision_sheet_url(repo, today)
    if problem:
        # Loud in the log, muted in the email: a missing sheet is an orchestrator
        # bug worth fixing, not something Adam should have to act on.
        print(f"WARNING: no decision sheet linked — {problem}")
    _send(
        f"AnalytIQ Daily — {today:%b %d} — agents' work + YOUR tasks",
        md_to_text(md, decision_banner_text(url, problem)),
        md_to_html(md, decision_banner_html(url, problem)),
    )
    print(f"Digest sent{' with decision sheet ' + url if url else ' (no decision sheet)'}.")


if __name__ == "__main__":
    main()
