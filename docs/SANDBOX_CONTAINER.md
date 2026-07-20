# Container sandbox for student code execution

Status: **scaffold, default OFF** — merged behind `SANDBOX_USE_CONTAINER=false`.
Requires validation on a Docker-capable host before it is enabled anywhere.

## Why

`services/code_runner.py` executes untrusted student code for two features:

- the playground **"Run"** button (`run_code`), and
- **deterministic grading** against stored test cases (`run_test_cases`).

C-1 (June 2026 audit) stripped secrets from the child's environment and pinned a
neutral working directory. But the child still runs **on the host** (the web /
Celery worker process). Its remaining defences are *in-process* and bypassable:

| Defence (host backend) | Bypass |
| --- | --- |
| import blocklist (`subprocess`, `ctypes`, …) | `os` is **not** blocked → `os.system(...)`, `os.popen(...)` |
| read-only `open()` shim | `os.open`/`os.write`, `io.FileIO` |
| `RLIMIT_AS/FSIZE/NPROC` (Linux only) | not enforced on non-Linux; per-process only |
| secret-free env | reads files on disk directly; the app source tree is reachable |
| network (**allowed** for `pd.read_csv(url)`) | SSRF to `169.254.169.254`, the DB/Redis hosts, internal services |

The container backend replaces those in-process shims with **kernel-enforced**
isolation and moves execution off the host.

## What the container backend does

When `SANDBOX_USE_CONTAINER=true`, each Python invocation runs via
`services/container_runner.py`, which writes the (unchanged) harness + student
code to a throwaway tempdir, bind-mounts it **read-only** into an ephemeral
container, and runs:

```
docker run --rm -i
  --name aq-sbx-<rand>
  --network none                      # no internal net / cloud metadata / exfil
  --read-only                         # immutable rootfs
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m
  --memory 512m --memory-swap 512m    # real-RAM cap, no swap
  --cpus 1.0
  --pids-limit 64                     # fork-bomb ceiling
  --cap-drop ALL
  --security-opt no-new-privileges
  --user 10001:10001                  # non-root
  [--runtime runsc]                   # optional gVisor kernel isolation
  -v <tmpdir>:/opt/run:ro analytiq-sandbox:latest \
  python /opt/run/harness.py <args…>
```

The harness stays in `code_runner.py`, so **grading output is byte-identical** to
the host backend — only *where* it runs changes.

### Fail-closed

If the flag is on but the container CLI/daemon is unavailable, execution returns
an error (`run_code` → "temporarily unavailable"; `run_test_cases` → 0
correctness). It **never** silently falls back to the host runner, so turning the
flag on can't give a false sense of isolation.

### Scope / known gaps

- **Python only.** JS/R/Java grading still use the host subprocess (the sandbox
  image ships only a Python runtime). Extend the image (or add per-language
  images) before relying on the container backend for those languages.
- **Not usable on Render's standard web/worker dynos** — they cannot run Docker.
  See "Deployment topology" below.

## Trade-off: `pd.read_csv(url)` and network

The playground historically allows network so `pd.read_csv(url)` /
`requests.get(url)` work like a Colab cell. That same network is an SSRF/exfil
surface. The container backend defaults **both** grading and Run to
`--network none`.

To restore public-internet fetches for the Run playground **safely**, set
`SANDBOX_CONTAINER_NETWORK_RUN` to a purpose-built Docker network that:

- **blocks** RFC1918 (`10/8`, `172.16/12`, `192.168/16`), `127/8`, `169.254/16`
  (link-local + cloud metadata), and the DB/Redis hosts, but
- **allows** outbound public HTTPS.

Do **not** use `--network bridge` in production — it grants unrestricted egress
to the internal network. `config.config_security_warnings()` warns if you do.
Grading stays on `--network none` regardless (it is deterministic and needs no
network).

## Configuration (all env vars, defaults preserve current behaviour)

| Var | Default | Meaning |
| --- | --- | --- |
| `SANDBOX_USE_CONTAINER` | `False` | Master switch. Off = host backend. |
| `SANDBOX_CONTAINER_IMAGE` | `analytiq-sandbox:latest` | Image tag to run. |
| `SANDBOX_CONTAINER_CLI` | `docker` | CLI (`docker`/`podman`). |
| `SANDBOX_CONTAINER_RUNTIME` | `` (daemon default) | e.g. `runsc` for gVisor. |
| `SANDBOX_CONTAINER_NETWORK_TEST` | `none` | `--network` for grading. |
| `SANDBOX_CONTAINER_NETWORK_RUN` | `none` | `--network` for the Run playground. |
| `SANDBOX_CONTAINER_MEMORY` | `512m` | cgroup RAM cap (= memory-swap). |
| `SANDBOX_CONTAINER_CPUS` | `1.0` | cgroup CPU cap. |
| `SANDBOX_CONTAINER_PIDS` | `64` | `--pids-limit`. |
| `SANDBOX_CONTAINER_TMPFS_SIZE` | `64m` | writable `/tmp` tmpfs size. |
| `SANDBOX_CONTAINER_STARTUP_GRACE` | `10` | seconds added to per-run timeout for spin-up. |

## Build the image

```
make sandbox-image
# or:
docker build -f docker/sandbox.Dockerfile -t analytiq-sandbox:latest docker/
```

Rebuild whenever `requirements.txt` bumps `pandas`/`numpy` so student code sees
the same library versions the host runner used to provide.

## Deployment topology (important)

Render's standard web/worker services run inside their own containers and
**cannot run Docker** (no daemon, not privileged). `SANDBOX_USE_CONTAINER=true`
will fail closed there. Pick one:

1. **Dedicated Docker host / VM** (EC2, GCE, Fly.io machine, self-managed) that
   runs the app *and* has a Docker daemon. Simplest; add `runsc` for gVisor.
2. **Remote sandbox microservice** — a small service on Docker/Firecracker
   infra that exposes an HTTP "execute" endpoint; the app POSTs code to it.
   Best isolation + scaling, more infra. (Future: a `SANDBOX_REMOTE_URL`
   backend alongside the container backend.)
3. **Managed execution API** (e.g. Piston/Judge0-style) if policy allows a third
   party to run student code.

This scaffold implements topology (1) directly and lays the seam for (2).

## Staging validation checklist

Run on a Docker-capable staging host before enabling anywhere:

- [ ] `make sandbox-image` builds; `docker images | grep analytiq-sandbox`.
- [ ] Set `SANDBOX_USE_CONTAINER=true`; restart app.
- [ ] Playground Run: `print(2+2)` → `4`. Grading: a known-good solution scores
      as it did on the host backend (compare a few exercises).
- [ ] **Isolation smoke tests** (all should be blocked / error, none should
      succeed):
  - [ ] `import os; os.system('id')` — no host command runs.
  - [ ] `open('/etc/passwd').read()` then a **write** attempt — rootfs read-only.
  - [ ] `import socket; socket.create_connection(('169.254.169.254',80),2)` —
        blocked by `--network none`.
  - [ ] `import urllib.request; urllib.request.urlopen('http://<internal-db-host>')`
        — blocked.
  - [ ] fork bomb (`import os; [os.fork() for _ in range(1000)]`) — capped by
        `--pids-limit`.
  - [ ] `x = ' ' * (2*1024*1024*1024)` — OOM-killed by `--memory`, not the host.
  - [ ] `while True: pass` — killed at the timeout; `docker ps -a` shows no
        lingering `aq-sbx-*` container.
- [ ] Decide network policy for Run: keep `none`, or point
      `SANDBOX_CONTAINER_NETWORK_RUN` at an egress-filtered network and re-verify
      `pd.read_csv('https://…')` works **and** the internal/metadata targets
      above still fail.
- [ ] (Recommended) install gVisor and set `SANDBOX_CONTAINER_RUNTIME=runsc`;
      re-run the smoke tests.
- [ ] Load check: concurrent submissions don't exhaust host resources (container
      caps + a concurrency limit upstream).

## Rollback

Set `SANDBOX_USE_CONTAINER=false` (or unset) and restart. The host backend —
today's exact behaviour — resumes immediately. No redeploy required.
