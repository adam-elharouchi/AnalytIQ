/**
 * Tenant Admin Dashboard Logic
 * Mirrors SuperAdminDashboard but scoped to a single tenant.
 * No tenant management, announcements, or platform-settings tabs.
 */

class TenantAdminDashboard {
    constructor() {
        const _base = window.API_BASE_URL || '/api';
        const origin = window.location.protocol + '//' + window.location.host;
        const apiRoot = _base.startsWith('http') ? _base : origin + _base;
        this.baseUrl = apiRoot + '/tenant-admin';
        this.ssoUrl  = apiRoot + '/sso/admin';
        this._auditPage = 1;
        this._currentUserId = null;   // user shown in user-detail modal
        this._currentUserStatus = null;
        this.init();
    }

    async init() {
        if (!this.verifyAccess()) return;
        this.setupNavigation();
        this.setupEventListeners();
        await this.loadOverview();
        await this.loadUsers();
        await this.loadPendingApprovals(false);  // badge only on start
    }

    verifyAccess() {
        let currentUser = null;
        try { currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}'); } catch (e) {}
        const role  = currentUser.role || localStorage.getItem('user_role');
        const token = localStorage.getItem('authToken');
        if (!token) { window.location.href = '/login.html'; return false; }
        if (role !== 'tenant_admin') {
            console.warn('Tenant admin access denied, role=', role);
            window.location.href = '/';
            return false;
        }
        return true;
    }

    setupNavigation() {
        const tabs     = document.querySelectorAll('.terminal-tab-btn[data-target]');
        const sections = document.querySelectorAll('.admin-section');

        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                tabs.forEach(t => t.classList.remove('active'));
                e.currentTarget.classList.add('active');

                const targetId = e.currentTarget.getAttribute('data-target');
                sections.forEach(s => {
                    s.classList.remove('active');
                    if (s.id === targetId) s.classList.add('active');
                });
            });
        });

        // Honor sessionStorage tab hint from home page card links
        const hint = sessionStorage.getItem('ta_tab');
        if (hint) {
            sessionStorage.removeItem('ta_tab');
            const target = document.querySelector(`.terminal-tab-btn[data-target="${hint}"]`);
            if (target) target.click();
        }
    }

    setupEventListeners() {
        const searchInput = document.getElementById('user-search-input');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.loadUsers(1);
            });
        }
        const classSearch = document.getElementById('class-admin-search');
        if (classSearch) {
            classSearch.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.loadAllClasses(1);
            });
        }
    }

    // ============================================================
    // Overview
    // ============================================================

    async loadOverview() {
        try {
            const res = await authFetch(`${this.baseUrl}/overview`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load overview');
            const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? 0; };
            set('stat-total-users',       data.total_users);
            set('stat-active-30d',        data.active_30d);
            set('stat-total-classes',     data.total_classes);
            set('stat-sso-providers',     data.sso_providers);
            set('stat-pending-approvals', data.pending_approvals);

            // Populate identity header quick-stats
            set('header-stat-users',   data.total_users);
            set('header-stat-classes', data.total_classes);
            set('header-stat-pending', data.pending_approvals);

            // Populate breadcrumb tenant name if available
            if (data.tenant_name) {
                const crumb = document.getElementById('tenant-name-breadcrumb');
                if (crumb) crumb.textContent = data.tenant_name.toLowerCase().replace(/\s+/g, '-');
                const desc = document.getElementById('tenant-identity-desc');
                if (desc) desc.textContent = `Manage users, classes, SSO, and approvals for ${data.tenant_name}.`;
            }
            const countLabel = document.getElementById('tenant-user-count');
            if (countLabel) countLabel.textContent = `· ${data.total_users ?? 0} users`;

            const badge = document.getElementById('approvals-badge');
            const count = data.pending_approvals || 0;
            if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'inline' : 'none'; }
        } catch (err) {
            console.error('loadOverview failed:', err);
        }
    }

    // ============================================================
    // Analytics
    // ============================================================

    async loadAnalytics() {
        ['an-total-users','an-new-7d','an-new-30d','an-active-7d','an-active-30d',
         'an-classes','an-chapters','an-exercises','an-completions'].forEach(id => {
            const el = document.getElementById(id); if (el) el.textContent = '…';
        });
        try {
            const res = await authFetch(`${this.baseUrl}/analytics`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load analytics');

            const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? '—'; };
            set('an-total-users',  data.users?.total);
            set('an-new-7d',       data.users?.new_7d);
            set('an-new-30d',      data.users?.new_30d);
            set('an-active-7d',    data.users?.active_7d);
            set('an-active-30d',   data.users?.active_30d);
            set('an-classes',      data.content?.classes);
            set('an-chapters',     data.content?.chapters);
            set('an-exercises',    data.content?.exercises);
            set('an-completions',  data.content?.completions);

            const rolesEl = document.getElementById('an-roles');
            if (rolesEl && data.users?.by_role) {
                const breakdown = data.users.by_role;
                const total = Object.values(breakdown).reduce((a, b) => a + b, 0) || 1;
                rolesEl.innerHTML = Object.entries(breakdown).map(([role, count]) => {
                    const pct = Math.round((count / total) * 100);
                    return `<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
                        <span style="min-width:90px;font-size:0.85rem;text-transform:capitalize;">${escapeHtml(role)}</span>
                        <div style="flex:1;height:8px;background:var(--bg-dark);border-radius:4px;overflow:hidden;">
                            <div style="width:${pct}%;height:100%;background:var(--primary-color);border-radius:4px;"></div>
                        </div>
                        <span style="font-size:0.85rem;color:var(--text-muted);min-width:35px;text-align:right;">${count}</span>
                    </div>`;
                }).join('');
            }

            const actionsEl = document.getElementById('an-actions');
            if (actionsEl && data.top_actions) {
                const maxCount = data.top_actions[0]?.count || 1;
                actionsEl.innerHTML = data.top_actions.slice(0, 8).map(a => {
                    const pct = Math.round((a.count / maxCount) * 100);
                    return `<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
                        <span style="min-width:160px;font-size:0.8rem;font-family:monospace;color:var(--text-muted);">${escapeHtml(a.action)}</span>
                        <div style="flex:1;height:8px;background:var(--bg-dark);border-radius:4px;overflow:hidden;">
                            <div style="width:${pct}%;height:100%;background:var(--color-success, #10b981);border-radius:4px;"></div>
                        </div>
                        <span style="font-size:0.85rem;color:var(--text-muted);min-width:30px;text-align:right;">${a.count}</span>
                    </div>`;
                }).join('');
            }
        } catch (err) {
            console.error('loadAnalytics failed:', err);
            showError(err.message);
        }
    }

    // ============================================================
    // Users
    // ============================================================

    async loadUsers(page = 1) {
        try {
            const q      = document.getElementById('user-search-input')?.value || '';
            const role   = document.getElementById('user-filter-role')?.value || '';
            const status = document.getElementById('user-filter-status')?.value || '';
            const params = new URLSearchParams({ page, limit: 50 });
            if (q)      params.set('q', q);
            if (role)   params.set('role', role);
            if (status) params.set('status', status);

            const res  = await authFetch(`${this.baseUrl}/users?${params}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load users');

            // Role distribution
            if (data.users) {
                const counts = { tenant_admin: 0, professor: 0, student: 0 };
                data.users.forEach(u => { if (u.role in counts) counts[u.role]++; });
                const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
                set('dist-tenant-admin', counts.tenant_admin);
                set('dist-professor',    counts.professor);
                set('dist-student',      counts.student);
            }
            this.renderUsers(data.users || [], data.current_page, data.pages || 1);
        } catch (err) {
            console.error('loadUsers failed:', err);
            showError(err.message);
        }
    }

    renderUsers(users, currentPage, totalPages) {
        const tbody = document.getElementById('users-table-body');
        if (!tbody) return;
        if (!users.length) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:1.5rem;color:var(--text-muted);">No users found.</td></tr>';
            this._renderUsersPager(null, currentPage, totalPages);
            return;
        }

        tbody.innerHTML = users.map(u => {
            const safeId     = escapeHtml(u.user_id);
            const safeName   = escapeHtml(u.name).replace(/'/g, "\\'");
            const safeEmail  = escapeHtml(u.email).replace(/'/g, "\\'");
            const safeRole   = escapeHtml(u.role);
            const safeStatus = escapeHtml(u.account_status);
            const roleBadge = `<span style="background:var(--bg-dark);border:1px solid var(--border-color);color:var(--text-color);padding:2px 8px;border-radius:4px;font-size:0.8rem;text-transform:capitalize;">${safeRole}</span>`;
            const statusBadge = u.account_status === 'active'
                ? '<span class="status-badge active">Active</span>'
                : u.account_status === 'disabled'
                    ? '<span class="status-badge disabled">Disabled</span>'
                    : `<span class="status-badge pending">${safeStatus}</span>`;
            return `<tr style="border-bottom:1px solid var(--border-color);">
                <td style="padding:1rem;">
                    <div style="font-weight:500;">${escapeHtml(u.name)}</div>
                    <div style="font-size:0.85rem;color:var(--text-muted);">${escapeHtml(u.email)}</div>
                </td>
                <td style="padding:1rem;">${roleBadge}</td>
                <td style="padding:1rem;">${statusBadge}</td>
                <td style="padding:0.75rem 1rem;">
                    <div class="icon-btn-row">
                        <button class="icon-btn" title="Manage User"
                            onclick="window.tenantAdminApp.openUserModal('${safeId}','${safeName}','${safeEmail}','${safeRole}','${safeStatus}')">
                            <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
                        </button>
                        <button class="icon-btn ${u.account_status === 'disabled' ? 'icon-btn-success' : 'icon-btn-amber'}"
                            title="${u.account_status === 'disabled' ? 'Enable Account' : 'Disable Account'}"
                            onclick="window.tenantAdminApp.quickToggleStatus('${safeId}','${safeStatus}')">
                            ${u.account_status === 'disabled'
                                ? `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="10 8 16 12 10 16 10 8"/></svg>`
                                : `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="10" y1="15" x2="10" y2="9"/><line x1="14" y1="15" x2="14" y2="9"/></svg>`}
                        </button>
                        <button class="icon-btn" title="Reset Password"
                            onclick="window.tenantAdminApp.quickPasswordReset('${safeId}')">
                            <svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                        </button>
                    </div>
                </td>
            </tr>`;
        }).join('');
        this._renderUsersPager(users, currentPage, totalPages);
    }

    _renderUsersPager(users, currentPage, totalPages) {
        const pager = document.getElementById('users-pagination');
        if (!pager) return;
        if (!totalPages || totalPages <= 1) { pager.innerHTML = ''; return; }
        const prev = currentPage > 1
            ? `<button class="btn btn-secondary" onclick="window.tenantAdminApp.loadUsers(${currentPage - 1})">← Prev</button>`
            : '';
        const next = currentPage < totalPages
            ? `<button class="btn btn-secondary" onclick="window.tenantAdminApp.loadUsers(${currentPage + 1})">Next →</button>`
            : '';
        pager.innerHTML = `${prev}<span style="display:flex;align-items:center;padding:0 1rem;color:var(--text-muted);">Page ${currentPage} of ${totalPages}</span>${next}`;
    }

    // ============================================================
    // User Detail Modal
    // ============================================================

    openUserModal(userId, name, email, role, status) {
        this._currentUserId     = userId;
        this._currentUserStatus = status;

        document.getElementById('user-modal-title').textContent  = 'User Actions';
        document.getElementById('user-modal-name').textContent   = name;
        document.getElementById('user-modal-email').textContent  = email;
        document.getElementById('user-modal-error').style.display = 'none';

        const roleSelect = document.getElementById('user-modal-role-select');
        if (roleSelect) roleSelect.value = role;

        const statusBtn = document.getElementById('user-modal-status-btn-label');
        if (statusBtn) statusBtn.textContent = status === 'active' ? 'Disable Account' : 'Enable Account';

        document.getElementById('user-detail-modal').style.display = 'flex';
    }

    closeUserModal() {
        document.getElementById('user-detail-modal').style.display = 'none';
        this._currentUserId = null;
    }

    _showUserModalError(msg) {
        const el = document.getElementById('user-modal-error');
        if (el) { el.textContent = msg; el.style.display = 'block'; }
    }

    async changeRole() {
        const userId  = this._currentUserId;
        const newRole = document.getElementById('user-modal-role-select')?.value;
        if (!userId || !newRole) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/users/${userId}/role`, {
                method: 'PATCH', body: JSON.stringify({ role: newRole })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Role update failed');
            showSuccess(`Role updated to ${newRole}.`);
            this.closeUserModal();
            this.loadUsers();
        } catch (err) { this._showUserModalError(err.message); }
    }

    async toggleStatus() {
        const userId    = this._currentUserId;
        const newStatus = this._currentUserStatus === 'active' ? 'disabled' : 'active';
        if (!userId) return;
        if (!confirm(`${newStatus === 'disabled' ? 'Disable' : 'Enable'} this account?`)) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/users/${userId}/status`, {
                method: 'PATCH', body: JSON.stringify({ status: newStatus })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Status update failed');
            showSuccess(`User ${newStatus === 'active' ? 'enabled' : 'disabled'}.`);
            this.closeUserModal();
            this.loadUsers();
        } catch (err) { this._showUserModalError(err.message); }
    }

    async forcePasswordReset() {
        const userId = this._currentUserId;
        if (!userId) return;
        if (!confirm('Force this user to change their password on next login?')) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/users/${userId}/force-reset`, { method: 'POST' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Reset failed');
            showSuccess(data.message || 'Password reset flagged.');
            this.closeUserModal();
        } catch (err) { this._showUserModalError(err.message); }
    }

    async impersonateUser() {
        const userId = this._currentUserId;
        if (!userId) return;
        if (!confirm('Impersonate this user? All actions will be logged.')) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/users/${userId}/impersonate`, { method: 'POST' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Impersonation failed');
            if (data.token) {
                if (!localStorage.getItem('original_token')) {
                    localStorage.setItem('original_token', localStorage.getItem('authToken'));
                    localStorage.setItem('original_user',  localStorage.getItem('currentUser'));
                }
                localStorage.setItem('authToken', data.token);
                let dest = '/student-classes.html';
                try {
                    const payload = JSON.parse(atob(data.token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));
                    localStorage.setItem('currentUser', JSON.stringify({
                        user_id: payload.user_id, name: payload.name, email: payload.email, role: payload.role
                    }));
                    dest = payload.role === 'professor' ? '/professor-dashboard.html' : '/student-classes.html';
                } catch (e) { console.error('JWT decode failed:', e); }
                localStorage.setItem('impersonation_started_at', Date.now().toString());
                window.location.href = dest;
            }
        } catch (err) { this._showUserModalError(err.message); }
    }

    async exportUser() {
        const userId = this._currentUserId;
        if (!userId) return;
        try {
            const token = localStorage.getItem('authToken');
            const res   = await fetch(`${this.baseUrl}/users/${userId}/export`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) { const d = await res.json(); throw new Error(d.error || 'Export failed'); }
            const blob = await res.blob();
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement('a');
            a.href     = url;
            a.download = `user-export-${userId}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) { this._showUserModalError(err.message); }
    }

    async deleteUser() {
        const userId = this._currentUserId;
        if (!userId) return;
        const name = document.getElementById('user-modal-name')?.textContent || userId;
        if (!confirm(`Permanently delete "${name}"?\n\nThis removes the user and all associated data. This action cannot be undone.`)) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/users/${userId}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Delete failed');
            showSuccess(data.message || `${name} deleted.`);
            this.closeUserModal();
            this.loadUsers();
        } catch (err) { this._showUserModalError(err.message); }
    }

    // Direct action helpers (used by icon buttons in user table rows)
    async quickToggleStatus(userId, currentStatus) {
        const newStatus = currentStatus === 'active' ? 'disabled' : 'active';
        if (!confirm(`${newStatus === 'disabled' ? 'Disable' : 'Enable'} this account?`)) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/users/${userId}/status`, {
                method: 'PATCH', body: JSON.stringify({ status: newStatus })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Status update failed');
            showSuccess(`User ${newStatus === 'active' ? 'enabled' : 'disabled'}.`);
            this.loadUsers();
        } catch (err) { showError(err.message); }
    }

    async quickPasswordReset(userId) {
        if (!confirm('Force this user to change their password on next login?')) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/users/${userId}/force-reset`, { method: 'POST' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Reset failed');
            showSuccess(data.message || 'Password reset flagged.');
        } catch (err) { showError(err.message); }
    }

    // ============================================================
    // Pending Approvals
    // ============================================================

    async loadPendingApprovals(renderTable = true) {
        try {
            const res  = await authFetch(`${this.baseUrl}/pending-approvals`);
            if (!res.ok) return;
            const data = await res.json();
            const count = data.count || 0;

            const badge = document.getElementById('approvals-badge');
            const stat  = document.getElementById('stat-pending-approvals');
            if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'inline' : 'none'; }
            if (stat)  stat.textContent = count;

            if (!renderTable) return;

            const tbody   = document.getElementById('approvals-table-body');
            const empty   = document.getElementById('approvals-empty');
            const wrapper = document.getElementById('approvals-table-wrapper');
            if (!tbody) return;

            if (!count) {
                if (wrapper) wrapper.style.display = 'none';
                if (empty)   empty.style.display = 'block';
                return;
            }
            if (wrapper) wrapper.style.display = '';
            if (empty)   empty.style.display = 'none';

            tbody.innerHTML = (data.pending || []).map(u => {
                const date = u.created_at ? new Date(u.created_at).toLocaleDateString() : '—';
                return `<tr style="border-bottom:1px solid var(--border-color);">
                    <td style="padding:1rem;">
                        <div style="font-weight:500;">${escapeHtml(u.name)}</div>
                        <div style="font-size:0.85rem;color:var(--text-muted);">${escapeHtml(u.email)}</div>
                    </td>
                    <td style="padding:1rem;">
                        <span style="background:rgba(234,179,8,0.2);color:#facc15;padding:2px 8px;border-radius:4px;font-size:0.8rem;font-weight:bold;text-transform:capitalize;">${escapeHtml(u.role)}</span>
                    </td>
                    <td style="padding:1rem;color:var(--text-muted);font-size:0.9rem;">${date}</td>
                    <td style="padding:1rem;text-align:right;display:flex;gap:0.5rem;justify-content:flex-end;">
                        <button class="btn btn-sm" style="background:var(--color-success, #10b981);color:#fff;border:none;"
                            onclick="window.tenantAdminApp.approveUser('${u.user_id}','${escapeHtml(u.name).replace(/'/g,"\\'")}')">
                            Approve
                        </button>
                        <button class="btn btn-sm btn-danger"
                            onclick="window.tenantAdminApp.denyUser('${u.user_id}','${escapeHtml(u.name).replace(/'/g,"\\'")}')">
                            Deny
                        </button>
                    </td>
                </tr>`;
            }).join('');
        } catch (err) {
            console.error('loadPendingApprovals failed:', err);
        }
    }

    async approveUser(userId, name) {
        if (!confirm(`Approve account for ${name}?`)) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/users/${userId}/approve`, { method: 'PATCH' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Approval failed');
            showSuccess(data.message || `${name} approved.`);
            this.loadPendingApprovals(true);
            this.loadOverview();
        } catch (err) { showError(err.message); }
    }

    async denyUser(userId, name) {
        if (!confirm(`Deny account for ${name}?`)) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/users/${userId}/deny`, { method: 'PATCH' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Denial failed');
            showSuccess(data.message || `${name}'s account denied.`);
            this.loadPendingApprovals(true);
            this.loadOverview();
        } catch (err) { showError(err.message); }
    }

    // ============================================================
    // Classes
    // ============================================================

    async loadAllClasses(page = 1) {
        const tbody = document.getElementById('classes-admin-table-body');
        if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">Loading…</td></tr>';
        try {
            const q      = document.getElementById('class-admin-search')?.value || '';
            const params = new URLSearchParams({ page, limit: 50 });
            if (q) params.set('q', q);
            const res  = await authFetch(`${this.baseUrl}/classes?${params}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load classes');

            const classes = data.classes || [];
            if (!classes.length) {
                if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No classes found.</td></tr>';
                return;
            }

            if (tbody) tbody.innerHTML = classes.map(c => {
                const safeName = escapeHtml(c.name).replace(/'/g, "\\'");
                return `<tr style="border-bottom:1px solid var(--border-color);">
                    <td style="padding:1rem;">
                        <div style="font-weight:500;">${escapeHtml(c.name)}</div>
                        <div style="font-size:0.8rem;color:var(--text-muted);">${escapeHtml(c.class_id)}</div>
                    </td>
                    <td style="padding:1rem;">
                        <div>${escapeHtml(c.professor_name || '—')}</div>
                        <div style="font-size:0.8rem;color:var(--text-muted);">${escapeHtml(c.professor_email || '')}</div>
                    </td>
                    <td style="padding:1rem;text-align:center;">${c.student_count || 0}</td>
                    <td style="padding:1rem;text-align:center;">${c.chapter_count || 0}</td>
                    <td style="padding:1rem;text-align:right;display:flex;gap:0.4rem;justify-content:flex-end;">
                        <button class="btn btn-sm btn-secondary"
                            onclick="window.tenantAdminApp.transferClass('${c.class_id}','${safeName}')">Transfer</button>
                        <button class="btn btn-sm btn-danger"
                            onclick="window.tenantAdminApp.deleteClass('${c.class_id}','${safeName}')">Delete</button>
                    </td>
                </tr>`;
            }).join('');

            const pager = document.getElementById('classes-admin-pagination');
            if (pager) {
                const prev = page > 1 ? `<button class="btn btn-secondary" onclick="window.tenantAdminApp.loadAllClasses(${page-1})">← Prev</button>` : '';
                const next = page < (data.pages || 1) ? `<button class="btn btn-secondary" onclick="window.tenantAdminApp.loadAllClasses(${page+1})">Next →</button>` : '';
                const info = `<span style="display:flex;align-items:center;color:var(--text-muted);font-size:0.85rem;">Page ${page} of ${data.pages || 1} (${data.total || classes.length} classes)</span>`;
                pager.innerHTML = `${prev}${info}${next}`;
            }
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:var(--color-danger, #ef4444);text-align:center;">${escapeHtml(err.message)}</td></tr>`;
        }
    }

    async transferClass(classId, className) {
        const newProfEmail = prompt(`Transfer class "${className}" to another professor.\n\nEnter the professor's email address (must be in your organization):`);
        if (!newProfEmail) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/classes/${classId}/transfer`, {
                method: 'PATCH', body: JSON.stringify({ professor_email: newProfEmail.trim() })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Transfer failed');
            showSuccess(data.message || 'Class transferred.');
            this.loadAllClasses();
        } catch (err) { showError(err.message); }
    }

    async deleteClass(classId, className) {
        if (!confirm(`Permanently delete class "${className}"?\n\nThis removes all chapters, exercises, and enrollments. This action cannot be undone.`)) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/classes/${classId}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Delete failed');
            showSuccess(data.message || `Class deleted.`);
            this.loadAllClasses();
        } catch (err) { showError(err.message); }
    }

    // ============================================================
    // SSO Providers
    // ============================================================

    async loadSSOProviders() {
        const tbody = document.getElementById('sso-providers-table-body');
        if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">Loading…</td></tr>';
        try {
            const res  = await authFetch(`${this.ssoUrl}/providers`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load SSO providers');

            const providers = data.providers || [];
            if (!providers.length) {
                if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:2rem;">No SSO providers configured. Click "Add Provider" to get started.</td></tr>';
                return;
            }

            if (tbody) tbody.innerHTML = providers.map(p => {
                const statusBadge = p.is_enabled
                    ? '<span class="status-badge enabled">Enabled</span>'
                    : '<span class="status-badge disabled-sso">Disabled</span>';
                const discoveryShort = p.discovery_url
                    ? (p.discovery_url.length > 50 ? p.discovery_url.substring(0, 50) + '…' : p.discovery_url)
                    : '—';
                return `<tr style="border-bottom:1px solid var(--border-color);">
                    <td style="padding:1rem;font-weight:500;">${escapeHtml(p.provider_name)}</td>
                    <td style="padding:1rem;text-transform:capitalize;">
                        <span style="background:var(--bg-dark);border:1px solid var(--border-color);padding:2px 8px;border-radius:4px;font-size:0.8rem;">${escapeHtml(p.provider_type)}</span>
                    </td>
                    <td style="padding:1rem;font-size:0.85rem;color:var(--text-muted);" title="${escapeHtml(p.discovery_url || '')}">${escapeHtml(discoveryShort)}</td>
                    <td style="padding:1rem;">${statusBadge}</td>
                    <td style="padding:1rem;text-align:right;display:flex;gap:0.4rem;justify-content:flex-end;">
                        <button class="btn btn-sm btn-secondary"
                            onclick="window.tenantAdminApp.editSSOProvider('${p.provider_id}')">Edit</button>
                        <button class="btn btn-sm btn-danger"
                            onclick="window.tenantAdminApp.deleteSSOProvider('${p.provider_id}','${escapeHtml(p.provider_name).replace(/'/g,"\\'")}')">Delete</button>
                    </td>
                </tr>`;
            }).join('');
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:var(--color-danger, #ef4444);text-align:center;">${escapeHtml(err.message)}</td></tr>`;
        }
    }

    showSSOProviderModal(providerId = null) {
        // Clear form
        document.getElementById('sso-provider-id').value      = '';
        document.getElementById('sso-provider-name').value    = '';
        document.getElementById('sso-provider-type').value    = 'oidc';
        document.getElementById('sso-client-id').value        = '';
        document.getElementById('sso-client-secret').value    = '';
        document.getElementById('sso-discovery-url').value    = '';
        document.getElementById('sso-allowed-domains').value  = '';
        document.getElementById('sso-default-role').value     = 'student';
        document.getElementById('sso-role-attr').value        = '';
        document.getElementById('sso-modal-error').style.display = 'none';
        document.getElementById('sso-modal-title').textContent = providerId ? 'Edit SSO Provider' : 'Add SSO Provider';
        document.getElementById('sso-provider-modal').style.display = 'flex';
    }

    async editSSOProvider(providerId) {
        this.showSSOProviderModal(providerId);
        try {
            const res  = await authFetch(`${this.ssoUrl}/providers/${providerId}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load provider');
            const p = data.provider || data;
            document.getElementById('sso-provider-id').value      = p.provider_id || providerId;
            document.getElementById('sso-provider-name').value    = p.provider_name || '';
            document.getElementById('sso-provider-type').value    = p.provider_type || 'oidc';
            document.getElementById('sso-client-id').value        = p.client_id || '';
            document.getElementById('sso-client-secret').value    = '';  // never prefill secrets
            document.getElementById('sso-discovery-url').value    = p.discovery_url || '';
            document.getElementById('sso-allowed-domains').value  = (p.allowed_domains || []).join(', ');
            document.getElementById('sso-default-role').value     = p.default_role || 'student';
            document.getElementById('sso-role-attr').value        = p.role_mapping_attribute || '';
        } catch (err) {
            document.getElementById('sso-modal-error').textContent = err.message;
            document.getElementById('sso-modal-error').style.display = 'block';
        }
    }

    closeSSOProviderModal() {
        document.getElementById('sso-provider-modal').style.display = 'none';
    }

    async saveSSOProvider() {
        const providerId    = document.getElementById('sso-provider-id').value.trim();
        const providerName  = document.getElementById('sso-provider-name').value.trim();
        const providerType  = document.getElementById('sso-provider-type').value;
        const clientId      = document.getElementById('sso-client-id').value.trim();
        const clientSecret  = document.getElementById('sso-client-secret').value;
        const discoveryUrl  = document.getElementById('sso-discovery-url').value.trim();
        const allowedRaw    = document.getElementById('sso-allowed-domains').value;
        const defaultRole   = document.getElementById('sso-default-role').value;
        const roleAttr      = document.getElementById('sso-role-attr').value.trim();

        const errEl = document.getElementById('sso-modal-error');
        errEl.style.display = 'none';

        if (!providerName) { errEl.textContent = 'Provider name is required.'; errEl.style.display = 'block'; return; }
        if (!clientId)     { errEl.textContent = 'Client ID is required.'; errEl.style.display = 'block'; return; }
        if (!discoveryUrl) { errEl.textContent = 'Discovery URL is required.'; errEl.style.display = 'block'; return; }
        if (!providerId && !clientSecret) { errEl.textContent = 'Client secret is required for new providers.'; errEl.style.display = 'block'; return; }

        const allowedDomains = allowedRaw.split(',').map(d => d.trim()).filter(Boolean);

        const body = {
            provider_name:          providerName,
            provider_type:          providerType,
            client_id:              clientId,
            discovery_url:          discoveryUrl,
            allowed_domains:        allowedDomains,
            default_role:           defaultRole,
            role_mapping_attribute: roleAttr || null,
        };
        if (clientSecret) body.client_secret = clientSecret;

        try {
            let res;
            if (providerId) {
                res = await authFetch(`${this.ssoUrl}/providers/${providerId}`, {
                    method: 'PUT', body: JSON.stringify(body)
                });
            } else {
                res = await authFetch(`${this.ssoUrl}/providers`, {
                    method: 'POST', body: JSON.stringify(body)
                });
            }
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to save provider');
            showSuccess(data.message || 'SSO provider saved.');
            this.closeSSOProviderModal();
            this.loadSSOProviders();
            this.loadOverview();
        } catch (err) {
            errEl.textContent = err.message;
            errEl.style.display = 'block';
        }
    }

    async deleteSSOProvider(providerId, providerName) {
        if (!confirm(`Delete SSO provider "${providerName}"?\n\nUsers who sign in via this provider will lose their SSO link. This action cannot be undone.`)) return;
        try {
            const res  = await authFetch(`${this.ssoUrl}/providers/${providerId}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Delete failed');
            showSuccess(data.message || 'Provider deleted.');
            this.loadSSOProviders();
            this.loadOverview();
        } catch (err) { showError(err.message); }
    }

    // ============================================================
    // Audit Log
    // ============================================================

    async loadAuditLog(page = 1) {
        this._auditPage = page;
        const action = document.getElementById('audit-action-filter')?.value || '';
        const from   = document.getElementById('audit-from')?.value || '';
        const to     = document.getElementById('audit-to')?.value || '';

        const tbody = document.getElementById('audit-table-body');
        if (tbody) tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);">Loading…</td></tr>';

        try {
            const params = new URLSearchParams({ page, limit: 50 });
            if (action) params.set('action', action);
            if (from)   params.set('from', from);
            if (to)     params.set('to', to);

            const res  = await authFetch(`${this.baseUrl}/audit?${params}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load audit log');
            this.renderAuditLog(data.entries || [], data.total, data.pages, page);
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="4" style="color:var(--color-danger, #ef4444);text-align:center;">${escapeHtml(err.message)}</td></tr>`;
        }
    }

    renderAuditLog(entries, total, pages, currentPage) {
        const tbody = document.getElementById('audit-table-body');
        const pager = document.getElementById('audit-pagination');
        if (!tbody) return;

        if (!entries.length) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);">No audit entries found.</td></tr>';
            if (pager) pager.innerHTML = '';
            return;
        }

        const actionColors = {
            IMPERSONATE_USER: '#f59e0b', DISABLE_USER: '#ef4444', ENABLE_USER: '#10b981',
            DELETE_USER: '#ef4444', DELETE_CLASS: '#ef4444', DELETE_CHAPTER: '#ef4444',
        };

        tbody.innerHTML = entries.map(e => {
            const ts    = e.created_at ? new Date(e.created_at).toLocaleString() : '—';
            const actor = e.user_name
                ? `${escapeHtml(e.user_name)}<br><span style="font-size:0.75rem;color:var(--text-muted);">${escapeHtml(e.user_email || '')}</span>`
                : escapeHtml(e.user_id || '—');
            const color    = actionColors[e.action] || 'var(--text-color)';
            const resource = [e.resource_type, e.resource_id].filter(Boolean).join(' / ');
            return `<tr>
                <td style="padding:0.75rem;font-size:0.85rem;color:var(--text-muted);white-space:nowrap;">${ts}</td>
                <td style="padding:0.75rem;font-weight:600;color:${color};white-space:nowrap;">${escapeHtml(e.action)}</td>
                <td style="padding:0.75rem;font-size:0.85rem;">${actor}</td>
                <td style="padding:0.75rem;font-size:0.85rem;color:var(--text-muted);">${escapeHtml(resource)}</td>
            </tr>`;
        }).join('');

        if (pager) {
            const totalStr = `<span style="color:var(--text-muted);font-size:0.85rem;">${(total || 0).toLocaleString()} entries</span>`;
            const prev = currentPage > 1
                ? `<button class="btn btn-secondary" style="padding:0.3rem 0.75rem" onclick="window.tenantAdminApp.loadAuditLog(${currentPage - 1})">← Prev</button>`
                : '';
            const next = currentPage < pages
                ? `<button class="btn btn-secondary" style="padding:0.3rem 0.75rem" onclick="window.tenantAdminApp.loadAuditLog(${currentPage + 1})">Next →</button>`
                : '';
            pager.innerHTML = `${prev} ${totalStr} ${next}`;
        }
    }

    // ── Announcements ──────────────────────────────────────────────────────

    async loadAnnouncements() {
        const tbody = document.getElementById('ann-table-body');
        if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">Loading…</td></tr>';
        try {
            const res  = await authFetch(`${this.baseUrl}/announcements`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load announcements');

            const items = data.announcements || [];
            if (!tbody) return;
            if (!items.length) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No announcements yet. Create one above.</td></tr>';
                return;
            }

            const typeColor = { info: '#3b82f6', warning: '#eab308', danger: '#ef4444', success: '#10b981' };
            tbody.innerHTML = items.map(a => {
                const exp    = a.expires_at ? new Date(a.expires_at).toLocaleDateString() : 'Never';
                const color  = typeColor[a.type] || 'var(--text-color)';
                const badge  = a.is_active
                    ? '<span class="status-badge active">Active</span>'
                    : '<span class="status-badge disabled">Inactive</span>';
                return `<tr style="border-bottom:1px solid var(--border-color);">
                    <td style="padding:1rem;font-weight:500;">${escapeHtml(a.title)}</td>
                    <td style="padding:1rem;"><span style="color:${color};font-weight:600;text-transform:capitalize;">${escapeHtml(a.type)}</span></td>
                    <td style="padding:1rem;">${badge}</td>
                    <td style="padding:1rem;color:var(--text-muted);font-size:0.9rem;">${exp}</td>
                    <td style="padding:1rem;text-align:right;">
                        <div class="icon-btn-row" style="justify-content:flex-end;">
                            <button class="btn btn-sm btn-secondary"
                                onclick="window.tenantAdminApp.toggleAnnouncement('${escapeHtml(a.id)}', ${!a.is_active})">
                                ${a.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                            <button class="btn btn-sm btn-danger"
                                onclick="window.tenantAdminApp.deleteAnnouncement('${escapeHtml(a.id)}')">
                                Delete
                            </button>
                        </div>
                    </td>
                </tr>`;
            }).join('');
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:var(--color-danger,#ef4444);text-align:center;padding:1rem;">${escapeHtml(err.message)}</td></tr>`;
        }
    }

    async createAnnouncement() {
        const title   = (document.getElementById('ann-title')?.value   || '').trim();
        const message = (document.getElementById('ann-message')?.value || '').trim();
        const type    = document.getElementById('ann-type')?.value  || 'info';
        const expires = document.getElementById('ann-expires')?.value || null;
        const rolesEl = document.getElementById('ann-roles');
        const roles   = rolesEl ? Array.from(rolesEl.selectedOptions).map(o => o.value) : [];

        if (!title || !message) { showError('Title and message are required.'); return; }

        try {
            const res  = await authFetch(`${this.baseUrl}/announcements`, {
                method: 'POST',
                body: JSON.stringify({ title, type, message, target_roles: roles, expires_at: expires || null })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to create announcement');
            showSuccess('Announcement posted.');
            // Clear form fields
            ['ann-title', 'ann-message', 'ann-expires'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            if (rolesEl) Array.from(rolesEl.options).forEach(o => o.selected = false);
            this.loadAnnouncements();
        } catch (err) {
            showError(err.message);
        }
    }

    async toggleAnnouncement(id, active) {
        try {
            const res  = await authFetch(`${this.baseUrl}/announcements/${id}`, {
                method: 'PATCH',
                body: JSON.stringify({ is_active: active })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Update failed');
            this.loadAnnouncements();
        } catch (err) {
            showError(err.message);
        }
    }

    async deleteAnnouncement(id) {
        if (!confirm('Delete this announcement? This cannot be undone.')) return;
        try {
            const res  = await authFetch(`${this.baseUrl}/announcements/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Delete failed');
            showSuccess('Announcement deleted.');
            this.loadAnnouncements();
        } catch (err) {
            showError(err.message);
        }
    }
}

// Initialize on DOM ready
window.tenantAdminApp = null;
document.addEventListener('DOMContentLoaded', () => {
    window.tenantAdminApp = new TenantAdminDashboard();
});
