// k6 shared helpers for AnalytIQ load tests
import http from 'k6/http';
import { check } from 'k6';

export function getBaseUrl() {
  return __ENV.BASE_URL || 'http://localhost:5000';
}

export function login(email, password) {
  const url = `${getBaseUrl()}/api/users/signin`;
  const res = http.post(url, JSON.stringify({ email, password }), {
    headers: { 'Content-Type': 'application/json' },
    timeout: '10s',
  });
  const ok = check(res, { 'login 200': (r) => r.status === 200 });
  if (!ok) return null;
  return JSON.parse(res.body).token;
}

export function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}
