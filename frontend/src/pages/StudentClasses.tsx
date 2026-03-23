/**
 * StudentClasses page — enrolled classes grid + join class drawer.
 * Migrated from student-classes.js + student-classes.html.
 */

import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { classesApi } from '@/api/endpoints'
import type { Class } from '@/types'

// ---------------------------------------------------------------------------
// Class card
// ---------------------------------------------------------------------------

interface ClassCardProps {
  classItem: Class
  featured: boolean
  spanStyle: string
}

function ClassCard({ classItem, featured, spanStyle }: ClassCardProps) {
  const navigate = useNavigate()

  function handleEnter() {
    navigate(`/class/${encodeURIComponent(classItem.class_id)}`)
  }

  return (
    <div
      className="class-card neon-hover"
      style={{ gridColumn: spanStyle || undefined }}
      onClick={handleEnter}
    >
      {/* IDE-style tab header */}
      <div className="card-tab-header">
        <div className="card-tab-label">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          <span>{classItem.class_id}.workspace</span>
        </div>
        <div className="card-tab-badges">
          {featured && <span className="badge badge-primary">PRIMARY</span>}
          <div className="card-indicator" />
        </div>
      </div>

      {/* Card body */}
      <div className={`card-body ${featured ? 'card-body--featured' : ''}`}>
        <div className="card-title-row">
          <h3 className={featured ? 'card-title--large' : 'card-title'}>{classItem.name}</h3>
        </div>

        <p className="card-professor">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          Prof. {classItem.professor_name ?? 'Unknown'}
        </p>

        {classItem.description && (
          <p className="card-description">{classItem.description}</p>
        )}

        <div className="card-stats">
          <div className="stat">
            <span className="stat-value">{classItem.chapter_count ?? 0}</span>
            <span className="stat-label">Modules</span>
          </div>
          <div className="stat stat--border-left">
            <span className="stat-value">{classItem.student_count ?? 0}</span>
            <span className="stat-label">Peers</span>
          </div>
        </div>

        <div className="card-footer">
          <button
            className="btn btn-primary btn-full"
            onClick={e => { e.stopPropagation(); handleEnter() }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <polyline points="9 18 15 12 9 6" />
            </svg>
            Enter Class
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Join class drawer
// ---------------------------------------------------------------------------

interface JoinDrawerProps {
  open: boolean
  onClose: () => void
}

function JoinClassDrawer({ open, onClose }: JoinDrawerProps) {
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const enrollMutation = useMutation({
    mutationFn: (classId: string) => classesApi.enroll(classId),
    onSuccess: (result) => {
      if (!result.ok) {
        setError(result.error ?? 'Failed to join class')
        return
      }
      queryClient.invalidateQueries({ queryKey: ['enrolledClasses'] })
      onClose()
      setCode('')
      setError(null)
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!code || code.length < 3 || code.length > 20) {
      setError('> ERROR: Invalid token. Expected 3–20 chars [A-Z, 0-9, -, _]')
      return
    }
    setError(null)
    enrollMutation.mutate(code)
  }

  if (!open) return null

  return (
    <>
      <div className="drawer-overlay visible" onClick={onClose} />
      <div className="drawer visible">
        <div className="drawer-header">
          <h2 className="drawer-title">Join a Class</h2>
          <button className="drawer-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="drawer-body">
          <div className="form-group">
            <label htmlFor="classCode">Class Access Code</label>
            <input
              id="classCode"
              type="text"
              value={code}
              onChange={e => setCode(e.target.value.toUpperCase())}
              placeholder="e.g. CS101-A"
              className="input-mono"
            />
          </div>

          {error && <p className="form-error">{error}</p>}

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={enrollMutation.isPending}
          >
            {enrollMutation.isPending ? '>_ connecting…' : '>_ execute: join'}
          </button>
        </form>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function StudentClasses() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['enrolledClasses'],
    queryFn: async () => {
      const result = await classesApi.getEnrolled()
      if (!result.ok) throw new Error(result.error ?? 'Failed to load classes')
      return result.data
    },
  })

  const classes = data?.classes ?? []
  const count = classes.length

  function getSpanStyle(index: number): string {
    if (count === 1) return ''
    if (count === 2) return index === 0 ? 'span 7' : 'span 5'
    return index === 0 ? 'span 8' : 'span 4'
  }

  return (
    <div className="page">
      {/* Breadcrumb */}
      <div className="page-header">
        <div className="breadcrumb">
          <span className="breadcrumb-item">workspace</span>
          <span className="breadcrumb-sep">›</span>
          <span className="breadcrumb-item breadcrumb-item--active">
            classes{!isLoading && ` · ${count} class${count !== 1 ? 'es' : ''} enrolled`}
          </span>
        </div>

        <div className="page-actions">
          <div className="status-indicator">
            <span
              className={`status-dot ${count > 0 ? 'status-dot--active' : 'status-dot--inactive'}`}
            />
            <span className="status-label">
              {count > 0 ? 'Active Nodes' : 'No Active Nodes'}
            </span>
          </div>
          <button className="btn btn-primary" onClick={() => setDrawerOpen(true)}>
            + Join Class
          </button>
        </div>
      </div>

      {/* Content */}
      {isLoading && (
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading your classes…</p>
        </div>
      )}

      {isError && (
        <div className="empty-state">
          <p className="empty-state-message">Failed to load classes. Please try again.</p>
        </div>
      )}

      {!isLoading && !isError && count === 0 && (
        <div className="empty-state">
          <p className="empty-state-title">No classes yet</p>
          <p className="empty-state-hint">Join a class using an access code from your professor.</p>
          <button className="btn btn-primary" onClick={() => setDrawerOpen(true)}>
            Join your first class
          </button>
        </div>
      )}

      {!isLoading && !isError && count > 0 && (
        <div
          className="classes-grid"
          style={{
            gridTemplateColumns: count === 1 ? '1fr' : 'repeat(12, 1fr)',
          }}
        >
          {classes.map((cls, i) => (
            <ClassCard
              key={cls.class_id}
              classItem={cls}
              featured={i === 0 && count > 1}
              spanStyle={getSpanStyle(i)}
            />
          ))}
        </div>
      )}

      <JoinClassDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  )
}
