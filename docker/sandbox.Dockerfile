# =============================================================================
# AnalytIQ code-execution sandbox image
# =============================================================================
# A deliberately minimal, non-root runtime for executing UNTRUSTED student code.
# It contains only a Python interpreter and the data-science libraries the
# playground/grader expose (pandas, numpy, requests) — no shell utilities, no
# build tools, no app source, no secrets.
#
# The per-run harness (services/code_runner.py) and the student code are NOT
# baked in. They are written to a throwaway host tempdir at run time and
# bind-mounted READ-ONLY at /opt/run by services/container_runner.py, which also
# applies the runtime isolation (--network none, --read-only, tmpfs, cgroup
# memory/cpu/pid caps, --cap-drop ALL, --security-opt no-new-privileges, non-root
# uid). Keeping the harness in code_runner.py means grading behaviour is
# byte-identical to the host runner — the container only changes WHERE it runs.
#
# Build (context is docker/ — the image COPYs nothing, so the app source and
# .git never reach the daemon; docker/.dockerignore empties the context):
#   docker build -f docker/sandbox.Dockerfile -t analytiq-sandbox:latest docker/
# (or `make sandbox-image`)
#
# This image is never network-exposed and runs one short-lived process per
# invocation. Rebuild it whenever the app bumps pandas/numpy so student code
# sees the same library versions as the host runner used to provide.
# =============================================================================

FROM python:3.11-slim-bookworm

# --- Interpreter hygiene -----------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# --- Data-science stack ------------------------------------------------------
# Pinned for reproducible builds; kept within the app's requirements.txt ranges
# (pandas>=2,<3 ; numpy>=1.26,<3). manylinux wheels install with no compiler,
# so no build toolchain is added to (or left in) the image.
RUN pip install --no-cache-dir \
        "pandas==2.2.3" \
        "numpy==2.1.3" \
        "requests==2.32.4" \
    && find /usr/local/lib/python3.11 -name '__pycache__' -type d -prune -exec rm -rf {} + \
    && rm -rf /root/.cache

# --- Non-root execution account ---------------------------------------------
# Fixed high uid/gid so the container never runs as root even if the runtime
# forgets --user. /opt/run is the read-only mount point for the harness+code.
RUN groupadd --gid 10001 sandbox \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin sandbox \
    && mkdir -p /opt/run \
    && chown root:root /opt/run

USER 10001:10001
WORKDIR /tmp

# No default CMD that does work — container_runner.py always supplies the exact
# `python /opt/run/<harness>.py …` argv. Fail loudly if run bare.
CMD ["python", "-c", "import sys; sys.stderr.write('sandbox image: no harness supplied\\n'); sys.exit(2)"]

LABEL org.opencontainers.image.title="analytiq-sandbox" \
      org.opencontainers.image.description="Locked-down runtime for untrusted student code execution" \
      org.opencontainers.image.source="https://github.com/adamelharouchi5-blip/AnalytIQ"
