/**
 * Typed API client — mirrors the behaviour of the legacy api-client.js.
 *
 * All methods resolve to { ok, data, error } so callers never need to
 * catch network errors manually.
 *
 * Global 401 interceptor clears auth storage and redirects to /login.
 */

const API_BASE = '/api'

export interface ApiResult<T = unknown> {
  ok: boolean
  data: T | null
  error: string | null
  status: number
}

function getToken(): string | null {
  return localStorage.getItem('authToken')
}

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

  Object.assign(headers, extraHeaders ?? {})

  const init: RequestInit = { method, headers }
  if (body !== undefined) {
    init.body = body instanceof FormData ? body : JSON.stringify(body)
  }

  try {
    const res = await fetch(API_BASE + path, init)

    // 401 — session expired; redirect to login.
    // Skip auth endpoints: a 401 from signin/signup means wrong credentials, not expiry.
    const isAuthEndpoint = path === '/users/signin' || path === '/users/signup'
    if (res.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('currentUser')
      // Stay inside the React app — /login is now a React route.
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
