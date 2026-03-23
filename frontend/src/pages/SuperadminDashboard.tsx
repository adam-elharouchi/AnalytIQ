/**
 * SuperadminDashboard — platform-wide admin UI.
 * Route: /admin (when user.role === 'superadmin')
 * Tabs: Overview | Analytics | Tenants | Users | Classes | Announcements | Settings | Approvals
 */

import { useState, type FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

// ---------------------------------------------------------------------------
// Local types
// ---------------------------------------------------------------------------

interface AnalyticsData {
  users: {
    total: number
    new_7d: number
    active_30d: number
    by_role: Record<string, number>
  }
  content: {
    classes: number
    chapters: number
    exercises: number
    completions: number
  }
}

interface HealthData {
  status: string
  postgres: string
  redis: string
  storage: string
}

interface AuditLog {
  id: string
  action: string
  user_name: string
  resource_type: string
  timestamp: string
  details: string
}

interface Tenant {
  tenant_id: string
  name: string
  is_active: boolean
  lti_issuer: string
  email_domain: string
  total_users: number
  total_classes: number
}

interface AdminUser {
  user_id: string
  name: string
  email: string
  role: string
  tenant_name: string
  account_status: string
  created_at: string
}

interface AdminClass {
  class_id: string
  name: string
  professor_email: string
  total_students: number
  status: string
  tenant_name: string
}

interface Announcement {
  id: string
  title: string
  type: 'info' | 'warning' | 'danger' | 'success'
  message: string
  is_active: boolean
  expires_at: string | null
  target_roles: string[]
}

interface PlatformConfig {
  maintenance_mode: string
  maintenance_message: string
}

interface BlockedIP {
  id: string
  ip_address: string
  reason: string
  blocked_by_name: string
  created_at: string
}

interface PendingApproval {
  user_id?: string
  class_id?: string
  name: string
  email?: string
  professor_email?: string
  type: string
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

type TabId =
  | 'overview'
  | 'analytics'
  | 'tenants'
  | 'users'
  | 'classes'
  | 'announcements'
  | 'settings'
  | 'approvals'

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'tenants', label: 'Tenants' },
  { id: 'users', label: 'Users' },
  { id: 'classes', label: 'Classes' },
  { id: 'announcements', label: 'Announcements' },
  { id: 'settings', label: 'Settings' },
  { id: 'approvals', label: 'Approvals' },
]

function HealthDot({ status }: { status: string }) {
  const ok = status === 'ok' || status === 'healthy' || status === 'connected'
  return (
    <span
      style={{
        display: 'inline-block',
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: ok ? 'var(--color-success)' : 'var(--color-danger)',
        marginRight: 6,
      }}
    />
  )
}

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    superadmin: 'var(--color-danger)',
    tenant_admin: 'var(--color-warning)',
    professor: 'var(--color-info)',
    student: 'var(--color-success)',
  }
  return (
    <span
      className="badge"
      style={{ background: colors[role] ?? 'var(--text-muted)', color: '#fff', fontSize: 11 }}
    >
      {role}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const active = status === 'active' || status === 'enabled'
  return (
    <span
      className="badge"
      style={{
        background: active ? 'var(--color-success)' : 'var(--text-muted)',
        color: '#fff',
        fontSize: 11,
      }}
    >
      {status}
    </span>
  )
}

function Spinner() {
  return (
    <div className="loading-state">
      <div className="spinner" />
    </div>
  )
}

function Pagination({
  page,
  pages,
  onPage,
}: {
  page: number
  pages: number
  onPage: (n: number) => void
}) {
  if (pages <= 1) return null
  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 12, alignItems: 'center' }}>
      <button
        className="btn btn-sm btn-ghost"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
      >
        ‹ Prev
      </button>
      <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
        {page} / {pages}
      </span>
      <button
        className="btn btn-sm btn-ghost"
        disabled={page >= pages}
        onClick={() => onPage(page + 1)}
      >
        Next ›
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab 1: Overview
// ---------------------------------------------------------------------------

function OverviewTab() {
  const analyticsQ = useQuery({
    queryKey: ['sa-analytics'],
    queryFn: () => apiClient.get<AnalyticsData>('/superadmin/analytics'),
  })
  const healthQ = useQuery({
    queryKey: ['sa-health'],
    queryFn: () => apiClient.get<HealthData>('/health'),
  })

  if (analyticsQ.isLoading || healthQ.isLoading) return <Spinner />

  const a = analyticsQ.data?.data
  const h = healthQ.data?.data

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        {[
          { label: 'Total Users', value: a?.users.total ?? '—' },
          { label: 'Active (30d)', value: a?.users.active_30d ?? '—' },
          { label: 'Total Classes', value: a?.content.classes ?? '—' },
          { label: 'Total Exercises', value: a?.content.exercises ?? '—' },
        ].map(card => (
          <div
            key={card.label}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius)',
              padding: '20px 24px',
            }}
          >
            <div style={{ fontSize: 28, fontWeight: 700 }}>{card.value}</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
              {card.label}
            </div>
          </div>
        ))}
      </div>

      {h && (
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius)',
            padding: '20px 24px',
          }}
        >
          <h3 style={{ marginBottom: 12, fontSize: 15 }}>System Health</h3>
          <div style={{ display: 'flex', gap: 32 }}>
            {(['postgres', 'redis', 'storage'] as const).map(svc => (
              <div key={svc} style={{ display: 'flex', alignItems: 'center' }}>
                <HealthDot status={h[svc]} />
                <span style={{ textTransform: 'capitalize', fontSize: 14 }}>{svc}</span>
                <span style={{ marginLeft: 6, color: 'var(--text-muted)', fontSize: 12 }}>
                  ({h[svc]})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab 2: Analytics
// ---------------------------------------------------------------------------

function AnalyticsTab() {
  const [page, setPage] = useState(1)

  const analyticsQ = useQuery({
    queryKey: ['sa-analytics'],
    queryFn: () => apiClient.get<AnalyticsData>('/superadmin/analytics'),
  })

  const auditQ = useQuery({
    queryKey: ['sa-audit', page],
    queryFn: () =>
      apiClient.get<{ logs: AuditLog[]; pages: number }>(
        `/superadmin/audit?page=${page}&limit=50`,
      ),
  })

  if (analyticsQ.isLoading) return <Spinner />

  const a = analyticsQ.data?.data
  const auditData = auditQ.data?.data

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {a && (
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius)',
            padding: '20px 24px',
          }}
        >
          <h3 style={{ marginBottom: 12, fontSize: 15 }}>Role Distribution</h3>
          <div style={{ display: 'flex', gap: 32 }}>
            {Object.entries(a.users.by_role).map(([role, count]) => (
              <div key={role}>
                <RoleBadge role={role} />
                <span style={{ marginLeft: 8, fontSize: 16, fontWeight: 600 }}>{count}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16, display: 'flex', gap: 32, color: 'var(--text-muted)', fontSize: 13 }}>
            <span>New users (7d): <strong style={{ color: 'var(--text-color)' }}>{a.users.new_7d}</strong></span>
            <span>Completions: <strong style={{ color: 'var(--text-color)' }}>{a.content.completions}</strong></span>
            <span>Chapters: <strong style={{ color: 'var(--text-color)' }}>{a.content.chapters}</strong></span>
          </div>
        </div>
      )}

      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius)',
          padding: '20px 24px',
        }}
      >
        <h3 style={{ marginBottom: 12, fontSize: 15 }}>Audit Log</h3>
        {auditQ.isLoading ? (
          <Spinner />
        ) : (
          <>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                  <th style={{ textAlign: 'left', padding: '8px 12px' }}>Action</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px' }}>User</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px' }}>Resource</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px' }}>Timestamp</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {auditData?.logs.map(log => (
                  <tr
                    key={log.id}
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  >
                    <td style={{ padding: '8px 12px' }}>{log.action}</td>
                    <td style={{ padding: '8px 12px' }}>{log.user_name}</td>
                    <td style={{ padding: '8px 12px' }}>{log.resource_type}</td>
                    <td style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td style={{ padding: '8px 12px', color: 'var(--text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {log.details}
                    </td>
                  </tr>
                ))}
                {(!auditData?.logs || auditData.logs.length === 0) && (
                  <tr>
                    <td colSpan={5} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                      No audit logs
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <Pagination
              page={page}
              pages={auditData?.pages ?? 1}
              onPage={setPage}
            />
          </>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab 3: Tenants
// ---------------------------------------------------------------------------

interface TenantEditModalProps {
  tenant: Tenant
  onClose: () => void
}

function TenantEditModal({ tenant, onClose }: TenantEditModalProps) {
  const [name, setName] = useState(tenant.name)
  const [ltiIssuer, setLtiIssuer] = useState(tenant.lti_issuer ?? '')
  const [emailDomain, setEmailDomain] = useState(tenant.email_domain ?? '')
  const [error, setError] = useState<string | null>(null)
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.put(`/superadmin/tenants/${tenant.tenant_id}`, {
        name,
        lti_issuer: ltiIssuer,
        email_domain: emailDomain,
      }),
    onSuccess: result => {
      if (!result.ok) { setError(result.error ?? 'Failed'); return }
      qc.invalidateQueries({ queryKey: ['sa-tenants'] })
      onClose()
    },
  })

  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal>
        <div className="modal-header">
          <h2 className="modal-title">Edit Tenant</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form
          className="modal-body"
          onSubmit={e => { e.preventDefault(); mutation.mutate() }}
        >
          <div className="form-group">
            <label>Name</label>
            <input value={name} onChange={e => setName(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>LTI Issuer</label>
            <input value={ltiIssuer} onChange={e => setLtiIssuer(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Email Domain</label>
            <input
              value={emailDomain}
              onChange={e => setEmailDomain(e.target.value)}
              placeholder="e.g. example.edu"
            />
          </div>
          {error && <p className="alert alert-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

function TenantsTab() {
  const [editTenant, setEditTenant] = useState<Tenant | null>(null)
  const qc = useQueryClient()

  const tenantsQ = useQuery({
    queryKey: ['sa-tenants'],
    queryFn: () => apiClient.get<{ tenants: Tenant[] }>('/superadmin/tenants'),
  })

  const toggleMutation = useMutation({
    mutationFn: (t: Tenant) =>
      apiClient.put(`/superadmin/tenants/${t.tenant_id}`, { is_active: !t.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-tenants'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.del(`/superadmin/tenants/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-tenants'] }),
  })

  if (tenantsQ.isLoading) return <Spinner />

  const tenants = tenantsQ.data?.data?.tenants ?? []

  return (
    <>
      {editTenant && (
        <TenantEditModal tenant={editTenant} onClose={() => setEditTenant(null)} />
      )}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius)',
          overflow: 'hidden',
        }}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
              <th style={{ textAlign: 'left', padding: '10px 16px' }}>Name</th>
              <th style={{ textAlign: 'left', padding: '10px 16px' }}>Users</th>
              <th style={{ textAlign: 'left', padding: '10px 16px' }}>Classes</th>
              <th style={{ textAlign: 'left', padding: '10px 16px' }}>Status</th>
              <th style={{ textAlign: 'left', padding: '10px 16px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map(t => (
              <tr key={t.tenant_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '10px 16px' }}>{t.name}</td>
                <td style={{ padding: '10px 16px' }}>{t.total_users}</td>
                <td style={{ padding: '10px 16px' }}>{t.total_classes}</td>
                <td style={{ padding: '10px 16px' }}>
                  <StatusBadge status={t.is_active ? 'active' : 'inactive'} />
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={() => setEditTenant(t)}
                    >
                      Edit
                    </button>
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={() => toggleMutation.mutate(t)}
                      disabled={toggleMutation.isPending}
                    >
                      {t.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => {
                        if (window.confirm(`Delete tenant "${t.name}"? This cannot be undone.`)) {
                          deleteMutation.mutate(t.tenant_id)
                        }
                      }}
                      disabled={deleteMutation.isPending}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {tenants.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-state" style={{ padding: 32, textAlign: 'center' }}>
                  No tenants found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Tab 4: Users
// ---------------------------------------------------------------------------

interface UserRoleModalProps {
  user: AdminUser
  onClose: () => void
}

function UserRoleModal({ user, onClose }: UserRoleModalProps) {
  const [role, setRole] = useState(user.role)
  const [tenantId, setTenantId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.put(`/superadmin/users/${user.user_id}/role`, {
        role,
        ...(role === 'tenant_admin' && tenantId ? { tenant_id: tenantId } : {}),
      }),
    onSuccess: result => {
      if (!result.ok) { setError(result.error ?? 'Failed'); return }
      qc.invalidateQueries({ queryKey: ['sa-users'] })
      onClose()
    },
  })

  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal>
        <div className="modal-header">
          <h2 className="modal-title">Change Role — {user.name}</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form
          className="modal-body"
          onSubmit={e => { e.preventDefault(); mutation.mutate() }}
        >
          <div className="form-group">
            <label>Role</label>
            <select value={role} onChange={e => setRole(e.target.value)}>
              <option value="student">student</option>
              <option value="professor">professor</option>
              <option value="tenant_admin">tenant_admin</option>
              <option value="superadmin">superadmin</option>
            </select>
          </div>
          {role === 'tenant_admin' && (
            <div className="form-group">
              <label>Tenant ID</label>
              <input
                value={tenantId}
                onChange={e => setTenantId(e.target.value)}
                placeholder="Required for tenant_admin"
              />
            </div>
          )}
          {error && <p className="alert alert-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

function UsersTab() {
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [roleModalUser, setRoleModalUser] = useState<AdminUser | null>(null)
  const qc = useQueryClient()

  const usersQ = useQuery({
    queryKey: ['sa-users', page, q, roleFilter, statusFilter],
    queryFn: () =>
      apiClient.get<{ users: AdminUser[]; current_page: number; pages: number }>(
        `/superadmin/users?page=${page}&limit=50&q=${encodeURIComponent(q)}&role=${roleFilter}&status=${statusFilter}`,
      ),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient.put(`/superadmin/users/${id}/status`, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-users'] }),
  })

  const resetMutation = useMutation({
    mutationFn: (id: string) => apiClient.post(`/superadmin/users/${id}/force-reset`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-users'] }),
  })

  const impersonateMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient.post<{ token: string }>(`/superadmin/users/${id}/impersonate`),
    onSuccess: result => {
      if (!result.ok || !result.data?.token) return
      const original = localStorage.getItem('authToken')
      if (original) localStorage.setItem('original_token', original)
      localStorage.setItem('impersonation_token', result.data.token)
      window.location.reload()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.del(`/superadmin/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-users'] }),
  })

  const data = usersQ.data?.data

  return (
    <>
      {roleModalUser && (
        <UserRoleModal user={roleModalUser} onClose={() => setRoleModalUser(null)} />
      )}

      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <input
          style={{ flex: 1, background: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-color)' }}
          placeholder="Search by name or email…"
          value={q}
          onChange={e => { setQ(e.target.value); setPage(1) }}
        />
        <select
          style={{ background: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-color)' }}
          value={roleFilter}
          onChange={e => { setRoleFilter(e.target.value); setPage(1) }}
        >
          <option value="">All roles</option>
          <option value="student">student</option>
          <option value="professor">professor</option>
          <option value="tenant_admin">tenant_admin</option>
          <option value="superadmin">superadmin</option>
        </select>
        <select
          style={{ background: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-color)' }}
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
        >
          <option value="">All statuses</option>
          <option value="active">active</option>
          <option value="disabled">disabled</option>
          <option value="pending">pending</option>
        </select>
      </div>

      {usersQ.isLoading ? (
        <Spinner />
      ) : (
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius)',
            overflow: 'hidden',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Name</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Email</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Role</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Tenant</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Status</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.users.map(u => (
                <tr key={u.user_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '10px 16px' }}>{u.name}</td>
                  <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>{u.email}</td>
                  <td style={{ padding: '10px 16px' }}>
                    <RoleBadge role={u.role} />
                  </td>
                  <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>{u.tenant_name ?? '—'}</td>
                  <td style={{ padding: '10px 16px' }}>
                    <StatusBadge status={u.account_status} />
                  </td>
                  <td style={{ padding: '10px 16px' }}>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={() => setRoleModalUser(u)}
                      >
                        Role
                      </button>
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={() => {
                          const newStatus = u.account_status === 'active' ? 'disabled' : 'active'
                          statusMutation.mutate({ id: u.user_id, status: newStatus })
                        }}
                        disabled={statusMutation.isPending}
                      >
                        {u.account_status === 'active' ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={() => {
                          if (window.confirm(`Force password reset for ${u.name}?`)) {
                            resetMutation.mutate(u.user_id)
                          }
                        }}
                        disabled={resetMutation.isPending}
                      >
                        Reset
                      </button>
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={() => {
                          if (window.confirm(`Impersonate ${u.name}? Your current token will be saved as original_token.`)) {
                            impersonateMutation.mutate(u.user_id)
                          }
                        }}
                        disabled={impersonateMutation.isPending}
                      >
                        Impersonate
                      </button>
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => {
                          if (window.confirm(`Permanently delete user ${u.name}?`)) {
                            deleteMutation.mutate(u.user_id)
                          }
                        }}
                        disabled={deleteMutation.isPending}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {(!data?.users || data.users.length === 0) && (
                <tr>
                  <td colSpan={6} className="empty-state" style={{ padding: 32, textAlign: 'center' }}>
                    No users found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <div style={{ padding: '8px 16px' }}>
            <Pagination page={page} pages={data?.pages ?? 1} onPage={setPage} />
          </div>
        </div>
      )}
    </>
  )
}

// ---------------------------------------------------------------------------
// Tab 5: Classes
// ---------------------------------------------------------------------------

function ClassesTab() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [transferEmail, setTransferEmail] = useState<Record<string, string>>({})
  const qc = useQueryClient()

  const classesQ = useQuery({
    queryKey: ['sa-classes', page, search],
    queryFn: () =>
      apiClient.get<{ classes: AdminClass[]; pages: number }>(
        `/superadmin/classes?page=${page}&limit=50&search=${encodeURIComponent(search)}`,
      ),
  })

  const transferMutation = useMutation({
    mutationFn: ({ id, email }: { id: string; email: string }) =>
      apiClient.put(`/superadmin/classes/${id}/transfer`, { professor_email: email }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-classes'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.del(`/superadmin/classes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-classes'] }),
  })

  const data = classesQ.data?.data

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <input
          style={{ width: '100%', background: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-color)' }}
          placeholder="Search classes…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
        />
      </div>

      {classesQ.isLoading ? (
        <Spinner />
      ) : (
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius)',
            overflow: 'hidden',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Name</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Professor</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Students</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Tenant</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.classes.map(c => (
                <tr key={c.class_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '10px 16px' }}>{c.name}</td>
                  <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>{c.professor_email}</td>
                  <td style={{ padding: '10px 16px' }}>{c.total_students}</td>
                  <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>{c.tenant_name}</td>
                  <td style={{ padding: '10px 16px' }}>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <input
                        style={{ width: 180, background: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '4px 8px', color: 'var(--text-color)', fontSize: 12 }}
                        placeholder="New professor email"
                        value={transferEmail[c.class_id] ?? ''}
                        onChange={e =>
                          setTransferEmail(prev => ({ ...prev, [c.class_id]: e.target.value }))
                        }
                      />
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={() => {
                          const email = transferEmail[c.class_id]?.trim()
                          if (!email) return
                          if (window.confirm(`Transfer class "${c.name}" to ${email}?`)) {
                            transferMutation.mutate({ id: c.class_id, email })
                          }
                        }}
                        disabled={transferMutation.isPending}
                      >
                        Transfer
                      </button>
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => {
                          if (window.confirm(`Delete class "${c.name}"?`)) {
                            deleteMutation.mutate(c.class_id)
                          }
                        }}
                        disabled={deleteMutation.isPending}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {(!data?.classes || data.classes.length === 0) && (
                <tr>
                  <td colSpan={5} className="empty-state" style={{ padding: 32, textAlign: 'center' }}>
                    No classes found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <div style={{ padding: '8px 16px' }}>
            <Pagination page={page} pages={data?.pages ?? 1} onPage={setPage} />
          </div>
        </div>
      )}
    </>
  )
}

// ---------------------------------------------------------------------------
// Tab 6: Announcements
// ---------------------------------------------------------------------------

const ANNOUNCEMENT_ROLES = ['student', 'professor', 'superadmin']

function AnnouncementsTab() {
  const [title, setTitle] = useState('')
  const [type, setType] = useState<Announcement['type']>('info')
  const [message, setMessage] = useState('')
  const [targetRoles, setTargetRoles] = useState<string[]>(['student'])
  const [expiresAt, setExpiresAt] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const qc = useQueryClient()

  const announcementsQ = useQuery({
    queryKey: ['sa-announcements'],
    queryFn: () =>
      apiClient.get<{ announcements: Announcement[] }>('/superadmin/announcements'),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      apiClient.post('/superadmin/announcements', {
        title,
        type,
        message,
        target_roles: targetRoles,
        ...(expiresAt ? { expires_at: expiresAt } : {}),
      }),
    onSuccess: result => {
      if (!result.ok) { setFormError(result.error ?? 'Failed'); return }
      qc.invalidateQueries({ queryKey: ['sa-announcements'] })
      setTitle('')
      setType('info')
      setMessage('')
      setTargetRoles(['student'])
      setExpiresAt('')
      setFormError(null)
    },
  })

  const toggleMutation = useMutation({
    mutationFn: (a: Announcement) =>
      apiClient.put(`/superadmin/announcements/${a.id}`, { is_active: !a.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-announcements'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.del(`/superadmin/announcements/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-announcements'] }),
  })

  function toggleRole(r: string) {
    setTargetRoles(prev =>
      prev.includes(r) ? prev.filter(x => x !== r) : [...prev, r],
    )
  }

  function handleCreate(e: FormEvent) {
    e.preventDefault()
    if (!title.trim() || !message.trim()) {
      setFormError('Title and message are required')
      return
    }
    if (targetRoles.length === 0) {
      setFormError('Select at least one target role')
      return
    }
    setFormError(null)
    createMutation.mutate()
  }

  const typeColors: Record<Announcement['type'], string> = {
    info: 'var(--color-info)',
    warning: 'var(--color-warning)',
    danger: 'var(--color-danger)',
    success: 'var(--color-success)',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Create form */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius)',
          padding: '20px 24px',
        }}
      >
        <h3 style={{ marginBottom: 16, fontSize: 15 }}>Create Announcement</h3>
        <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Title</label>
              <input value={title} onChange={e => setTitle(e.target.value)} required />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Type</label>
              <select
                value={type}
                onChange={e => setType(e.target.value as Announcement['type'])}
              >
                <option value="info">info</option>
                <option value="warning">warning</option>
                <option value="danger">danger</option>
                <option value="success">success</option>
              </select>
            </div>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label>Message</label>
            <textarea
              value={message}
              onChange={e => setMessage(e.target.value)}
              rows={3}
              required
            />
          </div>
          <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
            <div>
              <label style={{ fontSize: 13, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Target Roles</label>
              <div style={{ display: 'flex', gap: 12 }}>
                {ANNOUNCEMENT_ROLES.map(r => (
                  <label key={r} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={targetRoles.includes(r)}
                      onChange={() => toggleRole(r)}
                    />
                    {r}
                  </label>
                ))}
              </div>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Expires At (optional)</label>
              <input
                type="date"
                value={expiresAt}
                onChange={e => setExpiresAt(e.target.value)}
                style={{ background: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '6px 10px', color: 'var(--text-color)' }}
              />
            </div>
          </div>
          {formError && <p className="alert alert-error">{formError}</p>}
          <div>
            <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating…' : 'Create Announcement'}
            </button>
          </div>
        </form>
      </div>

      {/* List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {announcementsQ.isLoading ? (
          <Spinner />
        ) : (
          announcementsQ.data?.data?.announcements.map(a => (
            <div
              key={a.id}
              style={{
                background: 'var(--bg-card)',
                border: `1px solid ${typeColors[a.type]}44`,
                borderLeft: `4px solid ${typeColors[a.type]}`,
                borderRadius: 'var(--radius)',
                padding: '14px 18px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {a.title}
                  <span
                    className="badge"
                    style={{ marginLeft: 8, background: typeColors[a.type], color: '#fff', fontSize: 11 }}
                  >
                    {a.type}
                  </span>
                  {!a.is_active && (
                    <span className="badge" style={{ marginLeft: 6, background: 'var(--text-muted)', color: '#fff', fontSize: 11 }}>
                      inactive
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 6 }}>{a.message}</div>
                <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                  Roles: {a.target_roles.join(', ')}
                  {a.expires_at && ` · Expires: ${new Date(a.expires_at).toLocaleDateString()}`}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0, marginLeft: 12 }}>
                <button
                  className="btn btn-sm btn-ghost"
                  onClick={() => toggleMutation.mutate(a)}
                  disabled={toggleMutation.isPending}
                >
                  {a.is_active ? 'Deactivate' : 'Activate'}
                </button>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => {
                    if (window.confirm(`Delete announcement "${a.title}"?`)) {
                      deleteMutation.mutate(a.id)
                    }
                  }}
                  disabled={deleteMutation.isPending}
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
        {!announcementsQ.isLoading &&
          (announcementsQ.data?.data?.announcements.length ?? 0) === 0 && (
            <div className="empty-state" style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
              No announcements
            </div>
          )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab 7: Settings
// ---------------------------------------------------------------------------

function SettingsTab() {
  const [ipAddress, setIpAddress] = useState('')
  const [ipReason, setIpReason] = useState('')
  const [configError, setConfigError] = useState<string | null>(null)
  const [configSuccess, setConfigSuccess] = useState(false)
  const [ipError, setIpError] = useState<string | null>(null)
  const qc = useQueryClient()

  const configQ = useQuery({
    queryKey: ['sa-platform-config'],
    queryFn: () => apiClient.get<PlatformConfig>('/superadmin/platform-config'),
  })

  const ipBlocklistQ = useQuery({
    queryKey: ['sa-ip-blocklist'],
    queryFn: () => apiClient.get<{ blocked: BlockedIP[] }>('/superadmin/ip-blocklist'),
  })

  // Sync from fetched config
  const configData = configQ.data?.data
  const effectiveMaintenance = configData
    ? configData.maintenance_mode === 'true'
    : false

  const [localMaintenance, setLocalMaintenance] = useState<boolean | null>(null)
  const [localMessage, setLocalMessage] = useState<string | null>(null)

  const displayMaintenance = localMaintenance !== null ? localMaintenance : effectiveMaintenance
  const displayMessage =
    localMessage !== null
      ? localMessage
      : (configData?.maintenance_message ?? '')

  const saveMutation = useMutation({
    mutationFn: () =>
      apiClient.put('/superadmin/platform-config', {
        maintenance_mode: String(displayMaintenance),
        maintenance_message: displayMessage,
      }),
    onSuccess: result => {
      if (!result.ok) {
        setConfigError(result.error ?? 'Failed to save')
        setConfigSuccess(false)
        return
      }
      setConfigError(null)
      setConfigSuccess(true)
      qc.invalidateQueries({ queryKey: ['sa-platform-config'] })
      setTimeout(() => setConfigSuccess(false), 3000)
    },
  })

  const unblockMutation = useMutation({
    mutationFn: (id: string) => apiClient.del(`/superadmin/ip-blocklist/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-ip-blocklist'] }),
  })

  const addIpMutation = useMutation({
    mutationFn: () =>
      apiClient.post('/superadmin/ip-blocklist', { ip_address: ipAddress, reason: ipReason }),
    onSuccess: result => {
      if (!result.ok) { setIpError(result.error ?? 'Failed'); return }
      qc.invalidateQueries({ queryKey: ['sa-ip-blocklist'] })
      setIpAddress('')
      setIpReason('')
      setIpError(null)
    },
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Maintenance mode */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius)',
          padding: '20px 24px',
        }}
      >
        <h3 style={{ marginBottom: 16, fontSize: 15 }}>Maintenance Mode</h3>
        {configQ.isLoading ? (
          <Spinner />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
              <input
                type="checkbox"
                checked={displayMaintenance}
                onChange={e => setLocalMaintenance(e.target.checked)}
              />
              Enable maintenance mode
            </label>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Maintenance Message</label>
              <textarea
                value={displayMessage}
                onChange={e => setLocalMessage(e.target.value)}
                rows={3}
                placeholder="Message shown to users during maintenance…"
              />
            </div>
            {configError && <p className="alert alert-error">{configError}</p>}
            {configSuccess && <p className="alert alert-success">Settings saved.</p>}
            <div>
              <button
                className="btn btn-primary"
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? 'Saving…' : 'Save Settings'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* IP Blocklist */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius)',
          padding: '20px 24px',
        }}
      >
        <h3 style={{ marginBottom: 16, fontSize: 15 }}>IP Blocklist</h3>

        <form
          style={{ display: 'flex', gap: 10, marginBottom: 16 }}
          onSubmit={e => {
            e.preventDefault()
            if (!ipAddress.trim()) return
            addIpMutation.mutate()
          }}
        >
          <input
            style={{ flex: 1, background: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-color)' }}
            placeholder="IP address (e.g. 192.168.1.1)"
            value={ipAddress}
            onChange={e => setIpAddress(e.target.value)}
            required
          />
          <input
            style={{ flex: 2, background: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-color)' }}
            placeholder="Reason"
            value={ipReason}
            onChange={e => setIpReason(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" disabled={addIpMutation.isPending}>
            {addIpMutation.isPending ? 'Adding…' : 'Block IP'}
          </button>
        </form>
        {ipError && <p className="alert alert-error" style={{ marginBottom: 12 }}>{ipError}</p>}

        {ipBlocklistQ.isLoading ? (
          <Spinner />
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                <th style={{ textAlign: 'left', padding: '8px 12px' }}>IP Address</th>
                <th style={{ textAlign: 'left', padding: '8px 12px' }}>Reason</th>
                <th style={{ textAlign: 'left', padding: '8px 12px' }}>Blocked By</th>
                <th style={{ textAlign: 'left', padding: '8px 12px' }}>Date</th>
                <th style={{ textAlign: 'left', padding: '8px 12px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {ipBlocklistQ.data?.data?.blocked.map(ip => (
                <tr key={ip.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)' }}>{ip.ip_address}</td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>{ip.reason}</td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>{ip.blocked_by_name}</td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>
                    {new Date(ip.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={() => {
                        if (window.confirm(`Unblock IP ${ip.ip_address}?`)) {
                          unblockMutation.mutate(ip.id)
                        }
                      }}
                      disabled={unblockMutation.isPending}
                    >
                      Unblock
                    </button>
                  </td>
                </tr>
              ))}
              {(ipBlocklistQ.data?.data?.blocked.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                    No blocked IPs
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab 8: Approvals
// ---------------------------------------------------------------------------

function ApprovalsTab() {
  const qc = useQueryClient()

  const approvalsQ = useQuery({
    queryKey: ['sa-approvals'],
    queryFn: () =>
      apiClient.get<{ pending: PendingApproval[] }>('/superadmin/pending-approvals'),
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => apiClient.put(`/superadmin/users/${id}/approve`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-approvals'] }),
  })

  const denyMutation = useMutation({
    mutationFn: (id: string) => apiClient.put(`/superadmin/users/${id}/deny`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-approvals'] }),
  })

  if (approvalsQ.isLoading) return <Spinner />

  const pending = approvalsQ.data?.data?.pending ?? []
  const userPending = pending.filter(p => p.type === 'user')
  const classPending = pending.filter(p => p.type === 'class')

  function ApprovalRow({ item }: { item: PendingApproval }) {
    const id = item.user_id ?? ''
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div>
          <div style={{ fontWeight: 500 }}>{item.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {item.email ?? item.professor_email ?? ''}
          </div>
        </div>
        {item.type === 'user' && id && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn btn-sm btn-primary"
              onClick={() => approveMutation.mutate(id)}
              disabled={approveMutation.isPending}
            >
              Approve
            </button>
            <button
              className="btn btn-sm btn-danger"
              onClick={() => {
                if (window.confirm(`Deny ${item.name}?`)) {
                  denyMutation.mutate(id)
                }
              }}
              disabled={denyMutation.isPending}
            >
              Deny
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* User approvals */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius)',
          overflow: 'hidden',
        }}
      >
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-color)', fontWeight: 600, fontSize: 14 }}>
          User Approvals ({userPending.length})
        </div>
        {userPending.length === 0 ? (
          <div className="empty-state" style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
            No pending user approvals
          </div>
        ) : (
          userPending.map((item, i) => <ApprovalRow key={item.user_id ?? i} item={item} />)
        )}
      </div>

      {/* Class approvals */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius)',
          overflow: 'hidden',
        }}
      >
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-color)', fontWeight: 600, fontSize: 14 }}>
          Class Approvals ({classPending.length})
        </div>
        {classPending.length === 0 ? (
          <div className="empty-state" style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
            No pending class approvals
          </div>
        ) : (
          classPending.map((item, i) => <ApprovalRow key={item.class_id ?? i} item={item} />)
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Root component
// ---------------------------------------------------------------------------

export default function SuperadminDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  return (
    <div className="page">
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>Platform Admin</h1>

      <div className="auth-tabs" style={{ marginBottom: 24 }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`auth-tab${activeTab === tab.id ? ' auth-tab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && <OverviewTab />}
      {activeTab === 'analytics' && <AnalyticsTab />}
      {activeTab === 'tenants' && <TenantsTab />}
      {activeTab === 'users' && <UsersTab />}
      {activeTab === 'classes' && <ClassesTab />}
      {activeTab === 'announcements' && <AnnouncementsTab />}
      {activeTab === 'settings' && <SettingsTab />}
      {activeTab === 'approvals' && <ApprovalsTab />}
    </div>
  )
}
