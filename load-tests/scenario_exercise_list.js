// k6 load test — run with:
//   CHAPTER_ID=<uuid> PROF_EMAIL=prof@hult.edu PROF_PASS=password k6 run load-tests/scenario_exercise_list.js
//
// Scenario: Read-heavy exercise list — simulates students browsing exercises concurrently.
// Requires a pre-existing chapter with ID passed via CHAPTER_ID env var.
// Thresholds: <0.5% errors, p95 < 500ms, p99 < 1s.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { getBaseUrl, login, authHeaders } from './helpers.js';

export const options = {
  vus: 100,
  duration: '2m',
  thresholds: {
    http_req_failed: ['rate<0.005'],     // <0.5% errors
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
  },
};

const BASE = getBaseUrl();
const CHAPTER_ID = __ENV.CHAPTER_ID;
const PROF_EMAIL = __ENV.PROF_EMAIL;
const PROF_PASS = __ENV.PROF_PASS;

// setup() runs once before the test, returns data shared with all VUs
export function setup() {
  if (!CHAPTER_ID) {
    throw new Error('CHAPTER_ID env var is required. Pass an existing chapter UUID.');
  }
  const token = login(PROF_EMAIL, PROF_PASS);
  if (!token) {
    throw new Error('Login failed — check PROF_EMAIL and PROF_PASS env vars.');
  }
  return { token, chapterId: CHAPTER_ID };
}

export default function (data) {
  const res = http.get(
    `${BASE}/api/chapters/${data.chapterId}/exercises`,
    { headers: authHeaders(data.token), timeout: '5s' }
  );
  check(res, {
    'exercises 200': (r) => r.status === 200,
    'exercises array present': (r) => Array.isArray((JSON.parse(r.body || '{}').exercises)),
  });
  sleep(0.5);
}
