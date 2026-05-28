/**
 * CodeAssistant — AI chat assistant page.
 * Route: /code-assistant
 * Authenticated users only.
 */

import { useState, useEffect, useRef, useCallback, type KeyboardEvent, type ChangeEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface Conversation {
  id: string
  title: string
  date: string
  messages: Message[]
  archived: boolean
}

interface ConversationsResponse {
  conversations: Conversation[]
}

interface NewConversationResponse {
  conversation_id: string
  title: string
}

interface PreferencesResponse {
  currentLanguage: string
  geminiModel: string
}

interface ChatResponse {
  response: string
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const LANGUAGES = ['Python', 'JavaScript', 'SQL', 'R', 'Java', 'C++', 'TypeScript', 'Go', 'Rust', 'HTML']

const MODELS = [
  { value: 'gemini-2.5-flash', label: 'gemini-2.5-flash', description: 'Fast & efficient' },
  { value: 'gemini-2.5-pro',   label: 'gemini-2.5-pro',   description: 'Production reliable' },
  { value: 'gemini-2.0-flash', label: 'gemini-2.0-flash', description: 'Quick responses' },
  { value: 'gemini-2.0-pro',   label: 'gemini-2.0-pro',   description: 'Advanced reasoning' },
]

const STARTER_PROMPTS = [
  'Analyze sales data and create visualizations',
  'Build a predictive model for customer churn',
  'Perform statistical analysis on revenue trends',
  'Create a dashboard for business metrics',
]

// ---------------------------------------------------------------------------
// Markdown-lite renderer: wraps ``` fenced code blocks in <pre><code>
// ---------------------------------------------------------------------------

function renderContent(content: string): React.ReactNode {
  const parts = content.split(/(```[\s\S]*?```)/g)
  return parts.map((part, idx) => {
    if (part.startsWith('```')) {
      // Strip opening/closing fences and optional language tag
      const inner = part.replace(/^```[^\n]*\n?/, '').replace(/```$/, '')
      return (
        <pre
          key={idx}
          style={{
            background: '#0f172a',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '0.375rem',
            padding: '0.75rem 1rem',
            overflowX: 'auto',
            margin: '0.5rem 0',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.8rem',
            lineHeight: 1.6,
            color: '#e2e8f0',
            whiteSpace: 'pre',
          }}
        >
          <code>{inner}</code>
        </pre>
      )
    }
    // Plain text — preserve newlines
    return (
      <span key={idx} style={{ whiteSpace: 'pre-wrap' }}>
        {part}
      </span>
    )
  })
}

// ---------------------------------------------------------------------------
// Sidebar conversation item
// ---------------------------------------------------------------------------

interface ConvItemProps {
  conv: Conversation
  active: boolean
  onLoad: (id: string) => void
  onArchive: (id: string) => void
  onDelete: (id: string) => void
  isArchived: boolean
}

function ConvItem({ conv, active, onLoad, onArchive, onDelete, isArchived }: ConvItemProps) {
  return (
    <div
      onClick={() => onLoad(conv.id)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.5rem 0.75rem',
        borderRadius: '0.375rem',
        cursor: 'pointer',
        background: active ? 'rgba(99,102,241,0.15)' : 'transparent',
        border: active ? '1px solid rgba(99,102,241,0.3)' : '1px solid transparent',
        transition: 'background 0.15s',
      }}
      onMouseEnter={e => {
        if (!active) (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.04)'
      }}
      onMouseLeave={e => {
        if (!active) (e.currentTarget as HTMLDivElement).style.background = 'transparent'
      }}
    >
      {/* Text block */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: '0.8rem',
            fontWeight: 500,
            color: active ? '#a5b4fc' : '#cbd5e1',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {conv.title}
        </div>
        <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.1rem' }}>
          {new Date(conv.date).toLocaleDateString()}
        </div>
      </div>

      {/* Action buttons */}
      <div
        style={{ display: 'flex', gap: '0.25rem', flexShrink: 0 }}
        onClick={e => e.stopPropagation()}
      >
        {/* Archive / Unarchive */}
        {!isArchived && (
          <button
            onClick={() => onArchive(conv.id)}
            title="Archive"
            style={iconBtnStyle}
          >
            {/* Box / archive icon */}
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="21 8 21 21 3 21 3 8" />
              <rect x="1" y="3" width="22" height="5" />
              <line x1="10" y1="12" x2="14" y2="12" />
            </svg>
          </button>
        )}
        {/* Delete */}
        <button
          onClick={() => onDelete(conv.id)}
          title="Delete"
          style={{ ...iconBtnStyle, color: '#f87171' }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6l-1 14H6L5 6" />
            <path d="M10 11v6M14 11v6" />
            <path d="M9 6V4h6v2" />
          </svg>
        </button>
      </div>
    </div>
  )
}

const iconBtnStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  cursor: 'pointer',
  padding: '0.2rem',
  color: '#64748b',
  borderRadius: '0.25rem',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  lineHeight: 1,
  transition: 'color 0.15s',
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '1rem',
      }}
    >
      {/* Assistant avatar */}
      {!isUser && (
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            marginRight: '0.5rem',
            marginTop: '0.15rem',
            fontSize: '0.7rem',
            color: '#fff',
            fontWeight: 700,
          }}
        >
          AI
        </div>
      )}

      <div
        style={{
          maxWidth: '75%',
          padding: '0.65rem 0.9rem',
          borderRadius: isUser ? '1rem 1rem 0.25rem 1rem' : '1rem 1rem 1rem 0.25rem',
          background: isUser
            ? 'linear-gradient(135deg,#4f46e5,#6366f1)'
            : 'rgba(30,41,59,0.9)',
          border: isUser ? 'none' : '1px solid rgba(255,255,255,0.07)',
          color: '#f1f5f9',
          fontSize: '0.875rem',
          lineHeight: 1.65,
          wordBreak: 'break-word',
        }}
      >
        {renderContent(message.content)}
      </div>

      {/* User avatar */}
      {isUser && (
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: 'rgba(99,102,241,0.2)',
            border: '1px solid rgba(99,102,241,0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            marginLeft: '0.5rem',
            marginTop: '0.15rem',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sending spinner row
// ---------------------------------------------------------------------------

function SendingIndicator() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          fontSize: '0.7rem',
          color: '#fff',
          fontWeight: 700,
        }}
      >
        AI
      </div>
      <div
        style={{
          padding: '0.65rem 0.9rem',
          borderRadius: '1rem 1rem 1rem 0.25rem',
          background: 'rgba(30,41,59,0.9)',
          border: '1px solid rgba(255,255,255,0.07)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          color: '#94a3b8',
          fontSize: '0.875rem',
        }}
      >
        <div className="spinner" style={{ width: 14, height: 14 }} />
        Sending…
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Starter prompts grid
// ---------------------------------------------------------------------------

function StarterPrompts({ onSelect }: { onSelect: (prompt: string) => void }) {
  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '2rem',
        padding: '2rem',
      }}
    >
      {/* Hero */}
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: '50%',
            background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1rem',
          }}
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.5">
            <path d="M12 2a10 10 0 1 0 10 10" />
            <path d="M12 6v6l4 2" />
            <path d="M22 2l-5 5M17 2h5v5" />
          </svg>
        </div>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 600, color: '#e2e8f0', margin: '0 0 0.5rem' }}>
          Code Assistant
        </h2>
        <p style={{ color: '#64748b', fontSize: '0.875rem', margin: 0 }}>
          Ask anything about data, code, or analysis
        </p>
      </div>

      {/* Suggestion cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '0.75rem',
          width: '100%',
          maxWidth: 560,
        }}
      >
        {STARTER_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onSelect(prompt)}
            style={{
              background: 'rgba(30,41,59,0.8)',
              border: '1px solid rgba(255,255,255,0.07)',
              borderRadius: '0.5rem',
              padding: '0.75rem 1rem',
              cursor: 'pointer',
              textAlign: 'left',
              color: '#cbd5e1',
              fontSize: '0.8rem',
              lineHeight: 1.5,
              transition: 'border-color 0.15s, background 0.15s',
            }}
            onMouseEnter={e => {
              const el = e.currentTarget
              el.style.borderColor = 'rgba(99,102,241,0.4)'
              el.style.background = 'rgba(99,102,241,0.06)'
            }}
            onMouseLeave={e => {
              const el = e.currentTarget
              el.style.borderColor = 'rgba(255,255,255,0.07)'
              el.style.background = 'rgba(30,41,59,0.8)'
            }}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function CodeAssistant() {
  const queryClient = useQueryClient()

  // Layout
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'active' | 'archived'>('active')

  // Conversation state
  const [currentConvId, setCurrentConvId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])

  // Input
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  // Preferences
  const [language, setLanguage] = useState('Python')
  const [model, setModel] = useState('gemini-2.5-flash')

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // -------------------------------------------------------------------------
  // Auto-scroll to bottom on new message
  // -------------------------------------------------------------------------

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // -------------------------------------------------------------------------
  // Auto-resize textarea
  // -------------------------------------------------------------------------

  function adjustTextarea() {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    const lineHeight = 22
    const minH = lineHeight * 2
    const maxH = lineHeight * 6
    ta.style.height = Math.min(Math.max(ta.scrollHeight, minH), maxH) + 'px'
  }

  // -------------------------------------------------------------------------
  // Load user preferences
  // -------------------------------------------------------------------------

  useQuery({
    queryKey: ['userPreferences'],
    queryFn: async () => {
      const result = await apiClient.get<PreferencesResponse>('/users/preferences')
      if (result.ok && result.data) {
        if (result.data.currentLanguage) setLanguage(result.data.currentLanguage)
        if (result.data.geminiModel) setModel(result.data.geminiModel)
      }
      return result.data
    },
  })

  // -------------------------------------------------------------------------
  // Active conversations list
  // -------------------------------------------------------------------------

  const { data: activeConvsData, refetch: refetchActive } = useQuery({
    queryKey: ['conversations', 'active'],
    queryFn: async () => {
      const result = await apiClient.get<ConversationsResponse>('/users/conversations?archived=false')
      if (!result.ok) throw new Error(result.error ?? 'Failed to load conversations')
      return result.data
    },
  })

  // -------------------------------------------------------------------------
  // Archived conversations list
  // -------------------------------------------------------------------------

  const { data: archivedConvsData, refetch: refetchArchived } = useQuery({
    queryKey: ['conversations', 'archived'],
    queryFn: async () => {
      const result = await apiClient.get<ConversationsResponse>('/users/conversations?archived=true')
      if (!result.ok) throw new Error(result.error ?? 'Failed to load archived conversations')
      return result.data
    },
    enabled: activeTab === 'archived',
  })

  const activeConvs = activeConvsData?.conversations ?? []
  const archivedConvs = archivedConvsData?.conversations ?? []
  const displayedConvs = activeTab === 'active' ? activeConvs : archivedConvs

  // -------------------------------------------------------------------------
  // New conversation
  // -------------------------------------------------------------------------

  async function handleNewConversation() {
    const id = crypto.randomUUID()
    const result = await apiClient.post<NewConversationResponse>('/users/conversations', {
      conversation_id: id,
      title: 'New Conversation',
    })
    if (result.ok) {
      setCurrentConvId(id)
      setMessages([])
      await refetchActive()
    }
  }

  // -------------------------------------------------------------------------
  // Load conversation
  // -------------------------------------------------------------------------

  async function handleLoadConversation(id: string) {
    const result = await apiClient.get<Conversation>(`/users/conversations/${id}`)
    if (result.ok && result.data) {
      setCurrentConvId(id)
      setMessages(result.data.messages ?? [])
      // On mobile close the sidebar after selecting
      if (window.innerWidth < 768) setSidebarOpen(false)
    }
  }

  // -------------------------------------------------------------------------
  // Archive conversation
  // -------------------------------------------------------------------------

  async function handleArchive(id: string) {
    await apiClient.put(`/users/conversations/${id}`, { archived: true })
    if (id === currentConvId) {
      setCurrentConvId(null)
      setMessages([])
    }
    await Promise.all([refetchActive(), refetchArchived()])
    queryClient.invalidateQueries({ queryKey: ['conversations'] })
  }

  // -------------------------------------------------------------------------
  // Delete conversation
  // -------------------------------------------------------------------------

  async function handleDelete(id: string) {
    await apiClient.del(`/users/conversations/${id}`)
    if (id === currentConvId) {
      setCurrentConvId(null)
      setMessages([])
    }
    await Promise.all([refetchActive(), refetchArchived()])
    queryClient.invalidateQueries({ queryKey: ['conversations'] })
  }

  // -------------------------------------------------------------------------
  // Send message
  // -------------------------------------------------------------------------

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || sending) return

    // Ensure there is an active conversation
    let convId = currentConvId
    if (!convId) {
      const id = crypto.randomUUID()
      const createResult = await apiClient.post<NewConversationResponse>('/users/conversations', {
        conversation_id: id,
        title: trimmed.slice(0, 60),
      })
      if (!createResult.ok) return
      convId = id
      setCurrentConvId(id)
      await refetchActive()
    }

    // Optimistically append user message
    const userMessage: Message = { role: 'user', content: trimmed }
    const updatedMessages: Message[] = [...messages, userMessage]
    setMessages(updatedMessages)
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    setSending(true)

    // POST to AI chat
    const chatResult = await apiClient.post<ChatResponse>('/api/ai/chat', {
      message: trimmed,
      conversation_id: convId,
      model,
    })

    const assistantContent =
      chatResult.ok && chatResult.data?.response
        ? chatResult.data.response
        : chatResult.error ?? 'An error occurred. Please try again.'

    const assistantMessage: Message = { role: 'assistant', content: assistantContent }
    const finalMessages: Message[] = [...updatedMessages, assistantMessage]
    setMessages(finalMessages)

    // Persist messages
    await apiClient.put(`/users/conversations/${convId}`, { messages: finalMessages })

    setSending(false)
  }, [currentConvId, messages, model, sending, refetchActive])

  // -------------------------------------------------------------------------
  // Input handlers
  // -------------------------------------------------------------------------

  function handleInputChange(e: ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    adjustTextarea()
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void sendMessage(input)
    }
  }

  // -------------------------------------------------------------------------
  // Save preference on change
  // -------------------------------------------------------------------------

  async function handleLanguageChange(lang: string) {
    setLanguage(lang)
    await apiClient.put('/users/preferences', { currentLanguage: lang })
  }

  async function handleModelChange(m: string) {
    setModel(m)
    await apiClient.put('/users/preferences', { geminiModel: m })
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div
      style={{
        display: 'flex',
        height: 'calc(100vh - 60px)',  // subtract nav height
        position: 'relative',
        overflow: 'hidden',
        background: 'var(--bg-primary, #0a0f1e)',
      }}
    >
      {/* ------------------------------------------------------------------ */}
      {/* Sidebar overlay (mobile) */}
      {/* ------------------------------------------------------------------ */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            zIndex: 19,
            display: 'none',
          }}
          className="sidebar-overlay-mobile"
        />
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Sidebar */}
      {/* ------------------------------------------------------------------ */}
      <aside
        style={{
          width: sidebarOpen ? 260 : 0,
          minWidth: sidebarOpen ? 260 : 0,
          overflow: 'hidden',
          transition: 'width 0.2s ease, min-width 0.2s ease',
          display: 'flex',
          flexDirection: 'column',
          background: 'rgba(15,23,42,0.95)',
          borderRight: '1px solid rgba(255,255,255,0.06)',
          flexShrink: 0,
          zIndex: 20,
        }}
      >
        {/* Sidebar header */}
        <div
          style={{
            padding: '0.75rem',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            flexShrink: 0,
          }}
        >
          <button
            className="btn btn-primary btn-sm"
            onClick={handleNewConversation}
            style={{ width: '100%', justifyContent: 'center' }}
          >
            + New Chat
          </button>
        </div>

        {/* Tabs */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            flexShrink: 0,
          }}
        >
          {(['active', 'archived'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                flex: 1,
                padding: '0.5rem',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === tab
                  ? '2px solid #6366f1'
                  : '2px solid transparent',
                color: activeTab === tab ? '#a5b4fc' : '#64748b',
                fontSize: '0.75rem',
                fontWeight: 500,
                cursor: 'pointer',
                textTransform: 'capitalize',
                transition: 'color 0.15s',
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Conversation list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
          {displayedConvs.length === 0 && (
            <p
              style={{
                color: '#475569',
                fontSize: '0.75rem',
                textAlign: 'center',
                marginTop: '1.5rem',
              }}
            >
              {activeTab === 'active' ? 'No conversations yet' : 'No archived conversations'}
            </p>
          )}
          {displayedConvs.map((conv) => (
            <ConvItem
              key={conv.id}
              conv={conv}
              active={conv.id === currentConvId}
              onLoad={handleLoadConversation}
              onArchive={handleArchive}
              onDelete={handleDelete}
              isArchived={activeTab === 'archived'}
            />
          ))}
        </div>
      </aside>

      {/* ------------------------------------------------------------------ */}
      {/* Main chat area */}
      {/* ------------------------------------------------------------------ */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* Top bar with sidebar toggle */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.6rem 1rem',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            flexShrink: 0,
            background: 'rgba(10,15,30,0.8)',
          }}
        >
          {/* Hamburger */}
          <button
            onClick={() => setSidebarOpen(o => !o)}
            title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: '#94a3b8',
              padding: '0.35rem',
              borderRadius: '0.375rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'color 0.15s, background 0.15s',
            }}
            onMouseEnter={e => {
              const el = e.currentTarget
              el.style.color = '#e2e8f0'
              el.style.background = 'rgba(255,255,255,0.05)'
            }}
            onMouseLeave={e => {
              const el = e.currentTarget
              el.style.color = '#94a3b8'
              el.style.background = 'transparent'
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>

          {/* Title */}
          <span style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 500 }}>
            Code Assistant
          </span>
        </div>

        {/* Messages scroll area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {messages.length === 0 && !sending ? (
            <StarterPrompts
              onSelect={(prompt) => {
                setInput(prompt)
                textareaRef.current?.focus()
              }}
            />
          ) : (
            <div style={{ padding: '1.25rem 1.25rem 0', maxWidth: 800, width: '100%', margin: '0 auto' }}>
              {messages.map((msg, idx) => (
                <MessageBubble key={idx} message={msg} />
              ))}
              {sending && <SendingIndicator />}
              <div ref={messagesEndRef} style={{ height: 4 }} />
            </div>
          )}
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Input area (sticky bottom) */}
        {/* ---------------------------------------------------------------- */}
        <div
          style={{
            flexShrink: 0,
            borderTop: '1px solid rgba(255,255,255,0.06)',
            background: 'rgba(10,15,30,0.95)',
            padding: '0.75rem 1rem',
          }}
        >
          <div
            style={{
              maxWidth: 800,
              margin: '0 auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
            }}
          >
            {/* Textarea row */}
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-end',
                gap: '0.5rem',
                background: 'rgba(30,41,59,0.8)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '0.5rem',
                padding: '0.5rem 0.5rem 0.5rem 0.75rem',
                transition: 'border-color 0.15s',
              }}
              onFocusCapture={e => {
                const el = e.currentTarget as HTMLDivElement
                el.style.borderColor = 'rgba(99,102,241,0.5)'
              }}
              onBlurCapture={e => {
                const el = e.currentTarget as HTMLDivElement
                el.style.borderColor = 'rgba(255,255,255,0.08)'
              }}
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                disabled={sending}
                placeholder="Ask anything… (Shift+Enter for newline)"
                rows={2}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  resize: 'none',
                  color: '#f1f5f9',
                  fontSize: '0.875rem',
                  lineHeight: '1.5',
                  fontFamily: 'inherit',
                  minHeight: 44,
                  maxHeight: 132,
                  overflowY: 'auto',
                }}
              />

              {/* Send button */}
              <button
                onClick={() => void sendMessage(input)}
                disabled={!input.trim() || sending}
                title="Send (Enter)"
                style={{
                  background: input.trim() && !sending
                    ? 'linear-gradient(135deg,#4f46e5,#6366f1)'
                    : 'rgba(255,255,255,0.06)',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: input.trim() && !sending ? 'pointer' : 'not-allowed',
                  color: input.trim() && !sending ? '#fff' : '#475569',
                  width: 36,
                  height: 36,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  transition: 'background 0.15s',
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>

            {/* Selectors row */}
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
              {/* Language selector */}
              <div className="form-group" style={{ margin: 0, flex: '0 0 auto' }}>
                <select
                  value={language}
                  onChange={e => void handleLanguageChange(e.target.value)}
                  style={selectStyle}
                >
                  {LANGUAGES.map(lang => (
                    <option key={lang} value={lang}>{lang}</option>
                  ))}
                </select>
              </div>

              {/* Model selector */}
              <div className="form-group" style={{ margin: 0, flex: '1 1 auto', minWidth: 160 }}>
                <select
                  value={model}
                  onChange={e => void handleModelChange(e.target.value)}
                  style={selectStyle}
                >
                  {MODELS.map(m => (
                    <option key={m.value} value={m.value}>
                      {m.label} — {m.description}
                    </option>
                  ))}
                </select>
              </div>

              <span
                style={{
                  fontSize: '0.7rem',
                  color: '#475569',
                  marginLeft: 'auto',
                  whiteSpace: 'nowrap',
                }}
              >
                Enter to send · Shift+Enter for newline
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const selectStyle: React.CSSProperties = {
  background: 'rgba(30,41,59,0.8)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '0.375rem',
  color: '#94a3b8',
  fontSize: '0.75rem',
  padding: '0.3rem 0.5rem',
  cursor: 'pointer',
  outline: 'none',
  width: '100%',
}
