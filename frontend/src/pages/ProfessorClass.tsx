/**
 * ProfessorClass — full class management page for professors, superadmins, tenant_admins.
 * Migrated from professor-class.html + professor-class.js (2,497 lines).
 * Route: /professor-class/:classId
 *
 * Tabs: Chapters | Exercises | Resources | Students | Leaderboard
 */

import { useState, useRef, type FormEvent, type ChangeEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

// ---------------------------------------------------------------------------
// Local types
// ---------------------------------------------------------------------------

interface ClassDetail {
  class_id: string
  name: string
  description?: string
  professor_name?: string
  student_count?: number
  chapter_count?: number
  exercise_count?: number
  join_code?: string
}

interface Chapter {
  chapter_id: string
  title: string
  description?: string
  chapter_number?: number
  created_at?: string
  pdf_url?: string
  pdf_filename?: string
}

interface Exercise {
  exercise_id: string
  chapter_id: string
  title: string
  description?: string
  difficulty?: 'easy' | 'medium' | 'hard'
  solution_code?: string
}

interface Resource {
  resource_id: string
  title: string
  description?: string
  resource_type: string
  resource_url: string
  is_default?: boolean
}

interface Student {
  user_id: string
  name: string
  email: string
  enrolled_at?: string
}

interface ProgressEntry {
  user_id: string
  name: string
  progress: Record<string, { completed: boolean; score?: number }>
}

interface ProgressData {
  students: ProgressEntry[]
  exercises: Array<{ id: string; title: string }>
}

interface AvgLeaderboardEntry {
  rank: number
  name: string
  exercises_completed: number
  average_score: number
}

interface ExerciseLeaderboardEntry {
  rank: number
  name: string
  score: number
  submitted_at?: string
}

type Tab = 'chapters' | 'exercises' | 'resources' | 'students' | 'leaderboard'
type LeaderboardSubTab = 'average' | 'by-exercise' | 'matrix'
type ResourceSourceMode = 'link' | 'file'

// ---------------------------------------------------------------------------
// Hardcoded default resources
// ---------------------------------------------------------------------------

const DEFAULT_RESOURCES: Resource[] = [
  {
    resource_id: 'default-colab',
    title: 'Google Colab',
    description: 'Free cloud Jupyter notebooks with GPU support',
    resource_type: 'tool',
    resource_url: 'https://colab.research.google.com',
    is_default: true,
  },
  {
    resource_id: 'default-code-assistant',
    title: 'Code Assistant',
    description: 'AI-powered coding help built into AnalytIQ',
    resource_type: 'tool',
    resource_url: '/code-assistant',
    is_default: true,
  },
  {
    resource_id: 'default-kaggle',
    title: 'Kaggle Datasets',
    description: 'Thousands of datasets for machine learning and analytics',
    resource_type: 'dataset',
    resource_url: 'https://www.kaggle.com/datasets',
    is_default: true,
  },
  {
    resource_id: 'default-uci',
    title: 'UCI ML Repository',
    description: 'Classic benchmark datasets for machine learning research',
    resource_type: 'dataset',
    resource_url: 'https://archive.ics.uci.edu/datasets',
    is_default: true,
  },
  {
    resource_id: 'default-nyc',
    title: 'NYC Open Data',
    description: 'Free public data published by New York City agencies',
    resource_type: 'dataset',
    resource_url: 'https://opendata.cityofnewyork.us',
    is_default: true,
  },
  {
    resource_id: 'default-worldbank',
    title: 'World Bank Open Data',
    description: 'Global development data from the World Bank',
    resource_type: 'dataset',
    resource_url: 'https://data.worldbank.org',
    is_default: true,
  },
]

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------

function difficultyStyle(difficulty?: string): React.CSSProperties {
  if (difficulty === 'easy') {
    return {
      color: '#6ee7b7',
      background: 'rgba(16,185,129,0.15)',
      border: '1px solid rgba(16,185,129,0.3)',
      fontFamily: 'monospace',
      fontSize: '0.7rem',
      padding: '0.15rem 0.5rem',
      borderRadius: '0.25rem',
    }
  }
  if (difficulty === 'medium') {
    return {
      color: '#fcd34d',
      background: 'rgba(245,158,11,0.15)',
      border: '1px solid rgba(245,158,11,0.3)',
      fontFamily: 'monospace',
      fontSize: '0.7rem',
      padding: '0.15rem 0.5rem',
      borderRadius: '0.25rem',
    }
  }
  if (difficulty === 'hard') {
    return {
      color: '#fca5a5',
      background: 'rgba(239,68,68,0.15)',
      border: '1px solid rgba(239,68,68,0.3)',
      fontFamily: 'monospace',
      fontSize: '0.7rem',
      padding: '0.15rem 0.5rem',
      borderRadius: '0.25rem',
    }
  }
  return {
    fontFamily: 'monospace',
    fontSize: '0.7rem',
    padding: '0.15rem 0.5rem',
    borderRadius: '0.25rem',
  }
}

function formatDate(iso?: string) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return iso
  }
}

function avg(nums: number[]): number {
  if (!nums.length) return 0
  return nums.reduce((s, n) => s + n, 0) / nums.length
}

// ---------------------------------------------------------------------------
// Delete confirmation modal
// ---------------------------------------------------------------------------

interface DeleteModalProps {
  open: boolean
  message: string
  isPending: boolean
  onConfirm: () => void
  onClose: () => void
}

function DeleteModal({ open, message, isPending, onConfirm, onClose }: DeleteModalProps) {
  if (!open) return null
  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal aria-labelledby="delete-modal-title">
        <div className="modal-header">
          <h2 id="delete-modal-title" className="modal-title">Confirm Delete</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="modal-body">
          <p style={{ marginBottom: '1.5rem' }}>{message}</p>
          <div className="modal-actions">
            <button className="btn btn-ghost" onClick={onClose} disabled={isPending}>Cancel</button>
            <button className="btn btn-danger" onClick={onConfirm} disabled={isPending}>
              {isPending ? 'Deleting…' : 'Delete'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Edit class modal
// ---------------------------------------------------------------------------

interface EditClassModalProps {
  open: boolean
  classDetail: ClassDetail
  onClose: () => void
  onSaved: () => void
  classId: string
}

function EditClassModal({ open, classDetail, onClose, onSaved, classId }: EditClassModalProps) {
  const [name, setName] = useState(classDetail.name)
  const [description, setDescription] = useState(classDetail.description ?? '')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => apiClient.put(`/classes/${classId}`, { name, description }),
    onSuccess: (result) => {
      if (!result.ok) { setError(result.error ?? 'Failed to update class'); return }
      onSaved()
      onClose()
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) { setError('Class name is required'); return }
    setError(null)
    mutation.mutate()
  }

  if (!open) return null
  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal aria-labelledby="edit-class-title">
        <div className="modal-header">
          <h2 id="edit-class-title" className="modal-title">Edit Class</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label htmlFor="edit-class-name">Class Name</label>
            <input
              id="edit-class-name"
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="edit-class-desc">Description</label>
            <textarea
              id="edit-class-desc"
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
            />
          </div>
          {error && <p className="alert alert-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Upload chapter modal
// ---------------------------------------------------------------------------

interface UploadChapterModalProps {
  open: boolean
  classId: string
  onClose: () => void
  onUploaded: () => void
}

function UploadChapterModal({ open, classId, onClose, onUploaded }: UploadChapterModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [exerciseMode, setExerciseMode] = useState<'auto' | 'manual'>('auto')
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const mutation = useMutation({
    mutationFn: () => {
      const file = fileRef.current?.files?.[0]
      if (!file) throw new Error('No file selected')
      const fd = new FormData()
      fd.append('pdf_file', file)
      fd.append('title', title)
      fd.append('description', description)
      fd.append('exercise_mode', exerciseMode)
      return apiClient.upload(`/classes/${classId}/chapters`, fd)
    },
    onSuccess: (result) => {
      if (!result.ok) { setError(result.error ?? 'Upload failed'); return }
      setTitle('')
      setDescription('')
      setExerciseMode('auto')
      if (fileRef.current) fileRef.current.value = ''
      setError(null)
      onUploaded()
      onClose()
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) { setError('Title is required'); return }
    if (!fileRef.current?.files?.length) { setError('PDF file is required'); return }
    setError(null)
    mutation.mutate()
  }

  if (!open) return null
  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal aria-labelledby="upload-chapter-title">
        <div className="modal-header">
          <h2 id="upload-chapter-title" className="modal-title">Upload Chapter</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label htmlFor="ch-title">Title *</label>
            <input
              id="ch-title"
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              required
              placeholder="e.g. Chapter 1: Introduction"
            />
          </div>
          <div className="form-group">
            <label htmlFor="ch-desc">Description</label>
            <textarea
              id="ch-desc"
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={2}
              placeholder="Optional overview…"
            />
          </div>
          <div className="form-group">
            <label htmlFor="ch-pdf">PDF File *</label>
            <input id="ch-pdf" type="file" accept=".pdf" ref={fileRef} required />
          </div>
          <div className="form-group">
            <label>Exercise Mode</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.25rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="exercise-mode"
                  value="auto"
                  checked={exerciseMode === 'auto'}
                  onChange={() => setExerciseMode('auto')}
                />
                Auto-generate exercises
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="exercise-mode"
                  value="manual"
                  checked={exerciseMode === 'manual'}
                  onChange={() => setExerciseMode('manual')}
                />
                Manual (add exercises later)
              </label>
            </div>
          </div>
          {error && <p className="alert alert-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Uploading…' : 'Upload Chapter'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Edit chapter modal
// ---------------------------------------------------------------------------

interface EditChapterModalProps {
  open: boolean
  chapter: Chapter | null
  onClose: () => void
  onSaved: () => void
}

function EditChapterModal({ open, chapter, onClose, onSaved }: EditChapterModalProps) {
  const [title, setTitle] = useState(chapter?.title ?? '')
  const [description, setDescription] = useState(chapter?.description ?? '')
  const [error, setError] = useState<string | null>(null)

  // Sync when chapter changes
  if (open && chapter && title !== chapter.title && description !== (chapter.description ?? '')) {
    setTitle(chapter.title)
    setDescription(chapter.description ?? '')
  }

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.put(`/chapters/${chapter!.chapter_id}`, { title, description }),
    onSuccess: (result) => {
      if (!result.ok) { setError(result.error ?? 'Failed to update chapter'); return }
      onSaved()
      onClose()
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) { setError('Title is required'); return }
    setError(null)
    mutation.mutate()
  }

  if (!open || !chapter) return null
  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal aria-labelledby="edit-chapter-title">
        <div className="modal-header">
          <h2 id="edit-chapter-title" className="modal-title">Edit Chapter</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label htmlFor="ech-title">Title *</label>
            <input
              id="ech-title"
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="ech-desc">Description</label>
            <textarea
              id="ech-desc"
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={2}
            />
          </div>
          {error && <p className="alert alert-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Create / Edit exercise modal
// ---------------------------------------------------------------------------

interface ExerciseModalProps {
  open: boolean
  chapters: Chapter[]
  classId: string
  editTarget: Exercise | null
  defaultChapterId?: string
  onClose: () => void
  onSaved: () => void
}

function ExerciseModal({ open, chapters, classId, editTarget, defaultChapterId, onClose, onSaved }: ExerciseModalProps) {
  const [chapterId, setChapterId] = useState(editTarget?.chapter_id ?? defaultChapterId ?? chapters[0]?.chapter_id ?? '')
  const [title, setTitle] = useState(editTarget?.title ?? '')
  const [description, setDescription] = useState(editTarget?.description ?? '')
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>(editTarget?.difficulty ?? 'medium')
  const [solutionCode, setSolutionCode] = useState(editTarget?.solution_code ?? '')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const isEdit = !!editTarget

  const mutation = useMutation({
    mutationFn: () => {
      const body = { title, description, difficulty, solution_code: solutionCode }
      if (isEdit) {
        return apiClient.put(`/exercises/${editTarget.exercise_id}`, body)
      }
      return apiClient.post(`/classes/${classId}/chapters/${chapterId}/exercises`, body)
    },
    onSuccess: (result) => {
      if (!result.ok) { setError(result.error ?? 'Failed to save exercise'); return }
      queryClient.invalidateQueries({ queryKey: ['exercises', classId] })
      onSaved()
      onClose()
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) { setError('Title is required'); return }
    if (!chapterId) { setError('Chapter is required'); return }
    setError(null)
    mutation.mutate()
  }

  // Reset when opening
  if (open && !isEdit && title === '' && chapters.length && !chapterId) {
    setChapterId(defaultChapterId ?? chapters[0].chapter_id)
  }

  if (!open) return null
  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal aria-labelledby="ex-modal-title" style={{ maxWidth: '600px' }}>
        <div className="modal-header">
          <h2 id="ex-modal-title" className="modal-title">{isEdit ? 'Edit Exercise' : 'Create Exercise'}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          {!isEdit && (
            <div className="form-group">
              <label htmlFor="ex-chapter">Chapter *</label>
              <select id="ex-chapter" value={chapterId} onChange={e => setChapterId(e.target.value)} required>
                <option value="">Select chapter…</option>
                {chapters.map(ch => (
                  <option key={ch.chapter_id} value={ch.chapter_id}>{ch.title}</option>
                ))}
              </select>
            </div>
          )}
          <div className="form-group">
            <label htmlFor="ex-title">Title *</label>
            <input
              id="ex-title"
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              required
              placeholder="e.g. Pandas DataFrame Basics"
            />
          </div>
          <div className="form-group">
            <label htmlFor="ex-desc">Description</label>
            <textarea
              id="ex-desc"
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={2}
              placeholder="What should students accomplish?"
            />
          </div>
          <div className="form-group">
            <label htmlFor="ex-difficulty">Difficulty</label>
            <select
              id="ex-difficulty"
              value={difficulty}
              onChange={e => setDifficulty(e.target.value as 'easy' | 'medium' | 'hard')}
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="ex-solution">Solution Code</label>
            <textarea
              id="ex-solution"
              value={solutionCode}
              onChange={e => setSolutionCode(e.target.value)}
              rows={5}
              placeholder="# Reference solution…"
              style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
            />
          </div>
          {error && <p className="alert alert-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Exercise'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Add / Edit resource modal
// ---------------------------------------------------------------------------

const RESOURCE_TYPES = ['pdf', 'tool', 'dataset', 'video', 'article', 'link', 'csv', 'excel', 'ipynb']

interface ResourceModalProps {
  open: boolean
  classId: string
  editTarget: Resource | null
  onClose: () => void
  onSaved: () => void
}

function ResourceModal({ open, classId, editTarget, onClose, onSaved }: ResourceModalProps) {
  const [title, setTitle] = useState(editTarget?.title ?? '')
  const [description, setDescription] = useState(editTarget?.description ?? '')
  const [resourceType, setResourceType] = useState(editTarget?.resource_type ?? 'link')
  const [sourceMode, setSourceMode] = useState<ResourceSourceMode>('link')
  const [url, setUrl] = useState(editTarget?.resource_url ?? '')
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const isEdit = !!editTarget

  const mutation = useMutation({
    mutationFn: () => {
      if (isEdit) {
        return apiClient.put(`/classes/${classId}/resources/${editTarget.resource_id}`, {
          title, description, resource_type: resourceType, resource_url: url,
        })
      }
      if (sourceMode === 'file') {
        const file = fileRef.current?.files?.[0]
        if (!file) throw new Error('No file selected')
        const fd = new FormData()
        fd.append('file', file)
        fd.append('class_id', classId)
        fd.append('resource_type', resourceType)
        fd.append('title', title)
        fd.append('description', description)
        return apiClient.upload(`/classes/${classId}/resources/upload`, fd)
      }
      return apiClient.post(`/classes/${classId}/resources`, {
        title, description, resource_type: resourceType, resource_url: url,
      })
    },
    onSuccess: (result) => {
      if (!result.ok) { setError(result.error ?? 'Failed to save resource'); return }
      queryClient.invalidateQueries({ queryKey: ['resources', classId] })
      onSaved()
      onClose()
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) { setError('Title is required'); return }
    if (!isEdit && sourceMode === 'link' && !url.trim()) { setError('URL is required'); return }
    if (!isEdit && sourceMode === 'file' && !fileRef.current?.files?.length) {
      setError('File is required')
      return
    }
    setError(null)
    mutation.mutate()
  }

  if (!open) return null
  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal aria-labelledby="res-modal-title">
        <div className="modal-header">
          <h2 id="res-modal-title" className="modal-title">{isEdit ? 'Edit Resource' : 'Add Resource'}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label htmlFor="res-title">Title *</label>
            <input
              id="res-title"
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              required
              placeholder="Resource name"
            />
          </div>
          <div className="form-group">
            <label htmlFor="res-desc">Description</label>
            <textarea
              id="res-desc"
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={2}
            />
          </div>
          <div className="form-group">
            <label htmlFor="res-type">Type</label>
            <select
              id="res-type"
              value={resourceType}
              onChange={e => setResourceType(e.target.value)}
            >
              {RESOURCE_TYPES.map(t => (
                <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
              ))}
            </select>
          </div>
          {!isEdit && (
            <>
              <div className="form-group">
                <label>Source</label>
                <div style={{ display: 'flex', gap: '1rem', marginTop: '0.25rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="source-mode"
                      value="link"
                      checked={sourceMode === 'link'}
                      onChange={() => setSourceMode('link')}
                    />
                    Link URL
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="source-mode"
                      value="file"
                      checked={sourceMode === 'file'}
                      onChange={() => setSourceMode('file')}
                    />
                    File Upload
                  </label>
                </div>
              </div>
              {sourceMode === 'link' ? (
                <div className="form-group">
                  <label htmlFor="res-url">URL *</label>
                  <input
                    id="res-url"
                    type="url"
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    placeholder="https://…"
                    required
                  />
                </div>
              ) : (
                <div className="form-group">
                  <label htmlFor="res-file">File *</label>
                  <input id="res-file" type="file" ref={fileRef} required />
                </div>
              )}
            </>
          )}
          {isEdit && (
            <div className="form-group">
              <label htmlFor="res-url-edit">URL</label>
              <input
                id="res-url-edit"
                type="url"
                value={url}
                onChange={e => setUrl(e.target.value)}
              />
            </div>
          )}
          {error && <p className="alert alert-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Resource'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Tab: Chapters
// ---------------------------------------------------------------------------

interface ChaptersTabProps {
  classId: string
  chapters: Chapter[]
  isLoading: boolean
  onRefresh: () => void
}

function ChaptersTab({ classId, chapters, isLoading, onRefresh }: ChaptersTabProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [editChapter, setEditChapter] = useState<Chapter | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Chapter | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (chapterId: string) => apiClient.del(`/chapters/${chapterId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapters', classId] })
      setDeleteTarget(null)
    },
  })

  if (isLoading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <p>Loading chapters…</p>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
        <button className="btn btn-primary" onClick={() => setUploadOpen(true)}>
          + Upload Chapter
        </button>
      </div>

      {chapters.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state-title">No chapters yet</p>
          <p className="empty-state-hint">Upload a PDF to create your first chapter.</p>
          <button className="btn btn-primary" onClick={() => setUploadOpen(true)}>Upload Chapter</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {chapters.map(ch => (
            <div key={ch.chapter_id} className="class-card">
              <div className="card-tab-header">
                <span className="card-tab-label" style={{ fontFamily: 'monospace', fontSize: '0.75rem', opacity: 0.6 }}>
                  ch-{ch.chapter_number ?? '?'}
                </span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {ch.pdf_url && (
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => navigate(`/chapter/${ch.chapter_id}?classId=${classId}`)}
                    >
                      Open Chapter
                    </button>
                  )}
                  <button className="btn btn-ghost btn-sm" onClick={() => setEditChapter(ch)}>Edit</button>
                  <button className="btn btn-danger btn-sm" onClick={() => setDeleteTarget(ch)}>Delete</button>
                </div>
              </div>
              <div className="card-body">
                <h3 style={{ margin: '0 0 0.25rem' }}>{ch.title}</h3>
                {ch.description && <p style={{ margin: '0 0 0.5rem', opacity: 0.7 }}>{ch.description}</p>}
                {ch.created_at && (
                  <span style={{ fontSize: '0.75rem', opacity: 0.5 }}>{formatDate(ch.created_at)}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <UploadChapterModal
        open={uploadOpen}
        classId={classId}
        onClose={() => setUploadOpen(false)}
        onUploaded={() => {
          queryClient.invalidateQueries({ queryKey: ['chapters', classId] })
          onRefresh()
        }}
      />

      <EditChapterModal
        open={!!editChapter}
        chapter={editChapter}
        onClose={() => setEditChapter(null)}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ['chapters', classId] })}
      />

      <DeleteModal
        open={!!deleteTarget}
        message={`Delete chapter "${deleteTarget?.title}"? This cannot be undone.`}
        isPending={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.chapter_id)}
        onClose={() => setDeleteTarget(null)}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab: Exercises
// ---------------------------------------------------------------------------

interface ExercisesTabProps {
  classId: string
  chapters: Chapter[]
}

function ExercisesTab({ classId, chapters }: ExercisesTabProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [editExercise, setEditExercise] = useState<Exercise | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Exercise | null>(null)

  // Load exercises for all chapters in parallel
  const exerciseQueries = useQuery({
    queryKey: ['exercises', classId],
    queryFn: async () => {
      const results = await Promise.all(
        chapters.map(ch =>
          apiClient.get<{ exercises: Exercise[] }>(`/chapters/${ch.chapter_id}/exercises`)
            .then(r => ({ chapterId: ch.chapter_id, exercises: r.ok ? ((r.data as { exercises: Exercise[] })?.exercises ?? []) : [] }))
        )
      )
      return results
    },
    enabled: chapters.length > 0,
  })

  const deleteMutation = useMutation({
    mutationFn: (exerciseId: string) => apiClient.del(`/exercises/${exerciseId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exercises', classId] })
      setDeleteTarget(null)
    },
  })

  const chapterMap = Object.fromEntries(chapters.map(ch => [ch.chapter_id, ch]))
  const allGroups = exerciseQueries.data ?? []

  if (!chapters.length) {
    return (
      <div className="empty-state">
        <p className="empty-state-title">No chapters yet</p>
        <p className="empty-state-hint">Upload a chapter first, then add exercises.</p>
      </div>
    )
  }

  if (exerciseQueries.isLoading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <p>Loading exercises…</p>
      </div>
    )
  }

  const hasAny = allGroups.some(g => g.exercises.length > 0)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
        <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
          + Create Exercise
        </button>
      </div>

      {!hasAny && (
        <div className="empty-state">
          <p className="empty-state-title">No exercises yet</p>
          <p className="empty-state-hint">Create your first exercise for students to complete.</p>
          <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>Create Exercise</button>
        </div>
      )}

      {allGroups.map(group => {
        if (!group.exercises.length) return null
        const chapter = chapterMap[group.chapterId]
        return (
          <div key={group.chapterId} style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ marginBottom: '0.75rem', opacity: 0.8, fontFamily: 'monospace', fontSize: '0.85rem' }}>
              {chapter?.title ?? group.chapterId}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {group.exercises.map(ex => (
                <div key={ex.exercise_id} className="class-card">
                  <div className="card-tab-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span>{ex.title}</span>
                      {ex.difficulty && (
                        <span style={difficultyStyle(ex.difficulty)}>{ex.difficulty}</span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => navigate(`/exercise/${ex.exercise_id}?classId=${classId}&chapterId=${ex.chapter_id}`)}
                      >
                        Execute
                      </button>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => setEditExercise(ex)}
                      >
                        Edit
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => setDeleteTarget(ex)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  {ex.description && (
                    <div className="card-body">
                      <p style={{ margin: 0, opacity: 0.7, fontSize: '0.875rem' }}>{ex.description}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )
      })}

      <ExerciseModal
        open={createOpen}
        chapters={chapters}
        classId={classId}
        editTarget={null}
        onClose={() => setCreateOpen(false)}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ['exercises', classId] })}
      />

      <ExerciseModal
        open={!!editExercise}
        chapters={chapters}
        classId={classId}
        editTarget={editExercise}
        onClose={() => setEditExercise(null)}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ['exercises', classId] })}
      />

      <DeleteModal
        open={!!deleteTarget}
        message={`Delete exercise "${deleteTarget?.title}"? This cannot be undone.`}
        isPending={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.exercise_id)}
        onClose={() => setDeleteTarget(null)}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab: Resources
// ---------------------------------------------------------------------------

interface ResourcesTabProps {
  classId: string
}

function ResourcesTab({ classId }: ResourcesTabProps) {
  const queryClient = useQueryClient()
  const [addOpen, setAddOpen] = useState(false)
  const [editResource, setEditResource] = useState<Resource | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Resource | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['resources', classId],
    queryFn: async () => {
      const r = await apiClient.get<{ all_resources: Resource[] }>(`/classes/${classId}/resources`)
      if (!r.ok) throw new Error(r.error ?? 'Failed to load resources')
      return r.data as { all_resources: Resource[] }
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (resourceId: string) => apiClient.del(`/classes/${classId}/resources/${resourceId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resources', classId] })
      setDeleteTarget(null)
    },
  })

  const customResources = data?.all_resources ?? []
  const allResources = [...DEFAULT_RESOURCES, ...customResources]

  // Group by type
  const grouped: Record<string, Resource[]> = {}
  for (const r of allResources) {
    if (!grouped[r.resource_type]) grouped[r.resource_type] = []
    grouped[r.resource_type].push(r)
  }

  if (isLoading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <p>Loading resources…</p>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
        <button className="btn btn-primary" onClick={() => setAddOpen(true)}>+ Add Resource</button>
      </div>

      {Object.entries(grouped).map(([type, resources]) => (
        <div key={type} style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ marginBottom: '0.75rem', fontFamily: 'monospace', fontSize: '0.85rem', opacity: 0.7, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {type}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {resources.map(res => (
              <div key={res.resource_id} className="class-card">
                <div className="card-tab-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span>{res.title}</span>
                    <span className="badge badge-primary" style={{ fontSize: '0.7rem' }}>{res.resource_type}</span>
                    {res.is_default && (
                      <span style={{ fontSize: '0.7rem', opacity: 0.5, fontFamily: 'monospace' }}>default</span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    {res.resource_url.startsWith('/') ? (
                      <a
                        href={res.resource_url}
                        className="btn btn-ghost btn-sm"
                        style={{ textDecoration: 'none' }}
                      >
                        Visit
                      </a>
                    ) : (
                      <a
                        href={res.resource_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-ghost btn-sm"
                        style={{ textDecoration: 'none' }}
                      >
                        Visit ↗
                      </a>
                    )}
                    {!res.is_default && (
                      <>
                        <button className="btn btn-ghost btn-sm" onClick={() => setEditResource(res)}>Edit</button>
                        <button className="btn btn-danger btn-sm" onClick={() => setDeleteTarget(res)}>Delete</button>
                      </>
                    )}
                  </div>
                </div>
                {res.description && (
                  <div className="card-body">
                    <p style={{ margin: 0, opacity: 0.7, fontSize: '0.875rem' }}>{res.description}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      <ResourceModal
        open={addOpen}
        classId={classId}
        editTarget={null}
        onClose={() => setAddOpen(false)}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ['resources', classId] })}
      />

      <ResourceModal
        open={!!editResource}
        classId={classId}
        editTarget={editResource}
        onClose={() => setEditResource(null)}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ['resources', classId] })}
      />

      <DeleteModal
        open={!!deleteTarget}
        message={`Delete resource "${deleteTarget?.title}"?`}
        isPending={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.resource_id)}
        onClose={() => setDeleteTarget(null)}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab: Students
// ---------------------------------------------------------------------------

interface StudentsTabProps {
  classId: string
  progressData: ProgressData | null
}

function StudentsTab({ classId, progressData }: StudentsTabProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['students', classId],
    queryFn: async () => {
      const r = await apiClient.get<{ students: Student[] }>(`/classes/${classId}/students`)
      if (!r.ok) throw new Error(r.error ?? 'Failed to load students')
      return r.data as { students: Student[] }
    },
  })

  const students = data?.students ?? []
  const totalExercises = progressData?.exercises.length ?? 0

  function getStudentProgress(userId: string) {
    const entry = progressData?.students.find(s => s.user_id === userId)
    if (!entry) return { completed: 0, avgScore: 0 }
    const vals = Object.values(entry.progress)
    const completed = vals.filter(v => v.completed).length
    const scores = vals.filter(v => v.score !== undefined).map(v => v.score as number)
    return {
      completed,
      avgScore: scores.length ? avg(scores) : 0,
    }
  }

  if (isLoading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <p>Loading students…</p>
      </div>
    )
  }

  if (!students.length) {
    return (
      <div className="empty-state">
        <p className="empty-state-title">No students enrolled</p>
        <p className="empty-state-hint">Share the class code so students can join.</p>
      </div>
    )
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
            <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', fontWeight: 600 }}>Name</th>
            <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', fontWeight: 600 }}>Email</th>
            <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', fontWeight: 600, minWidth: '140px' }}>Progress</th>
            <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', fontWeight: 600 }}>Avg Score</th>
            <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', fontWeight: 600 }}>Enrolled</th>
          </tr>
        </thead>
        <tbody>
          {students.map(s => {
            const { completed, avgScore } = getStudentProgress(s.user_id)
            const pct = totalExercises > 0 ? Math.round((completed / totalExercises) * 100) : 0
            return (
              <tr key={s.user_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '0.75rem 0.5rem' }}>{s.name}</td>
                <td style={{ padding: '0.75rem 0.5rem', opacity: 0.7, fontFamily: 'monospace', fontSize: '0.8rem' }}>{s.email}</td>
                <td style={{ padding: '0.75rem 0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div
                      style={{
                        flex: 1,
                        minWidth: '80px',
                        height: '6px',
                        background: 'rgba(255,255,255,0.1)',
                        borderRadius: '3px',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          width: `${pct}%`,
                          height: '100%',
                          background: pct >= 90 ? '#6ee7b7' : pct >= 70 ? '#60a5fa' : pct >= 50 ? '#fcd34d' : '#f87171',
                          borderRadius: '3px',
                          transition: 'width 0.3s ease',
                        }}
                      />
                    </div>
                    <span style={{ fontSize: '0.75rem', opacity: 0.7, whiteSpace: 'nowrap' }}>
                      {completed}/{totalExercises}
                    </span>
                  </div>
                </td>
                <td style={{ padding: '0.75rem 0.5rem' }}>
                  {avgScore > 0 ? `${Math.round(avgScore)}%` : '—'}
                </td>
                <td style={{ padding: '0.75rem 0.5rem', opacity: 0.6, fontSize: '0.8rem' }}>
                  {formatDate(s.enrolled_at)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab: Leaderboard
// ---------------------------------------------------------------------------

interface LeaderboardTabProps {
  classId: string
  progressData: ProgressData | null
  exercises: Exercise[]
}

function LeaderboardTab({ classId, progressData, exercises }: LeaderboardTabProps) {
  const [subTab, setSubTab] = useState<LeaderboardSubTab>('average')
  const [selectedExerciseId, setSelectedExerciseId] = useState<string>('')

  const avgQuery = useQuery({
    queryKey: ['leaderboard-avg', classId],
    queryFn: async () => {
      const r = await apiClient.get<{ leaderboard: AvgLeaderboardEntry[] }>(`/classes/${classId}/leaderboard/average`)
      if (!r.ok) throw new Error(r.error ?? 'Failed')
      return r.data as { leaderboard: AvgLeaderboardEntry[] }
    },
    enabled: subTab === 'average',
  })

  const exLeaderQuery = useQuery({
    queryKey: ['leaderboard-ex', classId, selectedExerciseId],
    queryFn: async () => {
      const r = await apiClient.get<{ leaderboard: ExerciseLeaderboardEntry[] }>(
        `/classes/${classId}/leaderboard/exercise/${selectedExerciseId}`
      )
      if (!r.ok) throw new Error(r.error ?? 'Failed')
      return r.data as { leaderboard: ExerciseLeaderboardEntry[] }
    },
    enabled: subTab === 'by-exercise' && !!selectedExerciseId,
  })

  function cellColor(score: number | undefined, completed: boolean): string {
    if (!completed || score === undefined) return 'rgba(255,255,255,0.05)'
    if (score >= 90) return 'rgba(16,185,129,0.3)'
    if (score >= 70) return 'rgba(96,165,250,0.3)'
    if (score >= 50) return 'rgba(245,158,11,0.3)'
    return 'rgba(239,68,68,0.3)'
  }

  return (
    <div>
      <div className="auth-tabs" style={{ marginBottom: '1.5rem' }}>
        {(['average', 'by-exercise', 'matrix'] as LeaderboardSubTab[]).map(st => (
          <button
            key={st}
            className={`auth-tab${subTab === st ? ' active' : ''}`}
            onClick={() => setSubTab(st)}
          >
            {st === 'average' ? 'Average Score' : st === 'by-exercise' ? 'By Exercise' : 'Progress Matrix'}
          </button>
        ))}
      </div>

      {/* Average Score */}
      {subTab === 'average' && (
        <>
          {avgQuery.isLoading && (
            <div className="loading-state"><div className="spinner" /><p>Loading leaderboard…</p></div>
          )}
          {avgQuery.isError && (
            <p className="alert alert-error">Failed to load leaderboard.</p>
          )}
          {avgQuery.data && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', width: '3rem' }}>Rank</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Name</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Exercises Completed</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Avg Score</th>
                </tr>
              </thead>
              <tbody>
                {avgQuery.data.leaderboard.map(entry => (
                  <tr key={entry.name} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '0.75rem 0.5rem', fontFamily: 'monospace', opacity: 0.6 }}>
                      #{entry.rank}
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>{entry.name}</td>
                    <td style={{ padding: '0.75rem 0.5rem', opacity: 0.7 }}>{entry.exercises_completed}</td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>
                      <span style={{ fontFamily: 'monospace', color: entry.average_score >= 80 ? '#6ee7b7' : undefined }}>
                        {Math.round(entry.average_score)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {avgQuery.data?.leaderboard.length === 0 && (
            <div className="empty-state">
              <p className="empty-state-title">No submissions yet</p>
              <p className="empty-state-hint">Students haven't completed any exercises yet.</p>
            </div>
          )}
        </>
      )}

      {/* By Exercise */}
      {subTab === 'by-exercise' && (
        <>
          <div className="form-group" style={{ maxWidth: '320px', marginBottom: '1rem' }}>
            <label htmlFor="lb-exercise-select">Select Exercise</label>
            <select
              id="lb-exercise-select"
              value={selectedExerciseId}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedExerciseId(e.target.value)}
            >
              <option value="">Choose an exercise…</option>
              {exercises.map(ex => (
                <option key={ex.exercise_id} value={ex.exercise_id}>{ex.title}</option>
              ))}
            </select>
          </div>
          {!selectedExerciseId && (
            <p style={{ opacity: 0.5 }}>Select an exercise to view its leaderboard.</p>
          )}
          {selectedExerciseId && exLeaderQuery.isLoading && (
            <div className="loading-state"><div className="spinner" /><p>Loading…</p></div>
          )}
          {selectedExerciseId && exLeaderQuery.data && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', width: '3rem' }}>Rank</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Name</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Score</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Submitted</th>
                </tr>
              </thead>
              <tbody>
                {exLeaderQuery.data.leaderboard.map(entry => (
                  <tr key={`${entry.name}-${entry.rank}`} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '0.75rem 0.5rem', fontFamily: 'monospace', opacity: 0.6 }}>#{entry.rank}</td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>{entry.name}</td>
                    <td style={{ padding: '0.75rem 0.5rem', fontFamily: 'monospace', color: entry.score >= 80 ? '#6ee7b7' : undefined }}>
                      {Math.round(entry.score)}%
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem', opacity: 0.6, fontSize: '0.8rem' }}>
                      {formatDate(entry.submitted_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {selectedExerciseId && exLeaderQuery.data?.leaderboard.length === 0 && (
            <div className="empty-state">
              <p className="empty-state-title">No submissions yet</p>
            </div>
          )}
        </>
      )}

      {/* Progress Matrix */}
      {subTab === 'matrix' && (
        <>
          {!progressData && (
            <div className="loading-state"><div className="spinner" /><p>Loading matrix…</p></div>
          )}
          {progressData && (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '0.5rem', minWidth: '120px', position: 'sticky', left: 0, background: 'var(--bg, #0d1117)', zIndex: 1 }}>
                      Student
                    </th>
                    {progressData.exercises.map(ex => (
                      <th
                        key={ex.id}
                        style={{ padding: '0.5rem', maxWidth: '80px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 400, opacity: 0.7 }}
                        title={ex.title}
                      >
                        {ex.title.length > 10 ? ex.title.slice(0, 10) + '…' : ex.title}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {progressData.students.map(student => (
                    <tr key={student.user_id}>
                      <td style={{ padding: '0.5rem', position: 'sticky', left: 0, background: 'var(--bg, #0d1117)', zIndex: 1, whiteSpace: 'nowrap' }}>
                        {student.name}
                      </td>
                      {progressData.exercises.map(ex => {
                        const entry = student.progress[ex.id]
                        const completed = entry?.completed ?? false
                        const score = entry?.score
                        return (
                          <td
                            key={ex.id}
                            title={completed ? (score !== undefined ? `${Math.round(score)}%` : 'Completed') : 'Not attempted'}
                            style={{
                              padding: '0.5rem',
                              textAlign: 'center',
                              background: cellColor(score, completed),
                              borderRadius: '2px',
                              cursor: 'default',
                              minWidth: '48px',
                            }}
                          >
                            {completed
                              ? (score !== undefined ? `${Math.round(score)}%` : '✓')
                              : <span style={{ opacity: 0.2 }}>—</span>}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', fontSize: '0.75rem', opacity: 0.7 }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span style={{ width: '12px', height: '12px', background: 'rgba(16,185,129,0.3)', borderRadius: '2px', display: 'inline-block' }} />
                  ≥90%
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span style={{ width: '12px', height: '12px', background: 'rgba(96,165,250,0.3)', borderRadius: '2px', display: 'inline-block' }} />
                  70–89%
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span style={{ width: '12px', height: '12px', background: 'rgba(245,158,11,0.3)', borderRadius: '2px', display: 'inline-block' }} />
                  50–69%
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span style={{ width: '12px', height: '12px', background: 'rgba(239,68,68,0.3)', borderRadius: '2px', display: 'inline-block' }} />
                  &lt;50%
                </span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function ProfessorClass() {
  const { classId } = useParams<{ classId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [activeTab, setActiveTab] = useState<Tab>('chapters')
  const [editClassOpen, setEditClassOpen] = useState(false)
  const [copiedCode, setCopiedCode] = useState(false)

  // --- Class detail ---
  const classQuery = useQuery({
    queryKey: ['classDetail', classId],
    queryFn: async () => {
      const r = await apiClient.get<{ class_id: string; name: string; description?: string; professor_name?: string; student_count?: number; chapter_count?: number; exercise_count?: number; join_code?: string }>(`/classes/${classId}`)
      if (!r.ok) throw new Error(r.error ?? 'Failed to load class')
      return r.data as ClassDetail
    },
    enabled: !!classId,
  })

  // --- Chapters ---
  const chaptersQuery = useQuery({
    queryKey: ['chapters', classId],
    queryFn: async () => {
      const r = await apiClient.get<{ chapters: Chapter[] }>(`/classes/${classId}/chapters`)
      if (!r.ok) throw new Error(r.error ?? 'Failed to load chapters')
      return r.data as { chapters: Chapter[] }
    },
    enabled: !!classId,
  })

  // --- Progress (used by Students + Leaderboard matrix) ---
  const progressQuery = useQuery({
    queryKey: ['progress', classId],
    queryFn: async () => {
      const r = await apiClient.get<ProgressData>(`/classes/${classId}/progress`)
      if (!r.ok) throw new Error(r.error ?? 'Failed to load progress')
      return r.data as ProgressData
    },
    enabled: !!classId && (activeTab === 'students' || activeTab === 'leaderboard'),
  })

  // --- All exercises flat list (for leaderboard by-exercise dropdown) ---
  const chapters = chaptersQuery.data?.chapters ?? []
  const allExercisesQuery = useQuery({
    queryKey: ['exercises-flat', classId],
    queryFn: async () => {
      const results = await Promise.all(
        chapters.map(ch =>
          apiClient.get<{ exercises: Exercise[] }>(`/chapters/${ch.chapter_id}/exercises`)
            .then(r => r.ok ? ((r.data as { exercises: Exercise[] })?.exercises ?? []) : [])
        )
      )
      return results.flat()
    },
    enabled: !!classId && activeTab === 'leaderboard' && chapters.length > 0,
  })

  function handleCopyCode() {
    const code = classQuery.data?.join_code ?? classId ?? ''
    navigator.clipboard.writeText(code).then(() => {
      setCopiedCode(true)
      setTimeout(() => setCopiedCode(false), 2000)
    })
  }

  const classDetail = classQuery.data

  // --- Loading / error states ---
  if (classQuery.isLoading) {
    return (
      <div className="page">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading class…</p>
        </div>
      </div>
    )
  }

  if (classQuery.isError || !classDetail) {
    return (
      <div className="page">
        <div className="empty-state">
          <p className="empty-state-title">Failed to load class</p>
          <p className="empty-state-hint">Check your connection and try again.</p>
          <button className="btn btn-ghost" onClick={() => navigate(-1)}>← Go back</button>
        </div>
      </div>
    )
  }

  const TABS: { key: Tab; label: string }[] = [
    { key: 'chapters', label: 'Chapters' },
    { key: 'exercises', label: 'Exercises' },
    { key: 'resources', label: 'Resources' },
    { key: 'students', label: 'Students' },
    { key: 'leaderboard', label: 'Leaderboard' },
  ]

  return (
    <div className="page">
      {/* Breadcrumb */}
      <div className="breadcrumb" style={{ marginBottom: '1rem' }}>
        <button className="btn btn-link" onClick={() => navigate(-1)} style={{ padding: 0 }}>
          dashboard
        </button>
        <span className="breadcrumb-sep" style={{ margin: '0 0.4rem', opacity: 0.5 }}>›</span>
        <span className="breadcrumb-item breadcrumb-item--active">{classDetail.name}</span>
      </div>

      {/* Class header */}
      <div className="class-card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-tab-header">
          <div>
            <h1 style={{ margin: '0 0 0.25rem', fontSize: '1.4rem' }}>{classDetail.name}</h1>
            {classDetail.professor_name && (
              <p style={{ margin: 0, opacity: 0.6, fontSize: '0.875rem' }}>
                {classDetail.professor_name}
              </p>
            )}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => setEditClassOpen(true)}>
            Edit Class
          </button>
        </div>

        <div className="card-body">
          {classDetail.description && (
            <p style={{ margin: '0 0 1rem', opacity: 0.75 }}>{classDetail.description}</p>
          )}

          {/* Class ID / join code badge */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <span className="badge badge-primary" style={{ fontFamily: 'monospace', fontSize: '0.875rem', letterSpacing: '0.05em' }}>
              {classDetail.join_code ?? classId}
            </span>
            <button className="btn btn-ghost btn-sm" onClick={handleCopyCode}>
              {copiedCode ? 'Copied!' : 'Copy Code'}
            </button>
          </div>

          {/* Stats */}
          <div className="card-stats">
            <div className="stat">
              <span className="stat-value">{classDetail.chapter_count ?? chapters.length}</span>
              <span className="stat-label">Chapters</span>
            </div>
            <div className="stat">
              <span className="stat-value">{classDetail.student_count ?? 0}</span>
              <span className="stat-label">Peers</span>
            </div>
            <div className="stat">
              <span className="stat-value">{classDetail.exercise_count ?? 0}</span>
              <span className="stat-label">Exercises</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="auth-tabs" style={{ marginBottom: '1.5rem' }}>
        {TABS.map(tab => (
          <button
            key={tab.key}
            className={`auth-tab${activeTab === tab.key ? ' active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'chapters' && (
        <ChaptersTab
          classId={classId!}
          chapters={chapters}
          isLoading={chaptersQuery.isLoading}
          onRefresh={() => queryClient.invalidateQueries({ queryKey: ['classDetail', classId] })}
        />
      )}

      {activeTab === 'exercises' && (
        <ExercisesTab
          classId={classId!}
          chapters={chapters}
        />
      )}

      {activeTab === 'resources' && (
        <ResourcesTab classId={classId!} />
      )}

      {activeTab === 'students' && (
        <StudentsTab
          classId={classId!}
          progressData={progressQuery.data ?? null}
        />
      )}

      {activeTab === 'leaderboard' && (
        <LeaderboardTab
          classId={classId!}
          progressData={progressQuery.data ?? null}
          exercises={allExercisesQuery.data ?? []}
        />
      )}

      {/* Edit class modal */}
      {editClassOpen && (
        <EditClassModal
          open={editClassOpen}
          classDetail={classDetail}
          classId={classId!}
          onClose={() => setEditClassOpen(false)}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ['classDetail', classId] })}
        />
      )}
    </div>
  )
}
