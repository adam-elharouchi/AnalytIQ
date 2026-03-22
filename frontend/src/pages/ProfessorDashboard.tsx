/**
 * ProfessorDashboard — class list + create class modal.
 * Migrated from professor-dashboard.js + professor-dashboard.html.
 */

import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { classesApi } from '@/api/endpoints'
import type { Class } from '@/types'

// ---------------------------------------------------------------------------
// Create class modal
// ---------------------------------------------------------------------------

interface CreateClassModalProps {
  open: boolean
  onClose: () => void
}

function CreateClassModal({ open, onClose }: CreateClassModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const createMutation = useMutation({
    mutationFn: () => classesApi.create({ name, description }),
    onSuccess: (result) => {
      if (!result.ok) {
        setError(result.error ?? 'Failed to create class')
        return
      }
      queryClient.invalidateQueries({ queryKey: ['professorClasses'] })
      setName('')
      setDescription('')
      setError(null)
      onClose()
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) { setError('Class name is required'); return }
    setError(null)
    createMutation.mutate()
  }

  if (!open) return null

  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal aria-labelledby="create-class-title">
        <div className="modal-header">
          <h2 id="create-class-title" className="modal-title">Create New Class</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label htmlFor="class-name">Class Name</label>
            <input
              id="class-name"
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              required
              placeholder="e.g. Introduction to Data Science"
            />
          </div>

          <div className="form-group">
            <label htmlFor="class-desc">Description <span className="form-optional">(optional)</span></label>
            <textarea
              id="class-desc"
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
              placeholder="Brief description of the course…"
            />
          </div>

          {error && <p className="form-error">{error}</p>}

          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating…' : 'Create Class'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Class row card
// ---------------------------------------------------------------------------

interface ClassRowProps {
  classItem: Class
  onDelete: (id: string) => void
  isDeleting: boolean
}

function ClassRow({ classItem, onDelete, isDeleting }: ClassRowProps) {
  const navigate = useNavigate()

  return (
    <div className="class-row" onClick={() => navigate(`/class/${classItem.class_id}`)}>
      <div className="class-row-main">
        <h3 className="class-row-name">{classItem.name}</h3>
        {classItem.description && (
          <p className="class-row-desc">{classItem.description}</p>
        )}
      </div>

      <div className="class-row-meta">
        <span className="meta-chip">{classItem.chapter_count ?? 0} modules</span>
        <span className="meta-chip">{classItem.student_count ?? 0} students</span>
        {classItem.join_code && (
          <span className="meta-chip meta-chip--mono">{classItem.join_code}</span>
        )}
      </div>

      <div className="class-row-actions" onClick={e => e.stopPropagation()}>
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => navigate(`/class/${classItem.class_id}`)}
        >
          Manage
        </button>
        <button
          className="btn btn-danger btn-sm"
          disabled={isDeleting}
          onClick={() => {
            if (window.confirm(`Delete "${classItem.name}"? This cannot be undone.`)) {
              onDelete(classItem.class_id)
            }
          }}
        >
          Delete
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ProfessorDashboard() {
  const [modalOpen, setModalOpen] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['professorClasses'],
    queryFn: async () => {
      const result = await classesApi.getProfessorClasses()
      if (!result.ok) throw new Error(result.error ?? 'Failed to load classes')
      return result.data as { classes: Class[] }
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (classId: string) => classesApi.delete(classId),
    onMutate: (classId) => setDeletingId(classId),
    onSettled: () => {
      setDeletingId(null)
      queryClient.invalidateQueries({ queryKey: ['professorClasses'] })
    },
  })

  const classes = data?.classes ?? []

  return (
    <div className="page">
      <div className="page-header">
        <div className="breadcrumb">
          <span className="breadcrumb-item">workspace</span>
          <span className="breadcrumb-sep">›</span>
          <span className="breadcrumb-item breadcrumb-item--active">
            dashboard · {classes.length} class{classes.length !== 1 ? 'es' : ''}
          </span>
        </div>

        <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
          + New Class
        </button>
      </div>

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

      {!isLoading && !isError && classes.length === 0 && (
        <div className="empty-state">
          <p className="empty-state-title">No classes yet</p>
          <p className="empty-state-hint">Create your first class to start adding students and content.</p>
          <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
            Create your first class
          </button>
        </div>
      )}

      {!isLoading && !isError && classes.length > 0 && (
        <div className="class-list">
          {classes.map(cls => (
            <ClassRow
              key={cls.class_id}
              classItem={cls}
              onDelete={id => deleteMutation.mutate(id)}
              isDeleting={deletingId === cls.class_id}
            />
          ))}
        </div>
      )}

      <CreateClassModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}
