// k6 load test — run with:
//   PROF_EMAIL=prof@hult.edu PROF_PASS=password k6 run load-tests/scenario_ai_chat.js
//
// Scenario: Concurrent AI chat — the most expensive endpoint.
// Ramps to 10 VUs, each sending a short message every 5-10s.
// Thresholds: <5% errors (AI can have occasional failures), p95 < 10s.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import { getBaseUrl, login, authHeaders } from './helpers.js';

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // ramp up
    { duration: '2m',  target: 10 },   // sustain
    { duration: '15s', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],        // <5% errors (Gemini can rate-limit)
    http_req_duration: ['p(95)<10000'],    // p95 < 10s
  },
};

const BASE = getBaseUrl();
const PROF_EMAIL = __ENV.PROF_EMAIL;
const PROF_PASS = __ENV.PROF_PASS;

export function setup() {
  const token = login(PROF_EMAIL, PROF_PASS);
  if (!token) {
    throw new Error('Login failed — check PROF_EMAIL and PROF_PASS env vars.');
  }
  return { token };
}

const QUESTIONS = [
  'What is a pandas DataFrame in one sentence?',
  'Explain a Python list comprehension briefly.',
  'What does the zip() function do?',
  'What is the difference between a list and a tuple?',
  'How does a dictionary differ from a set in Python?',
];

export default function (data) {
  const question = QUESTIONS[__VU % QUESTIONS.length];
  const payload = {
    contents: [{ role: 'user', parts: [{ text: question }] }],
    model: 'gemini-2.0-flash',
  };

  const res = http.post(
    `${BASE}/api/ai/chat`,
    JSON.stringify(payload),
    { headers: authHeaders(data.token), timeout: '30s' }
  );

  check(res, {
    'ai chat 200': (r) => r.status === 200,
    'response has content': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.candidates !== undefined || body.text !== undefined || body.response !== undefined;
      } catch {
        return false;
      }
    },
  });

  // Realistic think time between messages
  sleep(randomIntBetween(5, 10));
}
