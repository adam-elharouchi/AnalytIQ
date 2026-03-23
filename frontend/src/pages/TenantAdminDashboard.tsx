/**
 * TenantAdminDashboard — scoped admin UI for tenant administrators.
 * Route: /admin (when user.role === 'tenant_admin')
 * Tabs: Overview | Users | Classes | SSO Config | Approvals | Audit
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'

// ---------------------------------------------------------------------------
// Local types
// ---------------------------------------------------------------------------

interface TenantOverview {
  total_users: number
  active_30d: number
  total_classes: number
  sso_providers: number
  pending_approvals: number
  tenant_name: string
}

interface TenantUser {
  user_id: string
  name: string
  email: string
  role: string
  account_status: string
  created_at: string
}

interface TenantClass {
  class_id: string
  name: string
  professor_email: string
  total_students: number
  status: string
}

interface SSOProvider {
  provider_id: string
  provider_name: string
  provider_type: 'oidc' | 'google' | 'microsoft'
  client_id: string
  discovery_url?: string
  allowed_domains: string
  default_role: string
  role_mapping_attribute?: string
  is_enabled: boolean
}

interface PendingApproval {
  user_id?: string
  class_id?: string
  name: string
  email?: string
  professor_email?: string
  type: string
}

interface TenantAuditLog {
  id: string
  action: string
  user_name: string
  resource_type: string
  timestamp: string
  details: string
}

// ---------------------------------------------------------------------------
// Tab helpers
// ---------------------------------------------------------------------------

type TabId = 'overview' | 'users' | 'classes' | 'sso' | 'approvals' | 'audit'

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'users', label: 'Users' },
  { id: 'classes', label: 'Classes' },
  { id: 'sso', label: 'SSO Config' },
  { id: 'approvals', label: 'Approvals' },
  { id: 'audit', label: 'Audit' },
]

// ---------------------------------------------------------------------------
// Shared small components
// ---------------------------------------------------------------------------

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
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
  const overviewQ = useQuery({
    queryKey: ['ta-overview'],
    queryFn: () => apiClient.get<TenantOverview>('/tenant-admin/overview'),
  })

  if (overviewQ.isLoading) return <Spinner />

  const d = overviewQ.data?.data

  const cards = [
    { label: 'Total Users', value: d?.total_users ?? '—' },
    { label: 'Active (30d)', value: d?.active_30d ?? '—' },
    { label: 'Classes', value: d?.total_classes ?? '—' },
    { label: 'SSO Providers', value: d?.sso_providers ?? '—' },
    { label: 'Pending Approvals', value: d?.pending_approvals ?? '—' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {d?.tenant_name && (
        <h2 style={{ fontSize: 16, color: 'var(--text-muted)' }}>
          Tenant: <span style={{ color: 'var(--text-color)' }}>{d.tenant_name}</span>
        </h2>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16 }}>
        {cards.map(c => (
          <div
            key={c.label}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius)',
              padding: '20px 24px',
            }}
          >
            <div style={{ fontSize: 28, fontWeight: 700 }}>{c.value}</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab 2: Users
// ---------------------------------------------------------------------------

interface TenantUserRoleModalProps {
  user: TenantUser
  onClose: () => void
}

function TenantUserRoleModal({ user, onClose }: TenantUserRoleModalProps) {
  const [role, setRole] = useState(user.role === 'professor' ? 'professor' : 'student')
  const [error, setError] = useState<string | null>(null)
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.put(`/tenant-admin/users/${user.user_id}/role`, { role }),
    onSuccess: result => {
      if (!result.ok) { setError(result.error ?? 'Failed'); return }
      qc.invalidateQueries({ queryKey: ['ta-users'] })
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
            </select>
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

function UsersTab() {
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [roleModalUser, setRoleModalUser] = useState<TenantUser | null>(null)
  const qc = useQueryClient()

  const usersQ = useQuery({
    queryKey: ['ta-users', page, q, roleFilter, statusFilter],
    queryFn: () =>
      apiClient.get<{ users: TenantUser[]; pages: number }>(
        `/tenant-admin/users?page=${page}&limit=50&q=${encodeURIComponent(q)}&role=${roleFilter}&status=${statusFilter}`,
      ),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient.put(`/tenant-admin/users/${id}/status`, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ta-users'] }),
  })

  const resetMutation = useMutation({
    mutationFn: (id: string) => apiClient.post(`/tenant-admin/users/${id}/force-reset`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ta-users'] }),
  })

  const impersonateMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient.post<{ token: string }>(`/tenant-admin/users/${id}/impersonate`),
    onSuccess: result => {
      if (!result.ok || !result.data?.token) return
      const original = localStorage.getItem('authToken')
      if (original) localStorage.setItem('original_token', original)
      localStorage.setItem('impersonation_token', result.data.token)
      window.location.reload()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.del(`/tenant-admin/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ta-users'] }),
  })

  const data = usersQ.data?.data

  return (
    <>
      {roleModalUser && (
        <TenantUserRoleModal user={roleModalUser} onClose={() => setRoleModalUser(null)} />
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
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Status</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Joined</th>
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
                  <td style={{ padding: '10px 16px' }}>
                    <StatusBadge status={u.account_status} />
                  </td>
                  <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>
                    {new Date(u.created_at).toLocaleDateString()}
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
                          if (window.confirm(`Impersonate ${u.name}? Your current token will be saved.`)) {
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
// Tab 3: Classes
// ---------------------------------------------------------------------------

function ClassesTab() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [transferEmail, setTransferEmail] = useState<Record<string, string>>({})
  const qc = useQueryClient()

  const classesQ = useQuery({
    queryKey: ['ta-classes', page, search],
    queryFn: () =>
      apiClient.get<{ classes: TenantClass[]; pages: number }>(
        `/tenant-admin/classes?page=${page}&limit=50&search=${encodeURIComponent(search)}`,
      ),
  })

  const transferMutation = useMutation({
    mutationFn: ({ id, email }: { id: string; email: string }) =>
      apiClient.put(`/tenant-admin/classes/${id}/transfer`, { professor_email: email }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ta-classes'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.del(`/tenant-admin/classes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ta-classes'] }),
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
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.classes.map(c => (
                <tr key={c.class_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '10px 16px' }}>{c.name}</td>
                  <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>{c.professor_email}</td>
                  <td style={{ padding: '10px 16px' }}>{c.total_students}</td>
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
                  <td colSpan={4} className="empty-state" style={{ padding: 32, textAlign: 'center' }}>
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
// Tab 4: SSO Config
// ---------------------------------------------------------------------------

interface SSOProviderModalProps {
  provider: SSOProvider | null
  onClose: () => void
}

function SSOProviderModal({ provider, onClose }: SSOProviderModalProps) {
  const isNew = provider === null
  const [providerName, setProviderName] = useState(provider?.provider_name ?? '')
  const [providerType, setProviderType] = useState<SSOProvider['provider_type']>(
    provider?.provider_type ?? 'oidc',
  )
  const [clientId, setClientId] = useState(provider?.client_id ?? '')
  const [clientSecret, setClientSecret] = useState('')
  const [discoveryUrl, setDiscoveryUrl] = useState(provider?.discovery_url ?? '')
  const [allowedDomains, setAllowedDomains] = useState(provider?.allowed_domains ?? '')
  const [defaultRole, setDefaultRole] = useState(provider?.default_role ?? 'student')
  const [roleMappingAttr, setRoleMappingAttr] = useState(
    provider?.role_mapping_attribute ?? '',
  )
  const [error, setError] = useState<string | null>(null)
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, string> = {
        provider_name: providerName,
        provider_type: providerType,
        client_id: clientId,
        allowed_domains: allowedDomains,
        default_role: defaultRole,
        role_mapping_attribute: roleMappingAttr,
      }
      if (clientSecret) payload.client_secret = clientSecret
      if (providerType === 'oidc' && discoveryUrl) payload.discovery_url = discoveryUrl

      if (isNew) {
        return apiClient.post('/sso/admin/providers', payload)
      }
      return apiClient.put(`/sso/admin/providers/${provider!.provider_id}`, payload)
    },
    onSuccess: result => {
      if (!result.ok) { setError(result.error ?? 'Failed'); return }
      qc.invalidateQueries({ queryKey: ['ta-sso-providers'] })
      onClose()
    },
  })

  return (
    <>
      <div className="modal-overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal>
        <div className="modal-header">
          <h2 className="modal-title">{isNew ? 'Add SSO Provider' : 'Edit SSO Provider'}</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form
          className="modal-body"
          onSubmit={e => { e.preventDefault(); mutation.mutate() }}
        >
          <div className="form-group">
            <label>Provider Name</label>
            <input
              value={providerName}
              onChange={e => setProviderName(e.target.value)}
              required
              placeholder="e.g. Company Google SSO"
            />
          </div>
          <div className="form-group">
            <label>Type</label>
            <select
              value={providerType}
              onChange={e => setProviderType(e.target.value as SSOProvider['provider_type'])}
            >
              <option value="oidc">oidc</option>
              <option value="google">google</option>
              <option value="microsoft">microsoft</option>
            </select>
          </div>
          <div className="form-group">
            <label>Client ID</label>
            <input
              value={clientId}
              onChange={e => setClientId(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>
              Client Secret
              {!isNew && (
                <span style={{ color: 'var(--text-muted)', fontSize: 12, marginLeft: 6 }}>
                  (leave blank to keep existing)
                </span>
              )}
            </label>
            <input
              type="password"
              value={clientSecret}
              onChange={e => setClientSecret(e.target.value)}
              required={isNew}
              autoComplete="new-password"
            />
          </div>
          {providerType === 'oidc' && (
            <div className="form-group">
              <label>Discovery URL</label>
              <input
                value={discoveryUrl}
                onChange={e => setDiscoveryUrl(e.target.value)}
                placeholder="https://accounts.example.com/.well-known/openid-configuration"
              />
            </div>
          )}
          <div className="form-group">
            <label>Allowed Domains (comma-separated)</label>
            <input
              value={allowedDomains}
              onChange={e => setAllowedDomains(e.target.value)}
              placeholder="example.com, example.edu"
            />
          </div>
          <div className="form-group">
            <label>Default Role</label>
            <select value={defaultRole} onChange={e => setDefaultRole(e.target.value)}>
              <option value="student">student</option>
              <option value="professor">professor</option>
            </select>
          </div>
          <div className="form-group">
            <label>Role Mapping Attribute (optional)</label>
            <input
              value={roleMappingAttr}
              onChange={e => setRoleMappingAttr(e.target.value)}
              placeholder="e.g. groups"
            />
          </div>
          {error && <p className="alert alert-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving…' : isNew ? 'Add Provider' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

function SSOConfigTab() {
  const [showModal, setShowModal] = useState(false)
  const [editProvider, setEditProvider] = useState<SSOProvider | null>(null)
  const qc = useQueryClient()

  const providersQ = useQuery({
    queryKey: ['ta-sso-providers'],
    queryFn: () =>
      apiClient.get<{ providers: SSOProvider[] }>('/sso/admin/providers'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.del(`/sso/admin/providers/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ta-sso-providers'] }),
  })

  const modalProvider = showModal && !editProvider ? null : editProvider
  const modalOpen = showModal || editProvider !== null

  const typeColors: Record<string, string> = {
    oidc: 'var(--color-info)',
    google: 'var(--color-danger)',
    microsoft: 'var(--color-primary)',
  }

  return (
    <>
      {modalOpen && (
        <SSOProviderModal
          provider={modalProvider}
          onClose={() => { setShowModal(false); setEditProvider(null) }}
        />
      )}

      <div style={{ marginBottom: 16 }}>
        <button
          className="btn btn-primary"
          onClick={() => { setEditProvider(null); setShowModal(true) }}
        >
          + Add Provider
        </button>
      </div>

      {providersQ.isLoading ? (
        <Spinner />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {providersQ.data?.data?.providers.map(p => (
            <div
              key={p.provider_id}
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius)',
                padding: '16px 20px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {p.provider_name}
                  <span
                    className="badge"
                    style={{ marginLeft: 8, background: typeColors[p.provider_type] ?? 'var(--text-muted)', color: '#fff', fontSize: 11 }}
                  >
                    {p.provider_type}
                  </span>
                  <span
                    className="badge"
                    style={{ marginLeft: 6, background: p.is_enabled ? 'var(--color-success)' : 'var(--text-muted)', color: '#fff', fontSize: 11 }}
                  >
                    {p.is_enabled ? 'enabled' : 'disabled'}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  Client ID: {p.client_id}
                  {p.allowed_domains && ` · Domains: ${p.allowed_domains}`}
                  {` · Default role: ${p.default_role}`}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="btn btn-sm btn-ghost"
                  onClick={() => { setEditProvider(p); setShowModal(false) }}
                >
                  Edit
                </button>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => {
                    if (window.confirm(`Delete SSO provider "${p.provider_name}"?`)) {
                      deleteMutation.mutate(p.provider_id)
                    }
                  }}
                  disabled={deleteMutation.isPending}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
          {(providersQ.data?.data?.providers.length ?? 0) === 0 && (
            <div className="empty-state" style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
              No SSO providers configured
            </div>
          )}
        </div>
      )}
    </>
  )
}

// ---------------------------------------------------------------------------
// Tab 5: Approvals
// ---------------------------------------------------------------------------

function ApprovalsTab() {
  const qc = useQueryClient()

  const approvalsQ = useQuery({
    queryKey: ['ta-approvals'],
    queryFn: () =>
      apiClient.get<{ pending: PendingApproval[] }>('/tenant-admin/pending-approvals'),
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => apiClient.put(`/tenant-admin/users/${id}/approve`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ta-approvals'] }),
  })

  const denyMutation = useMutation({
    mutationFn: (id: string) => apiClient.put(`/tenant-admin/users/${id}/deny`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ta-approvals'] }),
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
// Tab 6: Audit
// ---------------------------------------------------------------------------

function AuditTab() {
  const [page, setPage] = useState(1)

  const auditQ = useQuery({
    queryKey: ['ta-audit', page],
    queryFn: () =>
      apiClient.get<{ logs: TenantAuditLog[]; pages: number }>(
        `/tenant-admin/audit?page=${page}&limit=50`,
      ),
  })

  const data = auditQ.data?.data

  return (
    <div
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius)',
        overflow: 'hidden',
      }}
    >
      {auditQ.isLoading ? (
        <Spinner />
      ) : (
        <>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Action</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>User</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Resource</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Timestamp</th>
                <th style={{ textAlign: 'left', padding: '10px 16px' }}>Details</th>
              </tr>
            </thead>
            <tbody>
              {data?.logs.map(log => (
                <tr key={log.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '10px 16px' }}>{log.action}</td>
                  <td style={{ padding: '10px 16px' }}>{log.user_name}</td>
                  <td style={{ padding: '10px 16px' }}>{log.resource_type}</td>
                  <td style={{ padding: '10px 16px', color: 'var(--text-muted)' }}>
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td
                    style={{
                      padding: '10px 16px',
                      color: 'var(--text-muted)',
                      maxWidth: 220,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {log.details}
                  </td>
                </tr>
              ))}
              {(!data?.logs || data.logs.length === 0) && (
                <tr>
                  <td colSpan={5} style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
                    No audit logs
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <div style={{ padding: '8px 16px' }}>
            <Pagination page={page} pages={data?.pages ?? 1} onPage={setPage} />
          </div>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Root component
// ---------------------------------------------------------------------------

export default function TenantAdminDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  return (
    <div className="page">
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 24 }}>Tenant Admin</h1>

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
      {activeTab === 'users' && <UsersTab />}
      {activeTab === 'classes' && <ClassesTab />}
      {activeTab === 'sso' && <SSOConfigTab />}
      {activeTab === 'approvals' && <ApprovalsTab />}
      {activeTab === 'audit' && <AuditTab />}
    </div>
  )
}
