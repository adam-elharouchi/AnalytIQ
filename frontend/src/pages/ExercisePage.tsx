/**
 * ExercisePage — code editor + AI grading for a single exercise.
 * Route: /exercise/:exerciseId?classId=...&chapterId=...
 * Replaces the legacy practice-playground.html.
 */

import { useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ExerciseResponse {
  exercise_id: string
  chapter_id: string
  title: string
  description?: string
  difficulty?: 'easy' | 'medium' | 'hard'
  exercise_type?: string
  points?: number
}

interface GradePayload {
  code: string
  class_id: string
}

interface GradeResult {
  success: boolean
  score?: number
  feedback?: string
  passed?: boolean
  error?: string
}

// ---------------------------------------------------------------------------
// Difficulty badge
// ---------------------------------------------------------------------------

const DIFFICULTY_STYLES: Record<
  'easy' | 'medium' | 'hard',
  React.CSSProperties
> = {
  easy: {
    color: '#6ee7b7',
    background: 'rgba(16,185,129,0.15)',
    border: '1px solid rgba(16,185,129,0.3)',
  },
  medium: {
    color: '#fcd34d',
    background: 'rgba(245,158,11,0.15)',
    border: '1px solid rgba(245,158,11,0.3)',
  },
  hard: {
    color: '#fca5a5',
    background: 'rgba(239,68,68,0.15)',
    border: '1px solid rgba(239,68,68,0.3)',
  },
}

function DifficultyBadge({ difficulty }: { difficulty?: 'easy' | 'medium' | 'hard' }) {
  if (!difficulty) return null
  return (
    <span
      style={{
        ...DIFFICULTY_STYLES[difficulty],
        fontSize: '0.7rem',
        fontWeight: 600,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        padding: '0.2rem 0.5rem',
        borderRadius: '0.25rem',
        display: 'inline-block',
      }}
    >
      {difficulty}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Code editor
// ---------------------------------------------------------------------------

interface CodeEditorProps {
  value: string
  onChange: (value: string) => void
  filename?: string
  disabled?: boolean
}

function CodeEditor({ value, onChange, filename = 'solution.py', disabled }: CodeEditorProps) {
  return (
    <div
      style={{
        borderRadius: '0.5rem',
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.1)',
        background: '#1e293b',
      }}
    >
      {/* macOS-style toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 0.75rem',
          background: '#0f172a',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
        }}
      >
        {/* Traffic-light dots */}
        <div style={{ display: 'flex', gap: '0.375rem' }}>
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#ef4444',
              display: 'inline-block',
            }}
          />
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#f59e0b',
              display: 'inline-block',
            }}
          />
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#22c55e',
              display: 'inline-block',
            }}
          />
        </div>
        <span
          style={{
            marginLeft: '0.5rem',
            fontSize: '0.75rem',
            color: '#64748b',
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          {filename}
        </span>
      </div>

      {/* Textarea */}
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        disabled={disabled}
        spellCheck={false}
        autoCapitalize="none"
        autoCorrect="off"
        style={{
          background: '#1e293b',
          color: '#f8fafc',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '14px',
          padding: '1rem',
          border: 'none',
          borderRadius: 0,
          width: '100%',
          minHeight: '300px',
          resize: 'vertical',
          outline: 'none',
          lineHeight: 1.6,
          boxSizing: 'border-box',
          display: 'block',
        }}
        placeholder="# Write your solution here…"
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Grading result panel
// ---------------------------------------------------------------------------

function GradeResultPanel({ result }: { result: GradeResult }) {
  const isPass = result.passed === true
  const hasFailed = result.passed === false || result.success === false

  return (
    <div
      className={isPass ? 'alert alert-success' : 'alert alert-error'}
      style={{ marginTop: '1rem' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <span style={{ fontWeight: 700, fontSize: '1rem' }}>
          {isPass ? 'Passed' : hasFailed ? 'Not quite' : 'Graded'}
        </span>
        {result.score !== undefined && (
          <span style={{ fontWeight: 600, opacity: 0.85 }}>
            Score: {result.score}
          </span>
        )}
      </div>

      {result.feedback && (
        <p style={{ margin: 0, fontSize: '0.875rem', lineHeight: 1.6 }}>
          {result.feedback}
        </p>
      )}

      {result.error && (
        <p
          style={{
            margin: result.feedback ? '0.5rem 0 0' : 0,
            fontSize: '0.8rem',
            fontFamily: "'JetBrains Mono', monospace",
            opacity: 0.8,
          }}
        >
          {result.error}
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ExercisePage() {
  const { exerciseId } = useParams<{ exerciseId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const classId = searchParams.get('classId') ?? ''
  const chapterId = searchParams.get('chapterId') ?? ''

  const [code, setCode] = useState('')
  const [gradeResult, setGradeResult] = useState<GradeResult | null>(null)

  // Fetch exercise metadata
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['exercise', exerciseId],
    queryFn: async () => {
      const result = await apiClient.get<ExerciseResponse>(`/exercises/${exerciseId}`)
      if (!result.ok) throw new Error(result.error ?? 'Failed to load exercise')
      return result.data
    },
    enabled: Boolean(exerciseId),
  })

  // Submit for grading
  const gradeMutation = useMutation({
    mutationFn: async (payload: GradePayload) => {
      const result = await apiClient.post<GradeResult>(
        `/exercises/${exerciseId}/grade`,
        payload,
      )
      if (!result.ok && !result.data) {
        throw new Error(result.error ?? 'Grading failed')
      }
      return result.data
    },
    onSuccess: (result) => {
      if (result) setGradeResult(result)
    },
    onError: (err) => {
      setGradeResult({
        success: false,
        error: err instanceof Error ? err.message : 'Grading request failed',
      })
    },
  })

  const backHref = classId ? `/class/${encodeURIComponent(classId)}` : '/classes'

  function handleSubmit() {
    if (!code.trim()) return
    setGradeResult(null)
    gradeMutation.mutate({ code, class_id: classId })
  }

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header">
        <div className="breadcrumb">
          <span className="breadcrumb-item">workspace</span>
          <span className="breadcrumb-sep">›</span>
          <button
            className="breadcrumb-item btn btn-ghost btn-sm"
            onClick={() => navigate(backHref)}
          >
            class
          </button>
          {chapterId && (
            <>
              <span className="breadcrumb-sep">›</span>
              <button
                className="breadcrumb-item btn btn-ghost btn-sm"
                onClick={() =>
                  navigate(
                    `/chapter/${encodeURIComponent(chapterId)}?classId=${encodeURIComponent(classId)}`,
                  )
                }
              >
                chapter
              </button>
            </>
          )}
          <span className="breadcrumb-sep">›</span>
          <span className="breadcrumb-item breadcrumb-item--active">
            {isLoading ? 'loading…' : (data?.title ?? 'exercise')}
          </span>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading exercise…</p>
        </div>
      )}

      {/* Fetch error */}
      {isError && (
        <div className="alert alert-error">
          {error instanceof Error ? error.message : 'Failed to load exercise. Please try again.'}
        </div>
      )}

      {/* Exercise content */}
      {!isLoading && !isError && data && (
        <>
          {/* Exercise header */}
          <div style={{ marginBottom: '1.25rem' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                marginBottom: '0.5rem',
              }}
            >
              <h1 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>
                {data.title}
              </h1>
              <DifficultyBadge difficulty={data.difficulty} />
              {data.points !== undefined && (
                <span
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-muted, #94a3b8)',
                    marginLeft: 'auto',
                  }}
                >
                  {data.points} pts
                </span>
              )}
            </div>

            {data.description && (
              <p
                style={{
                  color: 'var(--text-muted, #94a3b8)',
                  fontSize: '0.9rem',
                  lineHeight: 1.6,
                  margin: 0,
                }}
              >
                {data.description}
              </p>
            )}
          </div>

          {/* Code editor */}
          <CodeEditor
            value={code}
            onChange={setCode}
            filename="solution.py"
            disabled={gradeMutation.isPending}
          />

          {/* Submit button */}
          <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={gradeMutation.isPending || !code.trim()}
            >
              {gradeMutation.isPending ? (
                <>
                  <span className="spinner" style={{ width: 14, height: 14, marginRight: '0.5rem' }} />
                  Grading…
                </>
              ) : (
                'Run & Submit'
              )}
            </button>
          </div>

          {/* Grade result */}
          {gradeResult && <GradeResultPanel result={gradeResult} />}
        </>
      )}
    </div>
  )
}
