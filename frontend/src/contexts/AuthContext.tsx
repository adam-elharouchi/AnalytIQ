/**
 * AuthContext — JWT + user session management.
 *
 * Replaces the localStorage-coupled AuthManager class in auth.js.
 * All components that need the current user or auth actions import
 * `useAuth()` from this module.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react'
import type { User } from '@/types'
import { authApi, type SignInPayload, type SignUpPayload } from '@/api/endpoints'

interface AuthState {
  user: User | null
  token: string | null
}

interface AuthContextValue extends AuthState {
  signIn: (payload: SignInPayload) => Promise<{ error: string | null; requiresReset?: boolean }>
  signUp: (payload: SignUpPayload) => Promise<{ error: string | null; pendingApproval?: boolean }>
  signOut: () => void
  isAuthenticated: boolean
}

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------

const STORAGE_TOKEN = 'authToken'
const STORAGE_REFRESH = 'refreshToken'
const STORAGE_USER = 'currentUser'

function loadStoredAuth(): AuthState {
  try {
    const token = localStorage.getItem(STORAGE_TOKEN)
    const userStr = localStorage.getItem(STORAGE_USER)
    const user = userStr ? (JSON.parse(userStr) as User) : null
    return { user, token }
  } catch {
    return { user: null, token: null }
  }
}

function saveAuth(user: User, token: string, refreshToken?: string | null) {
  localStorage.setItem(STORAGE_TOKEN, token)
  if (refreshToken) localStorage.setItem(STORAGE_REFRESH, refreshToken)
  localStorage.setItem(STORAGE_USER, JSON.stringify(user))
}

function clearAuth() {
  localStorage.removeItem(STORAGE_TOKEN)
  localStorage.removeItem(STORAGE_REFRESH)
  localStorage.removeItem(STORAGE_USER)
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>(loadStoredAuth)

  const signIn = useCallback(async (payload: SignInPayload) => {
    const { ok, data, error } = await authApi.signIn(payload)
    if (!ok || !data) return { error: error ?? 'Sign in failed' }

    if (!data.token) return { error: 'No token returned' }

    const user: User = {
      id: data.user_id ?? data.id ?? '',
      user_id: data.user_id ?? data.id ?? '',
      name: data.name,
      email: data.email,
      role: data.role,
      tenant_id: data.tenant_id,
    }

    saveAuth(user, data.token, data.refresh_token)
    setAuth({ user, token: data.token })
    return { error: null, requiresReset: data.requires_password_reset }
  }, [])

  const signUp = useCallback(async (payload: SignUpPayload) => {
    const { ok, data, error } = await authApi.signUp(payload)
    if (!ok || !data) return { error: error ?? 'Sign up failed' }

    if (data.pending_approval) {
      return { error: null, pendingApproval: true }
    }

    if (!data.token) return { error: 'No token returned' }

    const user: User = {
      id: data.user_id ?? data.id ?? '',
      user_id: data.user_id ?? data.id ?? '',
      name: data.name,
      email: data.email,
      role: data.role,
      tenant_id: data.tenant_id,
    }

    saveAuth(user, data.token, data.refresh_token)
    setAuth({ user, token: data.token })
    return { error: null, pendingApproval: false }
  }, [])

  const signOut = useCallback(() => {
    clearAuth()
    setAuth({ user: null, token: null })
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      ...auth,
      signIn,
      signUp,
      signOut,
      isAuthenticated: auth.user !== null && auth.token !== null,
    }),
    [auth, signIn, signUp, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
