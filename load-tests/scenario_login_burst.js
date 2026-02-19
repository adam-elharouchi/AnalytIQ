// k6 load test — run with: k6 run load-tests/scenario_login_burst.js
//
// Scenario: Login/signup burst — simulates many users authenticating at once.
// Each VU signs up a unique account then immediately signs in.
// Thresholds: <1% errors, p95 latency < 2s.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { getBaseUrl } from './helpers.js';

export const options = {
  stages: [
    { duration: '30s', target: 50 },  // ramp up to 50 VUs
    { duration: '60s', target: 50 },  // sustain
    { duration: '30s', target: 0 },   // ramp down
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],           // <1% errors
    http_req_duration: ['p(95)<2000'],        // p95 < 2s
  },
};

const BASE = getBaseUrl();

export default function () {
  const uid = `${__VU}_${__ITER}_${Date.now()}`;
  const email = `load_${uid}@hult.edu`;
  const password = 'Loadtest123!';
  const name = `Load User ${uid}`;

  // Sign up
  const signupRes = http.post(
    `${BASE}/api/users/signup`,
    JSON.stringify({ name, email, password }),
    { headers: { 'Content-Type': 'application/json' }, timeout: '10s' }
  );
  check(signupRes, {
    'signup 201': (r) => r.status === 201,
  });

  // Sign in immediately after
  const signinRes = http.post(
    `${BASE}/api/users/signin`,
    JSON.stringify({ email, password }),
    { headers: { 'Content-Type': 'application/json' }, timeout: '10s' }
  );
  check(signinRes, {
    'signin 200': (r) => r.status === 200,
    'token present': (r) => JSON.parse(r.body || '{}').token !== undefined,
  });

  sleep(1);
}
