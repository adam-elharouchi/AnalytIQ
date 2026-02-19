# Load Tests (k6)

k6 load tests for AnalytIQ covering three scenarios.

## Prerequisites

### Install k6
```bash
# macOS
brew install k6

# Ubuntu/Debian
sudo apt-get install k6

# Windows (Chocolatey)
choco install k6

# Or via Docker
docker pull grafana/k6
```

### Start the App
```bash
# Run the app in production-like mode (not testing mode)
python app.py
```

The app should be reachable at `http://localhost:5000`.
Override with `BASE_URL` env var for remote targets.

## Scenarios

### 1. Login Burst (`scenario_login_burst.js`)
Simulates 50 concurrent users signing up and logging in.

```bash
k6 run load-tests/scenario_login_burst.js

# Against a remote server
BASE_URL=https://myanalytiq.org k6 run load-tests/scenario_login_burst.js
```

**Thresholds:** <1% error rate, p95 < 2s

---

### 2. Exercise List — Read Heavy (`scenario_exercise_list.js`)
Simulates 100 students concurrently fetching exercises from the same chapter.

Requires a pre-existing chapter. Get a chapter UUID from your DB or create one via the app first.

```bash
CHAPTER_ID=<chapter-uuid> \
PROF_EMAIL=prof@hult.edu \
PROF_PASS=yourpassword \
k6 run load-tests/scenario_exercise_list.js
```

**Thresholds:** <0.5% error rate, p95 < 500ms, p99 < 1s

---

### 3. Concurrent AI Chat (`scenario_ai_chat.js`)
Simulates 10 users sending AI chat messages with realistic pacing (5–10s between messages).

> **Note:** This hits the real Gemini API. Keep VU count low to avoid rate limits.
> Use `--vus 2 --duration 30s` for a smoke test.

```bash
PROF_EMAIL=prof@hult.edu \
PROF_PASS=yourpassword \
k6 run load-tests/scenario_ai_chat.js

# Smoke test (2 VUs, 30s)
PROF_EMAIL=prof@hult.edu PROF_PASS=yourpassword \
k6 run load-tests/scenario_ai_chat.js --vus 2 --duration 30s
```

**Thresholds:** <5% error rate, p95 < 10s

---

## Interpreting Results

```
✓ login 200        ← check passed for all requests
✗ signin 200       ← check failed (shown in red with failure count)

http_req_duration: avg=123ms  p(95)=450ms  p(99)=980ms
http_req_failed:   0.42%      ← must be below threshold
```

- **`http_req_failed`** — non-2xx or network error rate. Threshold failure = system is broken under load.
- **`p(95)`** — 95th percentile latency. 95% of requests complete within this time.
- **`checks`** — application-level assertions (token present, array returned, etc.).

## Run via Docker (no local install)

```bash
docker run --rm -i \
  -e BASE_URL=http://host.docker.internal:5000 \
  grafana/k6 run - < load-tests/scenario_login_burst.js
```
