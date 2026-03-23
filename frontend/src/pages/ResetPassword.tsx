/**
 * ResetPassword — public page, reads token + email from query params.
 * Route: /reset-password
 */

import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

// ---------------------------------------------------------------------------
// Local types
// ---------------------------------------------------------------------------

type PageState = 'form' | 'success' | 'invalid'

interface ResetPayload {
  token: string
  email: string
  newPassword: string
}

interface ResetResponse {
  success: boolean
  message?: string
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const token = searchParams.get('token')
  const email = searchParams.get('email')

  const initialState: PageState = token && email ? 'form' : 'invalid'

  const [pageState, setPageState] = useState<PageState>(initialState)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const resetMutation = useMutation({
    mutationFn: (payload: ResetPayload) =>
      apiClient.post<ResetResponse>('/users/reset-password', payload),
    onSuccess: (result) => {
      if (!result.ok) {
        setFormError(result.error ?? 'Failed to reset password. The link may have expired.')
        return
      }
      setPageState('success')
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setFormError(null)

    if (newPassword.length < 8) {
      setFormError('Password must be at least 8 characters')
      return
    }
    if (newPassword.length > 72) {
      setFormError('Password must be at most 72 characters')
      return
    }
    if (newPassword !== confirmPassword) {
      setFormError('Passwords do not match')
      return
    }

    resetMutation.mutate({ token: token!, email: email!, newPassword })
  }

  // -------------------------------------------------------------------------
  // Render: invalid link
  // -------------------------------------------------------------------------

  if (pageState === 'invalid') {
    return (
      <div className="auth-page">
        <div className="auth-container">
          <div className="auth-header">
            <Link to="/" className="auth-brand">
              <span>Analyt</span><span className="brand-accent">IQ</span>
            </Link>
            <p className="auth-tagline">AI-powered learning platform</p>
          </div>

          <div className="alert alert-error">
            Invalid or missing reset link. Please request a new password reset.
          </div>

          <Link to="/login" className="btn btn-primary btn-full">
            Go to Sign In
          </Link>
        </div>
      </div>
    )
  }

  // -------------------------------------------------------------------------
  // Render: success
  // -------------------------------------------------------------------------

  if (pageState === 'success') {
    return (
      <div className="auth-page">
        <div className="auth-container">
          <div className="auth-header">
            <Link to="/" className="auth-brand">
              <span>Analyt</span><span className="brand-accent">IQ</span>
            </Link>
            <p className="auth-tagline">AI-powered learning platform</p>
          </div>

          <div className="alert alert-success">
            Password reset successfully. You can now sign in with your new password.
          </div>

          <button
            type="button"
            className="btn btn-primary btn-full"
            onClick={() => navigate('/login')}
          >
            Sign In
          </button>
        </div>
      </div>
    )
  }

  // -------------------------------------------------------------------------
  // Render: form
  // -------------------------------------------------------------------------

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-header">
          <Link to="/" className="auth-brand">
            <span>Analyt</span><span className="brand-accent">IQ</span>
          </Link>
          <p className="auth-tagline">AI-powered learning platform</p>
        </div>

        <h2 className="auth-subtitle">Set a New Password</h2>

        {formError && <div className="alert alert-error">{formError}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="new-password">New Password</label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              required
              autoComplete="new-password"
              placeholder="Min 8 characters"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirm-password">Confirm Password</label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
              placeholder="Repeat new password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={resetMutation.isPending}
          >
            {resetMutation.isPending ? 'Resetting…' : 'Reset Password'}
          </button>

          <Link to="/login" className="btn-link" style={{ display: 'block', marginTop: '0.75rem', textAlign: 'center' }}>
            Back to Sign In
          </Link>
        </form>
      </div>
    </div>
  )
}
