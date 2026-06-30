/**
 * ChapterView page — displays a chapter's PDF via iframe.
 * Route: /chapter/:chapterId?classId=...
 * Migrated from the legacy pdf.js canvas-rendering approach.
 */

import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

interface ChapterResponse {
  chapter_id: string
  title: string
  description?: string
  class_id: string
  pdf_url?: string
  source_type?: string
  created_at?: string
}

export default function ChapterView() {
  const { chapterId } = useParams<{ chapterId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const classId = searchParams.get('classId') ?? ''

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['chapter', chapterId],
    queryFn: async () => {
      const result = await apiClient.get<ChapterResponse>(`/chapters/${chapterId}`)
      if (!result.ok) throw new Error(result.error ?? 'Failed to load chapter')
      return result.data
    },
    enabled: Boolean(chapterId),
  })

  // The PDF endpoint is loaded via <iframe> and cannot send an Authorization
  // header, so we mint a short-lived capability token and append it as ?token=.
  const { data: tokenData } = useQuery({
    queryKey: ['chapter-token', chapterId],
    queryFn: async () => {
      const result = await apiClient.get<{ token: string }>(
        `/chapters/${chapterId}/access-token`,
      )
      if (!result.ok) throw new Error(result.error ?? 'Failed to authorize chapter')
      return result.data
    },
    enabled: Boolean(chapterId) && Boolean(data?.pdf_url),
  })

  const pdfSrc =
    data?.pdf_url && tokenData?.token
      ? `${data.pdf_url}${data.pdf_url.includes('?') ? '&' : '?'}token=${encodeURIComponent(
          tokenData.token,
        )}`
      : null

  const backHref = classId ? `/class/${encodeURIComponent(classId)}` : '/classes'

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
          <span className="breadcrumb-sep">›</span>
          <span className="breadcrumb-item breadcrumb-item--active">
            {isLoading ? 'loading…' : (data?.title ?? 'chapter')}
          </span>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading chapter…</p>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="alert alert-error">
          {error instanceof Error ? error.message : 'Failed to load chapter. Please try again.'}
        </div>
      )}

      {/* Content */}
      {!isLoading && !isError && data && (
        <>
          {/* Chapter meta */}
          <div style={{ marginBottom: '1rem' }}>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.375rem' }}>
              {data.title}
            </h1>
            {data.description && (
              <p style={{ color: 'var(--text-muted, #94a3b8)', fontSize: '0.875rem' }}>
                {data.description}
              </p>
            )}
          </div>

          {/* PDF viewer */}
          {data.pdf_url ? (
            pdfSrc ? (
              <iframe
                src={pdfSrc}
                title={data.title}
                style={{
                  width: '100%',
                  height: 'calc(100vh - 200px)',
                  border: 'none',
                  borderRadius: '0.5rem',
                  display: 'block',
                }}
              />
            ) : (
              <div className="loading-state">
                <div className="spinner" />
                <p>Authorizing…</p>
              </div>
            )
          ) : (
            <div className="empty-state">
              <p className="empty-state-title">No PDF available</p>
              <p className="empty-state-hint">No PDF has been uploaded for this chapter yet.</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
