/**
 * StudentClass page — per-class view for students.
 * Migrated from student-class.html + student-class.js (931-line vanilla JS).
 *
 * Route: /classes/:classId
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Class, Chapter, Exercise } from '@/types'

// ---------------------------------------------------------------------------
// Supplemental types not yet in @/types
// ---------------------------------------------------------------------------

interface Resource {
  resource_id: string
  title: string
  description?: string
  resource_type: string
  resource_url: string
  is_default?: boolean
}

interface LeaderboardEntry {
  user_id: string
  name: string
  score: number
  rank?: number
}

// ---------------------------------------------------------------------------
// API response shapes
// ---------------------------------------------------------------------------

interface ClassDetailResponse {
  class: Class & { exercise_count?: number }
}

interface ChaptersResponse {
  chapters: (Chapter & { description?: string; pdf_filename?: string })[]
}

interface ExercisesResponse {
  exercises: Exercise[]
}

interface ResourcesResponse {
  all_resources: Resource[]
}

interface LeaderboardResponse {
  leaderboard: LeaderboardEntry[]
}

// ---------------------------------------------------------------------------
// Hardcoded default resources
// ---------------------------------------------------------------------------

const DEFAULT_RESOURCES: Resource[] = [
  {
    resource_id: 'default-colab',
    title: 'Google Colab',
    description: 'Free Jupyter notebooks in the cloud with GPU support.',
    resource_type: 'tool',
    resource_url: 'https://colab.research.google.com',
    is_default: true,
  },
  {
    resource_id: 'default-code-assistant',
    title: 'Code Assistant',
    description: 'AI-powered coding help built into AnalytIQ.',
    resource_type: 'tool',
    resource_url: '/code-assistant',
    is_default: true,
  },
  {
    resource_id: 'default-kaggle',
    title: 'Kaggle Datasets',
    description: 'Thousands of public datasets for machine learning and data analysis.',
    resource_type: 'dataset',
    resource_url: 'https://www.kaggle.com/datasets',
    is_default: true,
  },
  {
    resource_id: 'default-uci',
    title: 'UCI ML Repository',
    description: 'Classic machine learning datasets maintained by UC Irvine.',
    resource_type: 'dataset',
    resource_url: 'https://archive.ics.uci.edu',
    is_default: true,
  },
  {
    resource_id: 'default-nyc',
    title: 'NYC Open Data',
    description: 'Free public data published by New York City agencies.',
    resource_type: 'dataset',
    resource_url: 'https://opendata.cityofnewyork.us',
    is_default: true,
  },
  {
    resource_id: 'default-worldbank',
    title: 'World Bank Open Data',
    description: 'Global development data from the World Bank Group.',
    resource_type: 'dataset',
    resource_url: 'https://data.worldbank.org',
    is_default: true,
  },
]

// ---------------------------------------------------------------------------
// Difficulty badge
// ---------------------------------------------------------------------------

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: '#10b981',
  medium: '#f59e0b',
  hard: '#ef4444',
}

function DifficultyBadge({ difficulty }: { difficulty?: string }) {
  if (!difficulty) return null
  const color = DIFFICULTY_COLORS[difficulty] ?? '#6b7280'
  return (
    <span
      className="badge"
      style={{ backgroundColor: color, color: '#fff', textTransform: 'capitalize' }}
    >
      {difficulty}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Tab IDs
// ---------------------------------------------------------------------------

type TabId = 'chapters' | 'exercises' | 'resources' | 'leaderboard'

const TABS: { id: TabId; label: string }[] = [
  { id: 'chapters',    label: '01 Chapters' },
  { id: 'exercises',   label: '02 Exercises' },
  { id: 'resources',   label: '03 Resources' },
  { id: 'leaderboard', label: '04 Leaderboard' },
]

// ---------------------------------------------------------------------------
// Chapters tab
// ---------------------------------------------------------------------------

function ChaptersTab({
  classId,
  chapters,
  isLoading,
  isError,
}: {
  classId: string
  chapters: ChaptersResponse['chapters']
  isLoading: boolean
  isError: boolean
}) {
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <p>Loading chapters…</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="alert alert-error">
        Failed to load chapters. Please try again.
      </div>
    )
  }

  if (chapters.length === 0) {
    return (
      <div className="empty-state">
        <p className="empty-state-title">No chapters yet</p>
        <p className="empty-state-hint">Your professor hasn&apos;t added any chapters to this class.</p>
      </div>
    )
  }

  function formatDate(dateStr?: string): string {
    if (!dateStr) return ''
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
    })
  }

  return (
    <div className="chapters-grid">
      {chapters.map((chapter, i) => {
        const hasPdf = !!(chapter.pdf_url || chapter.pdf_filename)
        return (
          <div key={chapter.chapter_id} className="class-card">
            <div className="card-tab-header">
              <div className="card-tab-label">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <span>[module_{i + 1}]</span>
              </div>
              <div className="card-tab-badges">
                {chapter.created_at && (
                  <span className="badge">{formatDate(chapter.created_at)}</span>
                )}
                <div className="card-indicator" />
              </div>
            </div>

            <div className="card-body">
              <h3 className="card-title">{chapter.title}</h3>
              {chapter.description && (
                <p className="card-description">{chapter.description}</p>
              )}

              <div className="card-stats">
                <div className="stat">
                  <span className="stat-value">{chapter.exercise_count ?? 0}</span>
                  <span className="stat-label">Exercises</span>
                </div>
              </div>

              {hasPdf && (
                <div className="card-footer">
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() =>
                      navigate(
                        `/chapter/${encodeURIComponent(chapter.chapter_id)}?classId=${encodeURIComponent(classId)}`,
                      )
                    }
                  >
                    Open Chapter
                  </button>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Exercises tab
// ---------------------------------------------------------------------------

function ExercisesTab({
  classId,
  chapters,
  chaptersLoading,
  chaptersError,
  exercisesByChapter,
  exercisesLoading,
}: {
  classId: string
  chapters: ChaptersResponse['chapters']
  chaptersLoading: boolean
  chaptersError: boolean
  exercisesByChapter: Map<string, Exercise[]>
  exercisesLoading: boolean
}) {
  const navigate = useNavigate()

  if (chaptersLoading || exercisesLoading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <p>Loading exercises…</p>
      </div>
    )
  }

  if (chaptersError) {
    return (
      <div className="alert alert-error">
        Failed to load exercises. Please try again.
      </div>
    )
  }

  const hasAny = chapters.some(ch => (exercisesByChapter.get(ch.chapter_id) ?? []).length > 0)

  if (!hasAny) {
    return (
      <div className="empty-state">
        <p className="empty-state-title">No exercises yet</p>
        <p className="empty-state-hint">Exercises will appear here once your professor adds them.</p>
      </div>
    )
  }

  return (
    <div>
      {chapters.map(chapter => {
        const exercises = exercisesByChapter.get(chapter.chapter_id) ?? []
        if (exercises.length === 0) return null
        return (
          <div key={chapter.chapter_id} className="exercise-group">
            <h3 className="exercise-group-title">{chapter.title}</h3>
            <div className="exercises-grid">
              {exercises.map(exercise => (
                <div key={exercise.exercise_id} className="class-card">
                  <div className="card-tab-header">
                    <div className="card-tab-label">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="16 18 22 12 16 6" />
                        <polyline points="8 6 2 12 8 18" />
                      </svg>
                      <span>{exercise.exercise_id}</span>
                    </div>
                    <div className="card-tab-badges">
                      <DifficultyBadge difficulty={exercise.difficulty} />
                      <div className="card-indicator" />
                    </div>
                  </div>

                  <div className="card-body">
                    <h4 className="card-title">{exercise.title}</h4>
                    {exercise.description && (
                      <p className="card-description">{exercise.description}</p>
                    )}

                    <div className="card-footer">
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() =>
                          navigate(
                            `/exercise/${encodeURIComponent(exercise.exercise_id)}?classId=${encodeURIComponent(classId)}&chapterId=${encodeURIComponent(exercise.chapter_id)}`,
                          )
                        }
                      >
                        Execute
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Resources tab
// ---------------------------------------------------------------------------

function ResourcesTab({ classId }: { classId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['classResources', classId],
    queryFn: async () => {
      const result = await apiClient.get<ResourcesResponse>(
        `/classes/${classId}/resources`,
      )
      if (!result.ok) throw new Error(result.error ?? 'Failed to load resources')
      return result.data
    },
  })

  if (isLoading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <p>Loading resources…</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="alert alert-error">
        Failed to load resources. Please try again.
      </div>
    )
  }

  const apiResources: Resource[] = data?.all_resources ?? []
  const allResources = [...DEFAULT_RESOURCES, ...apiResources]

  // Group by type
  const byType = new Map<string, Resource[]>()
  for (const r of allResources) {
    const group = byType.get(r.resource_type) ?? []
    group.push(r)
    byType.set(r.resource_type, group)
  }

  return (
    <div>
      {Array.from(byType.entries()).map(([type, resources]) => (
        <div key={type} className="resource-group">
          <h3 className="resource-group-title" style={{ textTransform: 'capitalize' }}>
            {type}s
          </h3>
          <div className="resources-grid">
            {resources.map(resource => {
              const isInternal = resource.resource_url.startsWith('/')
              return (
                <div key={resource.resource_id} className="class-card">
                  <div className="card-tab-header">
                    <div className="card-tab-label">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                      </svg>
                      <span>{resource.resource_type}</span>
                    </div>
                    <div className="card-indicator" />
                  </div>

                  <div className="card-body">
                    <h4 className="card-title">{resource.title}</h4>
                    {resource.description && (
                      <p className="card-description">{resource.description}</p>
                    )}

                    <div className="card-footer">
                      <a
                        href={resource.resource_url}
                        className="btn btn-ghost btn-sm"
                        target={isInternal ? '_self' : '_blank'}
                        rel={isInternal ? undefined : 'noopener noreferrer'}
                      >
                        Visit Resource
                      </a>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Leaderboard tab
// ---------------------------------------------------------------------------

function LeaderboardTab({
  classId,
  allExercises,
}: {
  classId: string
  allExercises: Exercise[]
}) {
  const [subTab, setSubTab] = useState<'average' | 'by-exercise'>('average')
  const [selectedExerciseId, setSelectedExerciseId] = useState<string>('')

  const avgQuery = useQuery({
    queryKey: ['leaderboardAverage', classId],
    queryFn: async () => {
      const result = await apiClient.get<LeaderboardResponse>(
        `/classes/${classId}/leaderboard/average`,
      )
      if (!result.ok) throw new Error(result.error ?? 'Failed to load leaderboard')
      return result.data
    },
    enabled: subTab === 'average',
  })

  const exerciseQuery = useQuery({
    queryKey: ['leaderboardExercise', classId, selectedExerciseId],
    queryFn: async () => {
      const result = await apiClient.get<LeaderboardResponse>(
        `/classes/${classId}/leaderboard/exercise/${selectedExerciseId}`,
      )
      if (!result.ok) throw new Error(result.error ?? 'Failed to load leaderboard')
      return result.data
    },
    enabled: subTab === 'by-exercise' && !!selectedExerciseId,
  })

  const currentQuery = subTab === 'average' ? avgQuery : exerciseQuery
  const entries: LeaderboardEntry[] = currentQuery.data?.leaderboard ?? []

  function renderMedal(rank: number): string {
    if (rank === 1) return '🥇'
    if (rank === 2) return '🥈'
    if (rank === 3) return '🥉'
    return String(rank)
  }

  return (
    <div>
      {/* Sub-tabs */}
      <div className="auth-tabs" style={{ marginBottom: '1.5rem' }}>
        <button
          className={`auth-tab ${subTab === 'average' ? 'auth-tab--active' : ''}`}
          onClick={() => setSubTab('average')}
        >
          Average Score
        </button>
        <button
          className={`auth-tab ${subTab === 'by-exercise' ? 'auth-tab--active' : ''}`}
          onClick={() => setSubTab('by-exercise')}
        >
          By Exercise
        </button>
      </div>

      {/* By-exercise dropdown */}
      {subTab === 'by-exercise' && (
        <div style={{ marginBottom: '1.5rem' }}>
          {allExercises.length === 0 ? (
            <p className="empty-state-hint">No exercises available to select.</p>
          ) : (
            <select
              className="input-mono"
              value={selectedExerciseId}
              onChange={e => setSelectedExerciseId(e.target.value)}
            >
              <option value="">— Select an exercise —</option>
              {allExercises.map(ex => (
                <option key={ex.exercise_id} value={ex.exercise_id}>
                  {ex.title}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Results */}
      {currentQuery.isLoading && (
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading leaderboard…</p>
        </div>
      )}

      {currentQuery.isError && (
        <div className="alert alert-error">
          Failed to load leaderboard. Please try again.
        </div>
      )}

      {subTab === 'by-exercise' && !selectedExerciseId && !currentQuery.isLoading && (
        <div className="empty-state">
          <p className="empty-state-hint">Select an exercise to view its leaderboard.</p>
        </div>
      )}

      {!currentQuery.isLoading && !currentQuery.isError && entries.length === 0 &&
        (subTab === 'average' || !!selectedExerciseId) && (
        <div className="empty-state">
          <p className="empty-state-title">No entries yet</p>
          <p className="empty-state-hint">Complete exercises to appear on the leaderboard.</p>
        </div>
      )}

      {!currentQuery.isLoading && entries.length > 0 && (
        <div className="leaderboard-list">
          {entries.map((entry, i) => {
            const rank = entry.rank ?? i + 1
            return (
              <div key={entry.user_id} className="leaderboard-row">
                <span className="leaderboard-rank">{renderMedal(rank)}</span>
                <span className="leaderboard-name">{entry.name}</span>
                <span className="leaderboard-score">{entry.score.toFixed(1)}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function StudentClass() {
  const { classId } = useParams<{ classId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const initialTab = (searchParams.get('tab') as TabId | null) ?? 'chapters'
  const [activeTab, setActiveTab] = useState<TabId>(initialTab)
  const [copied, setCopied] = useState(false)

  // Sync tab if URL changes externally
  useEffect(() => {
    const tabParam = searchParams.get('tab') as TabId | null
    if (tabParam && TABS.some(t => t.id === tabParam)) {
      setActiveTab(tabParam)
    }
  }, [searchParams])

  // Class detail
  const classQuery = useQuery({
    queryKey: ['classDetail', classId],
    queryFn: async () => {
      const result = await apiClient.get<ClassDetailResponse>(`/classes/${classId}`)
      if (!result.ok) throw new Error(result.error ?? 'Failed to load class')
      return result.data
    },
    enabled: !!classId,
  })

  // Chapters — fetched once and shared across tabs
  const chaptersQuery = useQuery({
    queryKey: ['chapters', classId],
    queryFn: async () => {
      const result = await apiClient.get<ChaptersResponse>(`/classes/${classId}/chapters`)
      if (!result.ok) throw new Error(result.error ?? 'Failed to load chapters')
      return result.data
    },
    enabled: !!classId,
  })

  const chapters = chaptersQuery.data?.chapters ?? []

  // All exercises — parallel fetch per chapter; used in Exercises tab and Leaderboard dropdown
  const exercisesQuery = useQuery({
    queryKey: ['allExercises', classId, chapters.map(c => c.chapter_id).join(',')],
    queryFn: async () => {
      const results = await Promise.all(
        chapters.map(ch =>
          apiClient.get<ExercisesResponse>(`/chapters/${ch.chapter_id}/exercises`),
        ),
      )
      const byChapter = new Map<string, Exercise[]>()
      for (let i = 0; i < chapters.length; i++) {
        const r = results[i]
        byChapter.set(chapters[i].chapter_id, r.data?.exercises ?? [])
      }
      return byChapter
    },
    enabled: chapters.length > 0,
  })

  const exercisesByChapter: Map<string, Exercise[]> = exercisesQuery.data ?? new Map()
  const allExercises: Exercise[] = Array.from(exercisesByChapter.values()).flat()

  function handleCopy() {
    if (!classId) return
    navigator.clipboard.writeText(classId).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const cls = classQuery.data?.class

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="page">
      {/* Breadcrumb */}
      <div className="page-header">
        <div className="breadcrumb">
          <button className="breadcrumb-item btn btn-link" onClick={() => navigate('/classes')}>
            classes
          </button>
          <span className="breadcrumb-sep">›</span>
          <span className="breadcrumb-item breadcrumb-item--active">
            {cls?.name ?? classId}
          </span>
        </div>
      </div>

      {/* Class loading / error */}
      {classQuery.isLoading && (
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading class…</p>
        </div>
      )}

      {classQuery.isError && (
        <div className="alert alert-error">
          Failed to load class details. Please try again.
        </div>
      )}

      {/* Class header card */}
      {cls && (
        <div className="class-card" style={{ marginBottom: '2rem' }}>
          <div className="card-tab-header">
            <div className="card-tab-label">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
              <span>{classId}.workspace</span>
            </div>
            <div className="card-tab-badges">
              <div className="card-indicator" />
            </div>
          </div>

          <div className="card-body">
            <div className="card-title-row">
              <h1 className="card-title--large">{cls.name}</h1>
            </div>

            {cls.description && (
              <p className="card-description">{cls.description}</p>
            )}

            {cls.professor_name && (
              <p className="card-professor">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                Prof. {cls.professor_name}
              </p>
            )}

            {/* Class ID with copy button */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
              <span className="card-professor" style={{ fontFamily: 'monospace' }}>
                ID: {classId}
              </span>
              <button className="btn btn-ghost btn-sm" onClick={handleCopy}>
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>

            <div className="card-stats" style={{ marginTop: '1rem' }}>
              <div className="stat">
                <span className="stat-value">{cls.chapter_count ?? chapters.length}</span>
                <span className="stat-label">Chapters</span>
              </div>
              <div className="stat stat--border-left">
                <span className="stat-value">{cls.student_count ?? 0}</span>
                <span className="stat-label">Peers</span>
              </div>
              <div className="stat stat--border-left">
                <span className="stat-value">{(cls as ClassDetailResponse['class']).exercise_count ?? allExercises.length}</span>
                <span className="stat-label">Exercises</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      {cls && (
        <>
          <div className="auth-tabs" style={{ marginBottom: '1.5rem' }}>
            {TABS.map(tab => (
              <button
                key={tab.id}
                className={`auth-tab ${activeTab === tab.id ? 'auth-tab--active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'chapters' && (
            <ChaptersTab
              classId={classId!}
              chapters={chapters}
              isLoading={chaptersQuery.isLoading}
              isError={chaptersQuery.isError}
            />
          )}

          {activeTab === 'exercises' && (
            <ExercisesTab
              classId={classId!}
              chapters={chapters}
              chaptersLoading={chaptersQuery.isLoading}
              chaptersError={chaptersQuery.isError}
              exercisesByChapter={exercisesByChapter}
              exercisesLoading={exercisesQuery.isLoading}
            />
          )}

          {activeTab === 'resources' && (
            <ResourcesTab classId={classId!} />
          )}

          {activeTab === 'leaderboard' && (
            <LeaderboardTab classId={classId!} allExercises={allExercises} />
          )}
        </>
      )}
    </div>
  )
}
