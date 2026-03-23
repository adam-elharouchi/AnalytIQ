/**
 * UploadAssistant — PDF upload + AI exercise generation wizard.
 * Route: /upload-assistant?classId=<id>
 * Roles: professor, superadmin, tenant_admin
 */

import { useState, useRef, type ChangeEvent, type DragEvent } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Chapter } from '@/types'

// ---------------------------------------------------------------------------
// Local types
// ---------------------------------------------------------------------------

type ViewState = 'upload' | 'processing' | 'review'
type UploadMode = 'new' | 'existing'
type StageStatus = 'pending' | 'active' | 'done' | 'error'

interface Stage {
  label: string
  status: StageStatus
}

interface ReviewExercise {
  exercise_id: string
  title: string
  description: string
  difficulty: 'easy' | 'medium' | 'hard'
  solution_code: string
}

interface ChapterCreateResponse {
  chapter_id: string
  title: string
}

interface ExercisesApiResponse {
  exercises: Array<{
    exercise_id: string
    title?: string
    description?: string
    difficulty?: 'easy' | 'medium' | 'hard'
    solution_code?: string
  }>
}

const INITIAL_STAGES: Stage[] = [
  { label: 'Upload', status: 'pending' },
  { label: 'Read Content', status: 'pending' },
  { label: 'Analyze & Generate', status: 'pending' },
]

// ---------------------------------------------------------------------------
// Stage icon
// ---------------------------------------------------------------------------

function StageIcon({ status }: { status: StageStatus }) {
  if (status === 'active') {
    return <span className="spinner" style={{ width: 20, height: 20 }} />
  }
  if (status === 'done') {
    return <span className="stage-icon stage-icon--done" aria-label="Done">✓</span>
  }
  if (status === 'error') {
    return <span className="stage-icon stage-icon--error" aria-label="Error">✕</span>
  }
  return <span className="stage-icon stage-icon--pending" aria-label="Pending">○</span>
}

// ---------------------------------------------------------------------------
// Difficulty badge
// ---------------------------------------------------------------------------

function DifficultyBadge({ difficulty }: { difficulty: 'easy' | 'medium' | 'hard' }) {
  const colorMap = {
    easy: '#2ecc71',
    medium: '#f39c12',
    hard: '#e74c3c',
  }
  return (
    <span
      className="difficulty-badge"
      style={{
        backgroundColor: colorMap[difficulty],
        color: '#fff',
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: '0.75rem',
        fontWeight: 600,
        textTransform: 'capitalize',
      }}
    >
      {difficulty}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function UploadAssistant() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const classId = searchParams.get('classId')

  // View state
  const [view, setView] = useState<ViewState>('upload')
  const [uploadMode, setUploadMode] = useState<UploadMode>('new')

  // New chapter form
  const [chapterTitle, setChapterTitle] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [autoGenerate, setAutoGenerate] = useState(true)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Existing chapter form
  const [selectedExistingChapterId, setSelectedExistingChapterId] = useState('')

  // Processing state
  const [stages, setStages] = useState<Stage[]>(INITIAL_STAGES)
  const [processError, setProcessError] = useState<string | null>(null)

  // Review state
  const [exercises, setExercises] = useState<ReviewExercise[]>([])
  const [saveAlert, setSaveAlert] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  // ---------------------------------------------------------------------------
  // Chapters query (for existing chapter dropdown)
  // ---------------------------------------------------------------------------

  const chaptersQuery = useQuery({
    queryKey: ['chapters', classId],
    queryFn: async () => {
      const result = await apiClient.get<{ chapters: Chapter[] }>(`/classes/${classId}/chapters`)
      if (!result.ok) throw new Error(result.error ?? 'Failed to load chapters')
      return result.data!.chapters
    },
    enabled: !!classId,
  })

  // ---------------------------------------------------------------------------
  // Stage helpers
  // ---------------------------------------------------------------------------

  function setStageStatus(index: number, status: StageStatus) {
    setStages(prev => prev.map((s, i) => i === index ? { ...s, status } : s))
  }

  function resetStages() {
    setStages(INITIAL_STAGES.map(s => ({ ...s, status: 'pending' as StageStatus })))
  }

  // ---------------------------------------------------------------------------
  // File drop zone handlers
  // ---------------------------------------------------------------------------

  function handleDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave() {
    setIsDragging(false)
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file && file.name.endsWith('.pdf')) {
      setSelectedFile(file)
    }
  }

  function handleFileInputChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) setSelectedFile(file)
    e.target.value = ''
  }

  // ---------------------------------------------------------------------------
  // processUpload — new chapter flow
  // ---------------------------------------------------------------------------

  async function processUpload() {
    if (!classId || !selectedFile || !chapterTitle.trim()) return

    setProcessError(null)
    resetStages()
    setView('processing')

    // Stage 1: Upload PDF + create chapter
    setStageStatus(0, 'active')

    const formData = new FormData()
    formData.append('pdf_file', selectedFile)
    formData.append('title', chapterTitle.trim())
    formData.append('exercise_mode', autoGenerate ? 'auto' : 'manual')
    formData.append('chapter_number', '999')

    const uploadResult = await apiClient.upload<ChapterCreateResponse>(
      `/classes/${classId}/chapters`,
      formData,
    )

    if (!uploadResult.ok || !uploadResult.data) {
      setStageStatus(0, 'error')
      setProcessError(uploadResult.error ?? 'Upload failed')
      return
    }

    const chapterId = uploadResult.data.chapter_id
    setStageStatus(0, 'done')

    // Manual mode: skip generation
    if (!autoGenerate) {
      setStages(prev => prev.map((s, i) => ({
        ...s,
        status: i === 0 ? 'done' : 'pending',
      })))
      navigate(`/professor-class/${classId}`)
      return
    }

    // Stage 2 + 3: Generate exercises
    setStageStatus(1, 'active')
    setStageStatus(2, 'active')

    const genResult = await apiClient.post(`/chapters/${chapterId}/generate-exercises`, {})
    if (!genResult.ok) {
      setStageStatus(1, 'error')
      setStageStatus(2, 'error')
      setProcessError(genResult.error ?? 'Exercise generation failed')
      return
    }

    setStageStatus(1, 'done')
    setStageStatus(2, 'done')

    // Fetch exercises
    const exResult = await apiClient.get<ExercisesApiResponse>(`/chapters/${chapterId}/exercises`)
    if (!exResult.ok || !exResult.data) {
      setProcessError(exResult.error ?? 'Failed to load exercises')
      return
    }

    const loaded: ReviewExercise[] = (exResult.data.exercises ?? []).map(ex => ({
      exercise_id: ex.exercise_id,
      title: ex.title ?? '',
      description: ex.description ?? '',
      difficulty: ex.difficulty ?? 'medium',
      solution_code: ex.solution_code ?? '',
    }))

    setExercises(loaded)
    setView('review')
  }

  // ---------------------------------------------------------------------------
  // processExisting — existing chapter flow
  // ---------------------------------------------------------------------------

  async function processExisting() {
    if (!selectedExistingChapterId) return

    setProcessError(null)
    resetStages()
    setView('processing')

    // Stage 1 is immediate for existing chapters
    setStageStatus(0, 'done')

    // Stage 2 + 3: Generate
    setStageStatus(1, 'active')
    setStageStatus(2, 'active')

    const genResult = await apiClient.post(
      `/chapters/${selectedExistingChapterId}/generate-exercises`,
      {},
    )
    if (!genResult.ok) {
      setStageStatus(1, 'error')
      setStageStatus(2, 'error')
      setProcessError(genResult.error ?? 'Exercise generation failed')
      return
    }

    setStageStatus(1, 'done')
    setStageStatus(2, 'done')

    const exResult = await apiClient.get<ExercisesApiResponse>(
      `/chapters/${selectedExistingChapterId}/exercises`,
    )
    if (!exResult.ok || !exResult.data) {
      setProcessError(exResult.error ?? 'Failed to load exercises')
      return
    }

    const loaded: ReviewExercise[] = (exResult.data.exercises ?? []).map(ex => ({
      exercise_id: ex.exercise_id,
      title: ex.title ?? '',
      description: ex.description ?? '',
      difficulty: ex.difficulty ?? 'medium',
      solution_code: ex.solution_code ?? '',
    }))

    setExercises(loaded)
    setView('review')
  }

  // ---------------------------------------------------------------------------
  // saveAll — review view
  // ---------------------------------------------------------------------------

  async function saveAll() {
    setSaveAlert(null)
    setIsSaving(true)

    const results = await Promise.all(
      exercises.map(ex =>
        apiClient.put(`/exercises/${ex.exercise_id}`, {
          title: ex.title,
          description: ex.description,
          difficulty: ex.difficulty,
          solution_code: ex.solution_code,
        }),
      ),
    )

    setIsSaving(false)

    const failed = results.filter(r => !r.ok)
    if (failed.length > 0) {
      setSaveAlert({ message: `Failed to save ${failed.length} exercise(s). Please try again.`, type: 'error' })
      return
    }

    navigate(`/professor-class/${classId}`)
  }

  // ---------------------------------------------------------------------------
  // Guard: no classId
  // ---------------------------------------------------------------------------

  if (!classId) {
    return (
      <div className="page">
        <div className="alert alert-error">
          No class specified. Please navigate here from a class page.
        </div>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => navigate(-1)}
          style={{ marginTop: '1rem' }}
        >
          Go Back
        </button>
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Render: processing view
  // ---------------------------------------------------------------------------

  if (view === 'processing') {
    return (
      <div className="page">
        <div className="page-header">
          <div className="breadcrumb">
            <span className="breadcrumb-item">class</span>
            <span className="breadcrumb-sep">›</span>
            <span className="breadcrumb-item breadcrumb-item--active">upload assistant</span>
          </div>
        </div>

        <div className="processing-container">
          <h2 style={{ marginBottom: '1.5rem' }}>Processing your upload…</h2>

          <div className="stages-list">
            {stages.map((stage, i) => (
              <div key={i} className={`stage-row stage-row--${stage.status}`}>
                <StageIcon status={stage.status} />
                <span className="stage-label">{stage.label}</span>
              </div>
            ))}
          </div>

          {processError && (
            <div className="alert alert-error" style={{ marginTop: '1.5rem' }}>
              {processError}
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => { setView('upload'); resetStages() }}
                style={{ marginLeft: '1rem' }}
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Render: review view
  // ---------------------------------------------------------------------------

  if (view === 'review') {
    return (
      <div className="page">
        <div className="page-header">
          <div className="breadcrumb">
            <Link to={`/professor-class/${classId}`} className="breadcrumb-item">class</Link>
            <span className="breadcrumb-sep">›</span>
            <span className="breadcrumb-item breadcrumb-item--active">review exercises</span>
          </div>

          <button
            type="button"
            className="btn btn-primary"
            onClick={saveAll}
            disabled={isSaving}
          >
            {isSaving ? 'Saving…' : 'Save All'}
          </button>
        </div>

        {saveAlert && (
          <div className={`alert ${saveAlert.type === 'error' ? 'alert-error' : 'alert-success'}`}>
            {saveAlert.message}
          </div>
        )}

        {exercises.length === 0 ? (
          <div className="alert alert-success">
            No exercises were generated. You can add them manually from the class page.
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => navigate(`/professor-class/${classId}`)}
              style={{ marginLeft: '1rem' }}
            >
              Go to Class
            </button>
          </div>
        ) : (
          <div className="exercise-review-list">
            {exercises.map((ex, i) => (
              <div key={ex.exercise_id} className="exercise-review-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                  <span style={{ fontWeight: 600, color: '#666' }}>#{i + 1}</span>
                  <DifficultyBadge difficulty={ex.difficulty} />
                </div>

                <div className="form-group">
                  <label htmlFor={`ex-title-${ex.exercise_id}`}>Title</label>
                  <input
                    id={`ex-title-${ex.exercise_id}`}
                    type="text"
                    value={ex.title}
                    onChange={e => setExercises(prev =>
                      prev.map(item =>
                        item.exercise_id === ex.exercise_id
                          ? { ...item, title: e.target.value }
                          : item,
                      ),
                    )}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor={`ex-desc-${ex.exercise_id}`}>Description</label>
                  <textarea
                    id={`ex-desc-${ex.exercise_id}`}
                    rows={3}
                    value={ex.description}
                    onChange={e => setExercises(prev =>
                      prev.map(item =>
                        item.exercise_id === ex.exercise_id
                          ? { ...item, description: e.target.value }
                          : item,
                      ),
                    )}
                  />
                </div>

                {ex.solution_code && (
                  <div className="form-group">
                    <label>Solution Code</label>
                    <div
                      style={{
                        fontFamily: 'monospace',
                        fontSize: '0.85rem',
                        backgroundColor: '#1e1e2e',
                        color: '#cdd6f4',
                        padding: '0.75rem 1rem',
                        borderRadius: 6,
                        overflowX: 'auto',
                        whiteSpace: 'pre',
                        maxHeight: 200,
                        overflowY: 'auto',
                      }}
                    >
                      {ex.solution_code}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Render: upload view (default)
  // ---------------------------------------------------------------------------

  const chapters = chaptersQuery.data ?? []

  return (
    <div className="page">
      <div className="page-header">
        <div className="breadcrumb">
          <Link to={`/professor-class/${classId}`} className="breadcrumb-item">class</Link>
          <span className="breadcrumb-sep">›</span>
          <span className="breadcrumb-item breadcrumb-item--active">upload assistant</span>
        </div>
      </div>

      <div className="upload-container">
        {/* Mode selector */}
        <div className="upload-mode-selector">
          <label className="radio-option">
            <input
              type="radio"
              name="upload-mode"
              value="new"
              checked={uploadMode === 'new'}
              onChange={() => setUploadMode('new')}
            />
            <span>New Chapter</span>
          </label>
          <label className="radio-option">
            <input
              type="radio"
              name="upload-mode"
              value="existing"
              checked={uploadMode === 'existing'}
              onChange={() => setUploadMode('existing')}
            />
            <span>Existing Chapter</span>
          </label>
        </div>

        {/* New chapter form */}
        {uploadMode === 'new' && (
          <div className="upload-form">
            <div className="form-group">
              <label htmlFor="chapter-title">Chapter Title <span style={{ color: '#e74c3c' }}>*</span></label>
              <input
                id="chapter-title"
                type="text"
                value={chapterTitle}
                onChange={e => setChapterTitle(e.target.value)}
                placeholder="e.g. Introduction to Pandas"
                required
              />
            </div>

            <div className="form-group">
              <label>PDF File</label>
              <div
                className={`drop-zone ${isDragging ? 'drop-zone--active' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click() }}
                aria-label="Drop a PDF here or click to browse"
              >
                {selectedFile ? (
                  <span className="drop-zone-filename">{selectedFile.name}</span>
                ) : (
                  <span className="drop-zone-hint">
                    Drop a PDF here or <u>click to browse</u>
                  </span>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                style={{ display: 'none' }}
                onChange={handleFileInputChange}
              />
            </div>

            <div className="form-group">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={autoGenerate}
                  onChange={e => setAutoGenerate(e.target.checked)}
                />
                <span>Auto-generate exercises</span>
              </label>
              <p className="form-hint">
                When checked, AI will analyze the PDF and generate exercises automatically.
              </p>
            </div>

            <button
              type="button"
              className="btn btn-primary"
              disabled={!selectedFile || !chapterTitle.trim()}
              onClick={processUpload}
            >
              Upload
            </button>
          </div>
        )}

        {/* Existing chapter form */}
        {uploadMode === 'existing' && (
          <div className="upload-form">
            <div className="form-group">
              <label htmlFor="existing-chapter">Select Chapter</label>
              {chaptersQuery.isLoading ? (
                <div className="loading-state">
                  <div className="spinner" />
                  <p>Loading chapters…</p>
                </div>
              ) : (
                <select
                  id="existing-chapter"
                  value={selectedExistingChapterId}
                  onChange={e => setSelectedExistingChapterId(e.target.value)}
                >
                  <option value="">— select a chapter —</option>
                  {chapters.map(ch => (
                    <option key={ch.chapter_id} value={ch.chapter_id}>
                      {ch.title}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <button
              type="button"
              className="btn btn-primary"
              disabled={!selectedExistingChapterId}
              onClick={processExisting}
            >
              Generate Exercises
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
