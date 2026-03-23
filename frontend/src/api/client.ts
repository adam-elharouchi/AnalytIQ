/**
 * Typed API client — mirrors the behaviour of the legacy api-client.js.
 *
 * All methods resolve to { ok, data, error } so callers never need to
 * catch network errors manually.
 *
 * Global 401 interceptor clears auth storage and redirects to /login.
 */

const API_BASE = '/api'

// ── CSRF token (Double Submit pattern) ───────────────────────────────────────
// Flask-WTF validates X-CSRFToken against the server-side session token.
// We fetch it once lazily before the first mutating request and cache it.
let _csrfToken: string | null = null

async function getCsrfToken(): Promise<string> {
  if (_csrfToken) return _csrfToken
  try {
    const res = await fetch(API_BASE + '/csrf-token', { credentials: 'same-origin' })
    const data = await res.json()
    _csrfToken = (data.csrfToken as string) ?? ''
  } catch {
    _csrfToken = ''
  }
  return _csrfToken
}

export interface ApiResult<T = unknown> {
  ok: boolean
  data: T | null
  error: string | null
  status: number
}

function getToken(): string | null {
  return localStorage.getItem('authToken')
}

const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
): Promise<ApiResult<T>> {
  const headers: Record<string, string> = {}

  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  if (body !== undefined && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  // Include CSRF token on all state-changing requests
  if (MUTATING_METHODS.has(method.toUpperCase())) {
    const csrf = await getCsrfToken()
    if (csrf) headers['X-CSRFToken'] = csrf
  }

  Object.assign(headers, extraHeaders ?? {})

  const init: RequestInit = { method, headers, credentials: 'same-origin' }
  if (body !== undefined) {
    init.body = body instanceof FormData ? body : JSON.stringify(body)
  }

  try {
    const res = await fetch(API_BASE + path, init)

    // If we get a CSRF error, clear the cached token and retry once
    if (res.status === 400) {
      const ct = res.headers.get('content-type') ?? ''
      if (ct.includes('application/json')) {
        const errData = await res.json()
        if (typeof errData?.error === 'string' && errData.error.toLowerCase().includes('csrf')) {
          _csrfToken = null
          const retryHeaders = { ...headers }
          const newCsrf = await getCsrfToken()
          if (newCsrf) retryHeaders['X-CSRFToken'] = newCsrf
          const retryRes = await fetch(API_BASE + path, { ...init, headers: retryHeaders })
          const retryData = retryRes.ok ? (await retryRes.json() as T) : null
          return {
            ok: retryRes.ok,
            data: retryData,
            error: retryRes.ok ? null : ((retryData as Record<string, string> | null)?.error ?? `HTTP ${retryRes.status}`),
            status: retryRes.status,
          }
        }
      }
    }

    // 401 — session expired; redirect to login.
    // Skip auth endpoints: a 401 from signin/signup means wrong credentials, not expiry.
    const isAuthEndpoint = path === '/users/signin' || path === '/users/signup'
    if (res.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('currentUser')
      window.location.replace('/login')
      return { ok: false, data: null, error: 'Session expired', status: 401 }
    }

    let data: T | null = null
    const ct = res.headers.get('content-type') ?? ''
    if (ct.includes('application/json')) {
      try {
        data = (await res.json()) as T
      } catch {
        // ignore malformed JSON
      }
    }

    const error = res.ok
      ? null
      : ((data as Record<string, string> | null)?.error ?? `HTTP ${res.status}`)

    return { ok: res.ok, data, error, status: res.status }
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Network error'
    return { ok: false, data: null, error: message, status: 0 }
  }
}

export const apiClient = {
  get: <T>(path: string, headers?: Record<string, string>) =>
    request<T>('GET', path, undefined, headers),

  post: <T>(path: string, body?: unknown, headers?: Record<string, string>) =>
    request<T>('POST', path, body, headers),

  put: <T>(path: string, body?: unknown, headers?: Record<string, string>) =>
    request<T>('PUT', path, body, headers),

  del: <T>(path: string, headers?: Record<string, string>) =>
    request<T>('DELETE', path, undefined, headers),

  upload: <T>(path: string, formData: FormData, headers?: Record<string, string>) =>
    request<T>('POST', path, formData, headers),
}
