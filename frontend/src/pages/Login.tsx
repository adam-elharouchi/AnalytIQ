/**
 * Login page — sign in + sign up tabs.
 * Migrated from auth.js + login.html.
 */

import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { authApi } from '@/api/endpoints'

type Tab = 'signin' | 'signup'

export default function Login() {
  const { signIn, signUp, isAuthenticated, user } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const reason = searchParams.get('reason')

  // If already authenticated, redirect immediately
  if (isAuthenticated && user) {
    navigate(getDefaultRedirect(user.role), { replace: true })
  }

  const [tab, setTab] = useState<Tab>('signin')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Sign-in form state
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  // Sign-up form state
  const [name, setName] = useState('')
  const [signupEmail, setSignupEmail] = useState('')
  const [signupPassword, setSignupPassword] = useState('')

  // Forgot password
  const [showForgot, setShowForgot] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')

  async function handleSignIn(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const { error, requiresReset } = await signIn({ email, password })
    setLoading(false)

    if (error) {
      setError(error)
      return
    }

    if (requiresReset) {
      navigate('/reset-password')
      return
    }

    // Decode stored role for redirect
    const stored = localStorage.getItem('currentUser')
    const role = stored ? (JSON.parse(stored) as { role: string }).role : 'student'
    navigate(getDefaultRedirect(role), { replace: true })
  }

  async function handleSignUp(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const { error, pendingApproval } = await signUp({
      name,
      email: signupEmail,
      password: signupPassword,
    })
    setLoading(false)

    if (error) {
      setError(error)
      return
    }

    if (pendingApproval) {
      setSuccess(
        'Account created. An administrator will review your request before you can sign in.',
      )
      return
    }

    const stored = localStorage.getItem('currentUser')
    const role = stored ? (JSON.parse(stored) as { role: string }).role : 'student'
    navigate(getDefaultRedirect(role), { replace: true })
  }

  async function handleForgotPassword(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const { ok, error } = await authApi.forgotPassword(forgotEmail)
    setLoading(false)

    if (!ok) {
      setError(error ?? 'Failed to send reset email')
      return
    }

    setSuccess('If an account exists with that email, password reset instructions have been sent.')
    setShowForgot(false)
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-header">
          <Link to="/" className="auth-brand">
            <span>Analyt</span><span className="brand-accent">IQ</span>
          </Link>
          <p className="auth-tagline">AI-powered learning platform</p>
        </div>

        {reason === 'session_expired' && (
          <div className="alert alert-warning">Your session has expired. Please sign in again.</div>
        )}

        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {!showForgot ? (
          <>
            <div className="auth-tabs">
              <button
                className={`auth-tab ${tab === 'signin' ? 'active' : ''}`}
                onClick={() => { setTab('signin'); setError(null) }}
              >
                Sign In
              </button>
              <button
                className={`auth-tab ${tab === 'signup' ? 'active' : ''}`}
                onClick={() => { setTab('signup'); setError(null) }}
              >
                Sign Up
              </button>
            </div>

            {tab === 'signin' ? (
              <form onSubmit={handleSignIn} className="auth-form">
                <div className="form-group">
                  <label htmlFor="email">Email</label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="you@example.com"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="password">Password</label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    placeholder="••••••••"
                  />
                </div>

                <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
                  {loading ? 'Signing in…' : 'Sign In'}
                </button>

                <button
                  type="button"
                  className="btn-link"
                  onClick={() => { setShowForgot(true); setError(null) }}
                >
                  Forgot your password?
                </button>
              </form>
            ) : (
              <form onSubmit={handleSignUp} className="auth-form">
                <div className="form-group">
                  <label htmlFor="signup-name">Full Name</label>
                  <input
                    id="signup-name"
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    required
                    placeholder="Your name"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="signup-email">Email</label>
                  <input
                    id="signup-email"
                    type="email"
                    value={signupEmail}
                    onChange={e => setSignupEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="you@example.com"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="signup-password">Password</label>
                  <input
                    id="signup-password"
                    type="password"
                    value={signupPassword}
                    onChange={e => setSignupPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    placeholder="Min 8 characters"
                    minLength={8}
                  />
                </div>

                <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
                  {loading ? 'Creating account…' : 'Create Account'}
                </button>
              </form>
            )}
          </>
        ) : (
          <form onSubmit={handleForgotPassword} className="auth-form">
            <h2 className="auth-subtitle">Reset Password</h2>
            <p className="auth-hint">
              Enter your email and we'll send you a link to reset your password.
            </p>

            <div className="form-group">
              <label htmlFor="forgot-email">Email</label>
              <input
                id="forgot-email"
                type="email"
                value={forgotEmail}
                onChange={e => setForgotEmail(e.target.value)}
                required
                placeholder="you@example.com"
              />
            </div>

            <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? 'Sending…' : 'Send Reset Link'}
            </button>

            <button
              type="button"
              className="btn-link"
              onClick={() => { setShowForgot(false); setError(null) }}
            >
              Back to sign in
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

function getDefaultRedirect(role?: string): string {
  switch (role) {
    case 'professor': return '/dashboard'
    case 'superadmin': return '/admin'
    case 'tenant_admin': return '/admin'
    default: return '/classes'
  }
}
