/**
 * Profile page — personal info, change password, notifications + danger zone.
 * Available to all authenticated users at /profile.
 */

import { useState, useRef, type FormEvent, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

// ---------------------------------------------------------------------------
// Local types
// ---------------------------------------------------------------------------

interface ProfileData {
  fullName: string
  name: string
  email: string
  bio: string
  profilePicture: string | null
}

interface ProfileResponse {
  fullName?: string
  name?: string
  email?: string
  bio?: string
  profilePicture?: string | null
}

interface SettingsData {
  emailNotifications: boolean
}

interface AlertState {
  message: string
  type: 'success' | 'error'
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// ---------------------------------------------------------------------------
// Section 1: Personal Information
// ---------------------------------------------------------------------------

interface PersonalInfoSectionProps {
  profile: ProfileData
  onProfileUpdate: () => void
}

function PersonalInfoSection({ profile, onProfileUpdate }: PersonalInfoSectionProps) {
  const [fullName, setFullName] = useState(profile.fullName || profile.name || '')
  const [email, setEmail] = useState(profile.email || '')
  const [bio, setBio] = useState(profile.bio || '')
  const [avatarSrc, setAvatarSrc] = useState<string | null>(profile.profilePicture ?? null)
  const [alert, setAlert] = useState<AlertState | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const queryClient = useQueryClient()

  const updateProfileMutation = useMutation({
    mutationFn: (payload: { fullName: string; email: string; bio: string }) =>
      apiClient.put('/users/profile', payload),
    onSuccess: (result) => {
      if (!result.ok) {
        setAlert({ message: result.error ?? 'Failed to save profile', type: 'error' })
        return
      }
      setAlert({ message: 'Profile updated successfully', type: 'success' })
      queryClient.invalidateQueries({ queryKey: ['userProfile'] })
      onProfileUpdate()
    },
  })

  const uploadAvatarMutation = useMutation({
    mutationFn: (profilePicture: string) =>
      apiClient.put('/users/profile', { profilePicture }),
    onSuccess: (result) => {
      if (!result.ok) {
        setAlert({ message: result.error ?? 'Failed to upload picture', type: 'error' })
        return
      }
      setAlert({ message: 'Profile picture updated', type: 'success' })
      queryClient.invalidateQueries({ queryKey: ['userProfile'] })
    },
  })

  function handleAvatarClick() {
    fileInputRef.current?.click()
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setAlert({ message: 'Please select an image file', type: 'error' })
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setAlert({ message: 'Image must be smaller than 5 MB', type: 'error' })
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const dataURL = reader.result as string
      setAvatarSrc(dataURL)
      uploadAvatarMutation.mutate(dataURL)
    }
    reader.readAsDataURL(file)

    // Reset so the same file can be re-selected
    e.target.value = ''
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setAlert(null)

    if (!EMAIL_RE.test(email)) {
      setAlert({ message: 'Please enter a valid email address', type: 'error' })
      return
    }

    updateProfileMutation.mutate({ fullName, email, bio })
  }

  const initials = (fullName || profile.name || '?')[0].toUpperCase()

  return (
    <section className="profile-section">
      <h2 className="profile-section-title">Personal Information</h2>

      {alert && (
        <div className={`alert ${alert.type === 'error' ? 'alert-error' : 'alert-success'}`}>
          {alert.message}
        </div>
      )}

      <div className="avatar-row">
        <button
          type="button"
          className="avatar-btn"
          onClick={handleAvatarClick}
          title="Click to change profile picture"
          aria-label="Change profile picture"
        >
          {avatarSrc ? (
            <img src={avatarSrc} alt="Profile" className="avatar-img" />
          ) : (
            <span className="avatar-initials">{initials}</span>
          )}
          <span className="avatar-overlay">
            {uploadAvatarMutation.isPending ? '…' : '✎'}
          </span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <div className="avatar-hint">Click to upload a new photo (max 5 MB)</div>
      </div>

      <form onSubmit={handleSubmit} className="profile-form">
        <div className="form-group">
          <label htmlFor="full-name">Full Name</label>
          <input
            id="full-name"
            type="text"
            value={fullName}
            onChange={e => setFullName(e.target.value)}
            placeholder="Your full name"
          />
        </div>

        <div className="form-group">
          <label htmlFor="profile-email">Email</label>
          <input
            id="profile-email"
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </div>

        <div className="form-group">
          <label htmlFor="bio">Bio</label>
          <textarea
            id="bio"
            rows={4}
            value={bio}
            onChange={e => setBio(e.target.value)}
            placeholder="Tell us a little about yourself…"
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={updateProfileMutation.isPending}
        >
          {updateProfileMutation.isPending ? 'Saving…' : 'Save Changes'}
        </button>
      </form>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Section 2: Change Password
// ---------------------------------------------------------------------------

function ChangePasswordSection() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [alert, setAlert] = useState<AlertState | null>(null)

  const passwordMutation = useMutation({
    mutationFn: (payload: { currentPassword: string; newPassword: string }) =>
      apiClient.put('/users/password', payload),
    onSuccess: (result) => {
      if (!result.ok) {
        setAlert({ message: result.error ?? 'Failed to update password', type: 'error' })
        return
      }
      setAlert({ message: 'Password updated successfully', type: 'success' })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setAlert(null)

    if (newPassword.length < 8) {
      setAlert({ message: 'New password must be at least 8 characters', type: 'error' })
      return
    }
    if (newPassword.length > 72) {
      setAlert({ message: 'New password must be at most 72 characters', type: 'error' })
      return
    }
    if (newPassword !== confirmPassword) {
      setAlert({ message: 'Passwords do not match', type: 'error' })
      return
    }

    passwordMutation.mutate({ currentPassword, newPassword })
  }

  return (
    <section className="profile-section">
      <h2 className="profile-section-title">Change Password</h2>

      {alert && (
        <div className={`alert ${alert.type === 'error' ? 'alert-error' : 'alert-success'}`}>
          {alert.message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="profile-form">
        <div className="form-group">
          <label htmlFor="current-password">Current Password</label>
          <input
            id="current-password"
            type="password"
            value={currentPassword}
            onChange={e => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
            placeholder="••••••••"
          />
        </div>

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
          <label htmlFor="confirm-password">Confirm New Password</label>
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
          className="btn btn-primary"
          disabled={passwordMutation.isPending}
        >
          {passwordMutation.isPending ? 'Updating…' : 'Update Password'}
        </button>
      </form>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Section 3: Notifications & Danger Zone
// ---------------------------------------------------------------------------

interface NotificationsSectionProps {
  settings: SettingsData
}

function NotificationsSection({ settings }: NotificationsSectionProps) {
  const [emailNotifications, setEmailNotifications] = useState(settings.emailNotifications)
  const [settingsAlert, setSettingsAlert] = useState<AlertState | null>(null)
  const [deleteAlert, setDeleteAlert] = useState<AlertState | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const settingsMutation = useMutation({
    mutationFn: (payload: { emailNotifications: boolean }) =>
      apiClient.put('/users/settings', payload),
    onSuccess: (result) => {
      if (!result.ok) {
        setSettingsAlert({ message: result.error ?? 'Failed to save settings', type: 'error' })
        return
      }
      setSettingsAlert({ message: 'Settings saved', type: 'success' })
      queryClient.invalidateQueries({ queryKey: ['userSettings'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.del('/users/delete'),
    onSuccess: (result) => {
      if (!result.ok) {
        setDeleteAlert({ message: result.error ?? 'Failed to delete account', type: 'error' })
        return
      }
      localStorage.clear()
      navigate('/login')
    },
  })

  function handleToggle(checked: boolean) {
    setEmailNotifications(checked)
    settingsMutation.mutate({ emailNotifications: checked })
  }

  function handleDeleteAccount() {
    const first = window.confirm(
      'Are you sure you want to delete your account? This action cannot be undone.',
    )
    if (!first) return

    const second = window.confirm(
      'This will permanently delete all your data. Are you absolutely sure?',
    )
    if (!second) return

    deleteMutation.mutate()
  }

  return (
    <section className="profile-section">
      <h2 className="profile-section-title">Notifications</h2>

      {settingsAlert && (
        <div className={`alert ${settingsAlert.type === 'error' ? 'alert-error' : 'alert-success'}`}>
          {settingsAlert.message}
        </div>
      )}

      <div className="form-group form-group--inline">
        <label htmlFor="email-notifications" className="toggle-label">
          <input
            id="email-notifications"
            type="checkbox"
            checked={emailNotifications}
            onChange={e => handleToggle(e.target.checked)}
            disabled={settingsMutation.isPending}
          />
          <span>Email Notifications</span>
        </label>
        <p className="form-hint">Receive emails about activity in your classes.</p>
      </div>

      <div className="danger-zone">
        <h3 className="danger-zone-title">Danger Zone</h3>
        <p className="danger-zone-desc">
          Permanently delete your account and all associated data. This cannot be undone.
        </p>

        {deleteAlert && (
          <div className={`alert ${deleteAlert.type === 'error' ? 'alert-error' : 'alert-success'}`}>
            {deleteAlert.message}
          </div>
        )}

        <button
          type="button"
          className="btn btn-danger"
          onClick={handleDeleteAccount}
          disabled={deleteMutation.isPending}
        >
          {deleteMutation.isPending ? 'Deleting…' : 'Delete Account'}
        </button>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Profile() {
  const profileQuery = useQuery({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const result = await apiClient.get<ProfileResponse>('/users/profile')
      if (!result.ok) throw new Error(result.error ?? 'Failed to load profile')
      return result.data!
    },
  })

  const settingsQuery = useQuery({
    queryKey: ['userSettings'],
    queryFn: async () => {
      const result = await apiClient.get<SettingsData>('/users/settings')
      if (!result.ok) throw new Error(result.error ?? 'Failed to load settings')
      return result.data!
    },
  })

  const queryClient = useQueryClient()

  if (profileQuery.isLoading || settingsQuery.isLoading) {
    return (
      <div className="page">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading profile…</p>
        </div>
      </div>
    )
  }

  if (profileQuery.isError) {
    return (
      <div className="page">
        <div className="alert alert-error">Failed to load profile. Please try again.</div>
      </div>
    )
  }

  const raw = profileQuery.data!
  const profile: ProfileData = {
    fullName: raw.fullName ?? '',
    name: raw.name ?? '',
    email: raw.email ?? '',
    bio: raw.bio ?? '',
    profilePicture: raw.profilePicture ?? null,
  }

  const settings: SettingsData = settingsQuery.data ?? { emailNotifications: false }

  return (
    <div className="page">
      <div className="page-header">
        <div className="breadcrumb">
          <span className="breadcrumb-item">account</span>
          <span className="breadcrumb-sep">›</span>
          <span className="breadcrumb-item breadcrumb-item--active">profile</span>
        </div>
      </div>

      <div className="profile-sections">
        <PersonalInfoSection
          profile={profile}
          onProfileUpdate={() => queryClient.invalidateQueries({ queryKey: ['userProfile'] })}
        />
        <ChangePasswordSection />
        <NotificationsSection settings={settings} />
      </div>
    </div>
  )
}
