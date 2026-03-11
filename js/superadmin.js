/**
 * Super Admin Dashboard Logic
 * Handles global metrics, tenant management, and user operations across all of AnalytIQ.
 */

class SuperAdminDashboard {
    constructor() {
        const _base = window.API_BASE_URL || '/api';
        // Handle absolute or relative paths gracefully for production
        this.baseAdminUrl = _base.startsWith('http')
            ? `${_base}/superadmin`
            : `${window.location.protocol}//${window.location.host}${_base}/superadmin`;
        this._auditPage = 1;
        this._maintenanceActive = false;
        this.init();
    }

    async init() {
        // Enforce Super Admin status before showing anything
        if (!this.verifyAccess()) return;

        this.setupNavigation();
        this.setupEventListeners();

        // Load initial data
        await this.loadTenants(); // Loads stats and populates the tenants table
        await this.loadUsers();   // Loads the first page of global users
        await this.loadSupportTickets(); // Loads contact forms
        await this.loadPendingApprovals(false); // Silently refresh badge count

        // Open requested tab from landing page routing
        const targetTab = sessionStorage.getItem('sa_tab');
        if (targetTab) {
            const tabLink = document.querySelector(`[data-target="${targetTab}-section"]`);
            if (tabLink) tabLink.click();
            sessionStorage.removeItem('sa_tab');
        }
    }

    verifyAccess() {
        let currentUser = null;
        try {
            currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        } catch (e) {
            console.error("Failed to parse currentUser:", e);
        }

        const role = currentUser.role || localStorage.getItem('user_role');
        const token = localStorage.getItem('authToken');

        if (!token) {
            window.location.href = '/login.html';
            return false;
        }

        if (role !== 'superadmin') {
            console.warn("Access denied: User role is", role);
            window.location.href = '/';
            return false;
        }

        return true;
    }

    setupNavigation() {
        // Support both old .admin-nav-link and new .terminal-tab-btn
        const links = document.querySelectorAll('.admin-nav-link, .terminal-tab-btn');
        const sections = document.querySelectorAll('.admin-section');

        links.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();

                // Active states — update whichever group the clicked element belongs to
                links.forEach(l => l.classList.remove('active'));
                e.currentTarget.classList.add('active');

                // Show section
                const targetId = e.currentTarget.getAttribute('data-target');
                if (!targetId) return;
                sections.forEach(s => {
                    s.style.display = s.id === targetId ? 'block' : 'none';
                });

                // Lazy-load data for sections that need it
                switch (targetId) {
                    case 'analytics-section':         this.loadAnalytics(); break;
                    case 'classes-admin-section':     this.loadAllClasses(); break;
                    case 'announcements-section':     this.loadAnnouncements(); break;
                    case 'platform-settings-section': this.loadPlatformSettings(); break;
                    case 'audit-section':             this.loadAuditLog(1); break;
                    case 'approvals-section':         this.loadPendingApprovals(true); break;
                }
            });
        });
    }

    setupEventListeners() {

        const userSearchInput = document.getElementById('user-search-input');
        if (userSearchInput) {
            userSearchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.loadUsers(1);
                }
            });
        }
    }

    // ==========================================
    // API & Data Fetching
    // ==========================================

    async loadTenants() {
        try {
            const res = await authFetch(`${this.baseAdminUrl}/tenants`);
            if (res.ok) {
                const data = await res.json();
                if (data && data.tenants) {
                    this.renderTenants(data.tenants);
                    this.updateOverviewStats(data.tenants);
                }
            }
        } catch (error) {
            console.error("Failed to load tenants:", error);
            showError("Failed to load tenant data.");
        }
    }

    viewTenantUsers(tenantId, tenantName) {
        this._activeUserTenantFilter = tenantId || null;
        this._activeUserTenantName  = tenantName || null;
        document.getElementById('user-search-input').value = '';
        document.getElementById('user-filter-role').value  = '';
        document.getElementById('user-filter-status').value = '';
        document.querySelector('[data-target=users-section]')?.click();
        this.loadUsers(1);
    }

    _clearTenantUserFilter() {
        this._activeUserTenantFilter = null;
        this._activeUserTenantName   = null;
        document.getElementById('user-search-input').value  = '';
        document.getElementById('user-filter-role').value   = '';
        document.getElementById('user-filter-status').value = '';
        this.loadUsers(1);
    }

    _updateTenantFilterBadge() {
        const badge = document.getElementById('user-tenant-filter-badge');
        const label = document.getElementById('user-tenant-filter-name');
        if (!badge) return;
        if (this._activeUserTenantFilter) {
            if (label) label.textContent = this._activeUserTenantName || this._activeUserTenantFilter;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }

    async loadUsers(page = 1) {
        try {
            const searchInput = document.getElementById('user-search-input');
            const roleFilter = document.getElementById('user-filter-role');
            const statusFilter = document.getElementById('user-filter-status');

            const query = searchInput ? searchInput.value : '';
            const role = roleFilter ? roleFilter.value : '';
            const status = statusFilter ? statusFilter.value : '';

            const url = new URL(`${this.baseAdminUrl}/users`, window.location.origin);
            url.searchParams.append('page', page);
            url.searchParams.append('limit', 50);
            if (query) url.searchParams.append('q', query);
            if (role) url.searchParams.append('role', role);
            if (status) url.searchParams.append('status', status);
            if (this._activeUserTenantFilter) url.searchParams.append('tenant_id', this._activeUserTenantFilter);
            this._updateTenantFilterBadge();

            const res = await authFetch(url.toString());
            if (res.ok) {
                const data = await res.json();
                if (data && data.users) {
                    if (data.role_distribution) {
                        const distr = data.role_distribution;
                        if (document.getElementById('dist-superadmin')) document.getElementById('dist-superadmin').textContent = distr.superadmin || 0;
                        if (document.getElementById('dist-professor')) document.getElementById('dist-professor').textContent = distr.professor || 0;
                        if (document.getElementById('dist-student')) document.getElementById('dist-student').textContent = distr.student || 0;
                    }
                    this.renderUsers(data.users, data.current_page, data.pages);
                }
            }
        } catch (error) {
            console.error("Failed to load users:", error);
            showError("Failed to load global users.");
        }
    }

    async loadSupportTickets(page = 1) {
        try {
            const res = await authFetch(`${this.baseAdminUrl}/contact-submissions?page=${page}&limit=50`);
            if (res.ok) {
                const data = await res.json();
                if (data && data.submissions) {
                    this.renderSupportTickets(data.submissions);
                }
            }
        } catch (error) {
            console.error("Failed to load support tickets:", error);
            showError("Failed to load contact submissions.");
        }
    }

    // ==========================================
    // Rendering
    // ==========================================

    updateOverviewStats(tenants) {
        let totalUsers = 0;
        let totalClasses = 0;

        tenants.forEach(t => {
            totalUsers += t.total_users;
            totalClasses += t.total_classes;
        });

        document.getElementById('stat-total-tenants').textContent = tenants.length;
        document.getElementById('stat-total-users').textContent = totalUsers;
        document.getElementById('stat-total-classes').textContent = totalClasses;

        // Populate header health status panel
        this.refreshHeaderHealth();
    }

    // Update both health panels (header Node Health + overview System Status) using /api/health
    async refreshHeaderHealth() {
        const setService = (key, status) => {
            const healthy = status === true || status === 'ok' || status === 'healthy' || status === 'connected';
            const cls = `system-status-item-dot ${healthy ? 'healthy' : 'down'}`;
            const txt = healthy ? 'operational' : 'degraded';
            // Header panel
            const hDot = document.getElementById(`health-dot-${key}`);
            const hVal = document.getElementById(`health-val-${key}`);
            if (hDot) hDot.className = cls;
            if (hVal) { hVal.className = `system-status-item-value ${healthy ? '' : 'down'}`; hVal.textContent = txt; }
            // Overview panel
            const oDot = document.getElementById(`overview-dot-${key}`);
            const oVal = document.getElementById(`overview-val-${key}`);
            if (oDot) oDot.className = cls;
            if (oVal) { oVal.className = `system-status-item-value ${healthy ? '' : 'down'}`; oVal.textContent = txt; }
        };

        try {
            const res = await authFetch('/api/health/detail');
            // Parse regardless of status — services may be degraded but data still present
            const data = await res.json();

            const svc = data.services || {};
            // database returns {status: "healthy"/"unhealthy"}
            // cache/storage return {healthy: bool} — use the boolean directly
            setService('postgres', svc.database?.status);
            setService('redis', svc.cache?.healthy);
            setService('storage', svc.storage?.healthy);

            const ts = document.getElementById('overview-health-timestamp');
            if (ts) ts.textContent = `Last check: ${new Date().toLocaleTimeString()}`;
        } catch (_e) {
            ['postgres', 'redis', 'storage'].forEach(key => {
                ['health-val-', 'overview-val-'].forEach(prefix => {
                    const el = document.getElementById(`${prefix}${key}`);
                    if (el) el.textContent = 'unknown';
                });
            });
        }
    }

    renderTenants(tenants) {
        const grid = document.getElementById('tenants-grid');
        if (!grid) return;

        grid.innerHTML = '';

        if (tenants.length === 0) {
            grid.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 2rem; grid-column: 1 / -1; background: var(--bg-card); border-radius: 0.75rem; border: 1px solid var(--border-color);">No tenants found.</div>';
            return;
        }

        tenants.forEach(t => {
            const isActive = t.is_active;
            const issuer = escapeHtml(t.lti_issuer || 'local');
            const issuerShort = issuer.length > 30 ? issuer.substring(0, 30) + '…' : issuer;
            const safeName = escapeHtml(t.name).replace(/'/g, "\\'");
            const statusDot = isActive
                ? 'background: var(--color-success); box-shadow: 0 0 6px rgba(34,197,94,0.6);'
                : 'background: #64748b;';

            const card = document.createElement('div');
            card.className = 'class-card bento-card neon-hover';
            card.style.cssText = 'display: flex; flex-direction: column; overflow: hidden; padding: 0; cursor: pointer;';
            card.addEventListener('click', (e) => {
                if (e.target.closest('button')) return; // let button clicks bubble normally
                window.adminApp.openTenantDetail(t.tenant_id, 'details');
            });

            card.innerHTML = `
                <!-- IDE-style tab header -->
                <div style="background: rgba(0,0,0,0.25); padding: 0.6rem 1.1rem; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;">
                    <div style="display: flex; align-items: center; gap: 0.5rem; font-family: var(--font-mono); font-size: 0.72rem; color: #64748b;">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6M9 12h6M9 15h4"/>
                        </svg>
                        ${escapeHtml(t.tenant_id)}.org
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.6rem;">
                        <span style="font-family: var(--font-mono); font-size: 0.65rem; color: ${isActive ? 'rgba(34,197,94,0.8)' : '#64748b'}; background: ${isActive ? 'rgba(34,197,94,0.08)' : 'rgba(100,116,139,0.1)'}; border: 1px solid ${isActive ? 'rgba(34,197,94,0.25)' : 'rgba(100,116,139,0.2)'}; padding: 0.1rem 0.4rem; border-radius: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">${isActive ? 'ACTIVE' : 'DISABLED'}</span>
                        <div style="width: 8px; height: 8px; border-radius: 50%; ${statusDot}"></div>
                    </div>
                </div>

                <!-- Body -->
                <div style="padding: 1.25rem 1.5rem; flex: 1; display: flex; flex-direction: column; gap: 1rem;">
                    <h3 style="margin: 0; font-size: 1.1rem; color: #f8fafc; font-weight: 700; line-height: 1.2;">${escapeHtml(t.name)}</h3>

                    <!-- Stats row -->
                    <div style="display: flex; border: 1px solid rgba(255,255,255,0.06); border-radius: 0.5rem; overflow: hidden; background: rgba(0,0,0,0.15);">
                        <div style="flex: 1; text-align: center; padding: 0.7rem 0.5rem; border-right: 1px solid rgba(255,255,255,0.06);">
                            <div style="font-size: 1.3rem; font-family: var(--font-mono); color: #f8fafc; font-weight: 700; line-height: 1;">${t.total_users || 0}</div>
                            <div style="font-size: 0.62rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.2rem;">Users</div>
                        </div>
                        <div style="flex: 1; text-align: center; padding: 0.7rem 0.5rem;">
                            <div style="font-size: 1.3rem; font-family: var(--font-mono); color: #f8fafc; font-weight: 700; line-height: 1;">${t.total_classes || 0}</div>
                            <div style="font-size: 0.62rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.2rem;">Classes</div>
                        </div>
                    </div>

                    <!-- LTI issuer pill -->
                    <div style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.78rem;">
                        <span style="color: #64748b; flex-shrink: 0;">LTI</span>
                        <span style="font-family: var(--font-mono); font-size: 0.75rem; color: rgba(99,102,241,0.9); background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.2); padding: 0.15rem 0.55rem; border-radius: 0.3rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${issuer}">${issuerShort}</span>
                    </div>

                    <!-- Actions -->
                    <div style="display: flex; gap: 0.5rem; margin-top: auto; padding-top: 0.25rem; border-top: 1px solid rgba(255,255,255,0.05);">
                        <button class="btn btn-primary" style="flex: 1; font-size: 0.82rem; display: flex; align-items: center; justify-content: center; gap: 0.35rem;"
                            onclick="window.adminApp.viewTenantUsers('${t.tenant_id}', '${safeName}')">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events:none;"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                            Users
                        </button>
                        <button class="btn btn-secondary" style="font-size: 0.82rem; padding: 0.5rem 0.75rem; background: transparent; border-color: rgba(255,255,255,0.1); color: #94a3b8;"
                            onclick="window.adminApp.openTenantDetail('${t.tenant_id}', 'details')"
                            title="Edit tenant">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events:none;"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        </button>
                        <button class="btn btn-secondary" style="font-size: 0.82rem; padding: 0.5rem 0.75rem; background: transparent; border-color: rgba(255,255,255,0.1); color: #94a3b8;"
                            onclick="window.adminApp.toggleTenantStatus('${t.tenant_id}', ${!isActive})"
                            title="${isActive ? 'Disable tenant' : 'Enable tenant'}">
                            ${isActive
                                ? '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events:none;"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>'
                                : '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events:none;"><polyline points="20 6 9 17 4 12"/></svg>'
                            }
                        </button>
                        <button class="btn btn-secondary" style="font-size: 0.82rem; padding: 0.5rem 0.75rem; background: transparent; border-color: rgba(239,68,68,0.25); color: rgba(239,68,68,0.7);"
                            onclick="window.adminApp.deleteTenant('${t.tenant_id}', '${safeName}')"
                            title="Delete tenant">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events:none;"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                        </button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    renderUsers(users, currentPage, totalPages) {
        const tbody = document.getElementById('users-table-body');
        tbody.innerHTML = '';

        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="padding: 1rem; text-align: center;">No users found.</td></tr>';
            return;
        }

        users.forEach(u => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid var(--border-color)';

            // Format Role
            const roleBadge = u.is_super_admin
                ? '<span style="background: rgba(234,179,8,0.15); border: 1px solid rgba(234,179,8,0.4); color: #fcd34d; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold;">Super Admin</span>'
                : `<span style="background: var(--bg-dark); border: 1px solid var(--border-color); color: var(--text-color); padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; text-transform: capitalize;">${escapeHtml(u.role)}</span>`;

            // Format Status
            let statusColor = 'var(--text-color)';
            if (u.account_status === 'disabled') statusColor = 'var(--error-color)';
            if (u.account_status === 'flagged') statusColor = '#eab308';

            const safeName = escapeHtml(u.name).replace(/'/g, "\\'");
            tr.innerHTML = `
                <td style="padding: 1rem;">
                    <div style="font-weight: 500;">${escapeHtml(u.name)}</div>
                    <div style="font-size: 0.85rem; color: var(--text-muted);">${escapeHtml(u.email)}</div>
                </td>
                <td style="padding: 1rem;">${roleBadge}</td>
                <td style="padding: 1rem; font-size: 0.9rem; color: var(--text-muted);">${escapeHtml(u.tenant_name || 'None')}</td>
                <td style="padding: 1rem; text-transform: capitalize; color: ${statusColor}; font-weight: 500;">
                    <span class="${u.account_status === 'disabled' ? 'status-badge disabled' : 'status-badge active'}">${escapeHtml(u.account_status)}</span>
                </td>
                <td style="padding: 0.75rem 1rem;">
                    <div class="icon-btn-row">
                        ${!u.is_super_admin ? `
                        <button class="icon-btn icon-btn-green" title="Impersonate" onclick="window.adminApp.impersonateUser('${u.user_id}')">
                            <svg viewBox="0 0 24 24"><path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/></svg>
                        </button>` : ''}
                        <button class="icon-btn" title="Change Role" onclick="window.adminApp.changeUserRole('${u.user_id}','${escapeHtml(u.role)}')">
                            <svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                        </button>
                        <button class="icon-btn ${u.account_status === 'disabled' ? 'icon-btn-success' : 'icon-btn-amber'}" title="${u.account_status === 'disabled' ? 'Enable' : 'Disable'}" onclick="window.adminApp.toggleUserStatus('${u.user_id}','${u.account_status === 'disabled' ? 'active' : 'disabled'}')">
                            ${u.account_status === 'disabled'
                                ? `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="10 8 16 12 10 16 10 8"/></svg>`
                                : `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="10" y1="15" x2="10" y2="9"/><line x1="14" y1="15" x2="14" y2="9"/></svg>`}
                        </button>
                        <button class="icon-btn" title="Reset Password" onclick="window.adminApp.forcePasswordReset('${u.user_id}','${safeName}')">
                            <svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                        </button>
                        <button class="icon-btn" title="Export Data" onclick="window.adminApp.exportUserData('${u.user_id}')">
                            <svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        </button>
                        <button class="icon-btn icon-btn-danger" title="Delete User" onclick="window.adminApp.deleteUser('${u.user_id}','${safeName}')">
                            <svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Simple Pagination
        const paginator = document.getElementById('users-pagination');
        if (paginator) {
            paginator.innerHTML = `
                <button class="btn btn-secondary" ${currentPage <= 1 ? 'disabled' : ''} onclick="window.adminApp.loadUsers(${currentPage - 1})">Previous</button>
                <span style="display: flex; align-items: center; padding: 0 1rem;">Page ${currentPage} of ${totalPages}</span>
                <button class="btn btn-secondary" ${currentPage >= totalPages ? 'disabled' : ''} onclick="window.adminApp.loadUsers(${currentPage + 1})">Next</button>
            `;
        }
    }

    renderSupportTickets(tickets) {
        const tbody = document.getElementById('support-table-body');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (tickets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="padding: 1rem; text-align: center;">No support tickets found.</td></tr>';
            return;
        }

        tickets.forEach(t => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid var(--border-color)';

            const date = new Date(t.created_at).toLocaleDateString();

            tr.innerHTML = `
                <td style="padding: 1rem; font-weight: 500;">
                    ${escapeHtml(t.name)}
                    ${t.user_id ? '<span style="font-size: 0.75rem; background: var(--bg-dark); padding: 1px 4px; border-radius: 4px; margin-left: 0.5rem; color: var(--text-muted);">Registered</span>' : ''}
                </td>
                <td style="padding: 1rem; color: var(--text-muted); font-size: 0.9rem;">${escapeHtml(t.email)}</td>
                <td style="padding: 1rem;"><div style="font-weight: 500; margin-bottom: 0.25rem;">${escapeHtml(t.subject)}</div><div style="font-size: 0.85rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 300px;">${escapeHtml(t.message)}</div></td>
                <td style="padding: 1rem; color: var(--text-muted);">${date}</td>
                <td style="padding: 1rem; text-align: right;">
                    <select onchange="window.adminApp.updateTicketStatus('${t.id}', this.value)"
                        style="padding:0.3rem 0.5rem;border:1px solid var(--border-color);border-radius:0.375rem;background:var(--bg-card);color:var(--text-color);font-size:0.85rem;cursor:pointer;">
                        ${['new','read','resolved','archived'].map(s =>
                            `<option value="${s}" ${(t.status||'new')===s ? 'selected' : ''}>${s}</option>`
                        ).join('')}
                    </select>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    // ==========================================
    // Actions Server Mutators
    // ==========================================

    async toggleTenantStatus(tenantId, activate) {
        if (!confirm(`Are you sure you want to ${activate ? 'enable' : 'disable'} this tenant?`)) return;

        try {
            const res = await authFetch(`${this.baseAdminUrl}/tenants/${tenantId}`, {
                method: 'PATCH',
                body: JSON.stringify({ is_active: activate })
            });
            if (res.ok) {
                showSuccess(`Tenant ${activate ? 'enabled' : 'disabled'} successfully`);
                this.loadTenants(); // Reload table
            } else {
                const err = await res.json();
                showError(err.error || "Failed to update tenant status");
            }
        } catch (error) {
            console.error("Failed to toggle tenant:", error);
            showError(error.message || "Failed to update tenant status");
        }
    }

    // Keep legacy alias for any remaining inline calls
    editTenant(tenantId, currentName, currentIssuer) {
        this.openTenantDetail(tenantId, 'details', currentName, currentIssuer);
    }

    openTenantDetail(tenantId, tab = 'details', preloadName = null, preloadIssuer = null) {
        document.getElementById('editTenantId').value = tenantId;
        // Populate header
        const titleEl    = document.getElementById('tenantDetailTitle');
        const subtitleEl = document.getElementById('tenantDetailSubtitle');
        if (titleEl)    titleEl.textContent    = preloadName || 'Tenant Details';
        if (subtitleEl) subtitleEl.textContent = `${tenantId}.org`;
        // Pre-fill details tab if we have the values
        if (preloadName !== null)   document.getElementById('editTenantName').value   = preloadName;
        if (preloadIssuer !== null) document.getElementById('editTenantIssuer').value = preloadIssuer === 'local' ? '' : preloadIssuer;
        // Switch to the requested tab
        this._switchTenantTab(tab);
        // Show modal
        document.getElementById('tenantDetailModal').style.display = 'flex';
        // If opening SSO tab, load providers
        if (tab === 'sso') this._loadTenantSSOProviders(tenantId);
    }

    _switchTenantTab(tab) {
        ['details', 'sso'].forEach(t => {
            const btn   = document.getElementById(`tdTab-${t}`);
            const panel = document.getElementById(`tdPanel-${t}`);
            const active = t === tab;
            if (btn) {
                btn.style.borderBottom = active ? '2px solid var(--color-primary,#2569f4)' : '2px solid transparent';
                btn.style.color        = active ? 'var(--text-primary,#f0f4ff)' : '#64748b';
                btn.style.fontWeight   = active ? '600' : '500';
            }
            if (panel) panel.style.display = active ? 'block' : 'none';
        });
        // Lazy-load SSO list when switching to that tab
        if (tab === 'sso') {
            const tenantId = document.getElementById('editTenantId')?.value;
            if (tenantId) this._loadTenantSSOProviders(tenantId);
        }
    }

    async submitEditTenant() {
        const tenantId = document.getElementById('editTenantId').value;
        const name = (document.getElementById('editTenantName').value || '').trim();
        const issuer = (document.getElementById('editTenantIssuer').value || '').trim();

        if (!name) { showError('Institution name is required'); return; }

        try {
            const res = await authFetch(`${this.baseAdminUrl}/tenants/${tenantId}`, {
                method: 'PATCH',
                body: JSON.stringify({ name, lti_issuer: issuer || null })
            });
            if (res.ok) {
                showSuccess('Tenant updated successfully');
                document.getElementById('tenantDetailModal').style.display = 'none';
                this.loadTenants();
            } else {
                const err = await res.json();
                showError(err.error || 'Failed to update tenant');
            }
        } catch (error) {
            showError(error.message || 'Failed to update tenant');
        }
    }

    // -----------------------------------------------------------------------
    // SSO Provider Management (within Tenant Detail)
    // -----------------------------------------------------------------------

    async _loadTenantSSOProviders(tenantId) {
        const container = document.getElementById('td-sso-providers-list');
        if (!container) return;
        container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:2rem;">Loading…</div>';
        const ssoBase = this.baseAdminUrl.replace('/superadmin', '/sso/admin');
        try {
            const res  = await authFetch(`${ssoBase}/providers?tenant_id=${encodeURIComponent(tenantId)}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load SSO providers');
            this._renderTenantSSOProviders(data.providers || []);
        } catch (err) {
            container.innerHTML = `<div style="color:#fca5a5;text-align:center;padding:1.5rem;">${escapeHtml(err.message)}</div>`;
        }
    }

    _renderTenantSSOProviders(providers) {
        const container = document.getElementById('td-sso-providers-list');
        if (!container) return;
        if (!providers.length) {
            container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:2.5rem;border:1px dashed rgba(255,255,255,0.08);border-radius:0.5rem;">No SSO providers configured yet. Click "Add Provider" to get started.</div>';
            return;
        }
        container.innerHTML = providers.map(p => {
            const typeBadge   = `<span style="background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.25);color:#a5b4fc;padding:1px 7px;border-radius:4px;font-size:0.78rem;text-transform:capitalize;">${escapeHtml(p.provider_type)}</span>`;
            const statusBadge = p.is_enabled
                ? '<span style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.25);color:#86efac;padding:1px 7px;border-radius:4px;font-size:0.78rem;">Enabled</span>'
                : '<span style="background:rgba(100,116,139,0.1);border:1px solid rgba(100,116,139,0.2);color:#64748b;padding:1px 7px;border-radius:4px;font-size:0.78rem;">Disabled</span>';
            const domains = (p.allowed_domains || []).length
                ? escapeHtml(p.allowed_domains.join(', '))
                : '<span style="color:#475569;">all domains</span>';
            return `
            <div style="background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.07);border-radius:0.5rem;padding:1rem 1.1rem;margin-bottom:0.75rem;">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.75rem;">
                <div style="min-width:0;">
                  <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.4rem;">
                    <span style="font-weight:600;color:#f0f4ff;font-size:0.95rem;">${escapeHtml(p.provider_name)}</span>
                    ${typeBadge} ${statusBadge}
                  </div>
                  <div style="font-size:0.8rem;color:#64748b;">Domains: ${domains}</div>
                  ${p.discovery_url ? `<div style="font-size:0.78rem;color:#475569;font-family:var(--font-mono);margin-top:0.2rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(p.discovery_url)}">${escapeHtml(p.discovery_url.length > 55 ? p.discovery_url.substring(0,55)+'…' : p.discovery_url)}</div>` : ''}
                </div>
                <div style="display:flex;gap:0.4rem;flex-shrink:0;">
                  <button onclick="window.adminApp.openTenantSSOForm('${p.provider_id}')"
                    style="padding:0.4rem 0.75rem;border:1px solid rgba(255,255,255,0.1);border-radius:0.35rem;background:transparent;color:#94a3b8;cursor:pointer;font-size:0.8rem;">Edit</button>
                  <button onclick="window.adminApp.deleteTenantSSOProvider('${p.provider_id}','${escapeHtml(p.provider_name).replace(/'/g,"\\'")}','${document.getElementById('editTenantId').value}')"
                    style="padding:0.4rem 0.75rem;border:1px solid rgba(239,68,68,0.25);border-radius:0.35rem;background:transparent;color:rgba(239,68,68,0.7);cursor:pointer;font-size:0.8rem;">Delete</button>
                </div>
              </div>
            </div>`;
        }).join('');
    }

    async openTenantSSOForm(providerId = null) {
        // Reset form
        document.getElementById('tdSsoProviderId').value    = '';
        document.getElementById('tdSsoName').value          = '';
        document.getElementById('tdSsoType').value          = 'google';
        document.getElementById('tdSsoDefaultRole').value   = 'student';
        document.getElementById('tdSsoClientId').value      = '';
        document.getElementById('tdSsoClientSecret').value  = '';
        document.getElementById('tdSsoDiscovery').value     = '';
        document.getElementById('tdSsoDomains').value       = '';
        document.getElementById('tdSsoError').style.display = 'none';
        document.getElementById('tdSsoSecretOptNote').style.display = 'none';
        document.getElementById('tenantSSOModalTitle').textContent  = providerId ? 'Edit SSO Provider' : 'Add SSO Provider';
        this._tdSsoOnTypeChange();

        if (providerId) {
            document.getElementById('tdSsoSecretOptNote').style.display = '';
            document.getElementById('tenantSSOModal').style.display = 'flex';
            const ssoBase = this.baseAdminUrl.replace('/superadmin', '/sso/admin');
            try {
                const res  = await authFetch(`${ssoBase}/providers/${providerId}`);
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Failed to load provider');
                const p = data.provider || data;
                document.getElementById('tdSsoProviderId').value   = p.provider_id || providerId;
                document.getElementById('tdSsoName').value         = p.provider_name || '';
                document.getElementById('tdSsoType').value         = p.provider_type || 'oidc';
                document.getElementById('tdSsoDefaultRole').value  = p.default_role || 'student';
                document.getElementById('tdSsoClientId').value     = p.client_id || '';
                document.getElementById('tdSsoDiscovery').value    = p.discovery_url || '';
                document.getElementById('tdSsoDomains').value      = (p.allowed_domains || []).join(', ');
                this._tdSsoOnTypeChange();
            } catch (err) {
                document.getElementById('tdSsoError').textContent     = err.message;
                document.getElementById('tdSsoError').style.display   = 'block';
            }
        } else {
            document.getElementById('tenantSSOModal').style.display = 'flex';
        }
    }

    _tdSsoOnTypeChange() {
        const type = document.getElementById('tdSsoType')?.value;
        const row  = document.getElementById('tdSsoDiscoveryRow');
        if (row) row.style.display = type === 'oidc' ? 'block' : 'none';
    }

    closeTenantSSOForm() {
        document.getElementById('tenantSSOModal').style.display = 'none';
    }

    async saveTenantSSOProvider() {
        const errEl       = document.getElementById('tdSsoError');
        errEl.style.display = 'none';

        const providerId    = document.getElementById('tdSsoProviderId').value.trim();
        const providerName  = document.getElementById('tdSsoName').value.trim();
        const providerType  = document.getElementById('tdSsoType').value;
        const defaultRole   = document.getElementById('tdSsoDefaultRole').value;
        const clientId      = document.getElementById('tdSsoClientId').value.trim();
        const clientSecret  = document.getElementById('tdSsoClientSecret').value;
        const discoveryUrl  = document.getElementById('tdSsoDiscovery').value.trim();
        const domainsRaw    = document.getElementById('tdSsoDomains').value;
        const tenantId      = document.getElementById('editTenantId').value;

        if (!providerName) { errEl.textContent = 'Provider name is required.'; errEl.style.display = 'block'; return; }
        if (!clientId)     { errEl.textContent = 'Client ID is required.'; errEl.style.display = 'block'; return; }
        if (providerType === 'oidc' && !discoveryUrl) { errEl.textContent = 'Discovery URL is required for Generic OIDC.'; errEl.style.display = 'block'; return; }
        if (!providerId && !clientSecret) { errEl.textContent = 'Client secret is required for new providers.'; errEl.style.display = 'block'; return; }

        const body = {
            tenant_id:     tenantId,
            provider_name: providerName,
            provider_type: providerType,
            client_id:     clientId,
            discovery_url: discoveryUrl,
            allowed_domains: domainsRaw.split(',').map(d => d.trim()).filter(Boolean),
            default_role:  defaultRole,
        };
        if (clientSecret) body.client_secret = clientSecret;

        const ssoBase = this.baseAdminUrl.replace('/superadmin', '/sso/admin');
        try {
            const res = await authFetch(
                providerId ? `${ssoBase}/providers/${providerId}` : `${ssoBase}/providers`,
                { method: providerId ? 'PUT' : 'POST', body: JSON.stringify(body) }
            );
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to save provider');
            showSuccess(data.message || 'SSO provider saved.');
            this.closeTenantSSOForm();
            this._loadTenantSSOProviders(tenantId);
        } catch (err) {
            errEl.textContent   = err.message;
            errEl.style.display = 'block';
        }
    }

    async deleteTenantSSOProvider(providerId, providerName, tenantId) {
        if (!confirm(`Delete SSO provider "${providerName}"?\n\nUsers who sign in via this provider will lose their SSO link.`)) return;
        const ssoBase = this.baseAdminUrl.replace('/superadmin', '/sso/admin');
        try {
            const res  = await authFetch(`${ssoBase}/providers/${providerId}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Delete failed');
            showSuccess(data.message || 'Provider deleted.');
            this._loadTenantSSOProviders(tenantId);
        } catch (err) { showError(err.message); }
    }

    async toggleUserStatus(userId, newStatus) {
        const actionText = newStatus === 'active' ? 'enable' : 'disable';
        if (!confirm(`Are you sure you want to ${actionText} this user's account?`)) return;

        try {
            const res = await authFetch(`${this.baseAdminUrl}/users/${userId}/status`, {
                method: 'PATCH',
                body: JSON.stringify({ account_status: newStatus })
            });
            if (res.ok) {
                showSuccess(`User account ${actionText}d successfully`);
                this.loadUsers(); // Reload table (staying on same page requires tracking current page, omitted for brevity, reload from 1 is fine or track globally)
            } else {
                const err = await res.json();
                showError(err.error || `Failed to update user status`);
            }
        } catch (error) {
            console.error(`Failed to ${actionText} user:`, error);
            showError(error.message || `Failed to update user status`);
        }
    }

    // -----------------------------------------------------------------------
    // New Tenant Setup Wizard
    // -----------------------------------------------------------------------

    showTenantWizard() {
        this._wz = { step: 1 };
        const ids = ['wzInstitutionName','wzPlatformName','wzIssuer','wzClientId',
                     'wzDeploymentIds','wzAuthLoginUrl','wzAuthTokenUrl','wzKeySetUrl',
                     'wzSsoName','wzSsoClientId','wzSsoSecret','wzSsoDiscovery','wzSsoDomains'];
        ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
        ['wzLtiEnable','wzSsoEnable'].forEach(id => {
            const el = document.getElementById(id); if (el) el.checked = false;
        });
        const roleEl = document.getElementById('wzSsoDefaultRole');
        if (roleEl) roleEl.value = 'student';
        const typeEl = document.getElementById('wzSsoType');
        if (typeEl) typeEl.value = 'google';
        this._wzToggleLti(false);
        this._wzToggleSso(false);
        this._wzGoTo(1);
        document.getElementById('tenantWizardModal').style.display = 'flex';
        setTimeout(() => document.getElementById('wzInstitutionName')?.focus(), 50);
    }

    _wzGoTo(step) {
        this._wz.step = step;
        ['1','2','3','done'].forEach(s => {
            const el = document.getElementById(`wz-step-${s}`);
            if (el) el.style.display = (s == step) ? 'block' : 'none';
        });
        const isDone = step === 'done';
        [1,2,3].forEach(s => {
            const ind = document.getElementById(`wz-ind-${s}`);
            const lbl = document.getElementById(`wz-lbl-${s}`);
            if (!ind) return;
            const past = !isDone && s < step;
            const active = !isDone && s === step;
            ind.style.background = past ? 'var(--color-success,#22c55e)' : active ? 'var(--color-primary,#2569f4)' : 'rgba(255,255,255,0.05)';
            ind.style.borderColor = past ? 'var(--color-success,#22c55e)' : active ? 'var(--color-primary,#2569f4)' : 'rgba(255,255,255,0.2)';
            ind.style.color = (past || active) ? '#fff' : '#64748b';
            ind.innerHTML = past ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>' : s;
            if (lbl) lbl.style.color = active ? 'var(--text-primary,#f0f4ff)' : past ? 'var(--color-success,#22c55e)' : '#64748b';
        });
        const footer = document.getElementById('wz-step-footer');
        if (footer) footer.style.display = isDone ? 'none' : 'flex';
        const back = document.getElementById('wz-btn-back');
        if (back) back.style.display = (!isDone && step > 1) ? 'inline-block' : 'none';
        const skip = document.getElementById('wz-btn-skip');
        if (skip) skip.style.display = (!isDone && (step === 2 || step === 3)) ? 'inline-block' : 'none';
        const next = document.getElementById('wz-btn-next');
        if (next) next.style.display = (!isDone && step < 3) ? 'inline-block' : 'none';
        const finish = document.getElementById('wz-btn-finish');
        if (finish) finish.style.display = (!isDone && step === 3) ? 'inline-block' : 'none';
    }

    _wzToggleLti(show) {
        const el = document.getElementById('wz-lti-fields');
        if (el) el.style.display = show ? 'block' : 'none';
    }

    _wzToggleSso(show) {
        const el = document.getElementById('wz-sso-fields');
        if (el) el.style.display = show ? 'block' : 'none';
        this._wzOnSsoTypeChange();
    }

    _wzOnSsoTypeChange() {
        const type = document.getElementById('wzSsoType')?.value;
        const row = document.getElementById('wz-sso-discovery-row');
        if (row) row.style.display = type === 'oidc' ? 'block' : 'none';
    }

    wzNext() {
        if (this._wz.step === 1) {
            const name = (document.getElementById('wzInstitutionName')?.value || '').trim();
            if (!name) { showError('Institution name is required.'); return; }
            this._wzGoTo(2);
        } else if (this._wz.step === 2) {
            this._wzGoTo(3);
        }
    }

    wzSkip() {
        if (this._wz.step === 2) {
            document.getElementById('wzLtiEnable').checked = false;
            this._wzToggleLti(false);
            this._wzGoTo(3);
        } else if (this._wz.step === 3) {
            document.getElementById('wzSsoEnable').checked = false;
            this._wzToggleSso(false);
            this.wzFinish();
        }
    }

    wzBack() {
        if (this._wz.step > 1) this._wzGoTo(this._wz.step - 1);
    }

    async wzFinish() {
        const name = (document.getElementById('wzInstitutionName')?.value || '').trim();
        const ltiEnabled = document.getElementById('wzLtiEnable')?.checked;
        const ssoEnabled = document.getElementById('wzSsoEnable')?.checked;

        const ltiIssuer = ltiEnabled ? (document.getElementById('wzIssuer')?.value || '').trim() : '';

        // Validate LTI fields if enabled
        if (ltiEnabled) {
            const required = { 'Platform Name': 'wzPlatformName', 'Issuer URL': 'wzIssuer',
                               'Client ID': 'wzClientId', 'Auth Login URL': 'wzAuthLoginUrl',
                               'Auth Token URL': 'wzAuthTokenUrl', 'Key Set URL': 'wzKeySetUrl' };
            for (const [label, id] of Object.entries(required)) {
                if (!(document.getElementById(id)?.value || '').trim()) {
                    showError(`${label} is required for LTI configuration.`);
                    this._wzGoTo(2); return;
                }
            }
        }

        // Validate SSO fields if enabled
        if (ssoEnabled) {
            const ssoRequired = { 'Provider Name': 'wzSsoName', 'Client ID': 'wzSsoClientId', 'Client Secret': 'wzSsoSecret' };
            for (const [label, id] of Object.entries(ssoRequired)) {
                if (!(document.getElementById(id)?.value || '').trim()) {
                    showError(`${label} is required for SSO configuration.`);
                    this._wzGoTo(3); return;
                }
            }
            if (document.getElementById('wzSsoType')?.value === 'oidc') {
                if (!(document.getElementById('wzSsoDiscovery')?.value || '').trim()) {
                    showError('Discovery URL is required for Generic OIDC providers.');
                    this._wzGoTo(3); return;
                }
            }
        }

        const finishBtn = document.getElementById('wz-btn-finish');
        if (finishBtn) { finishBtn.disabled = true; finishBtn.textContent = 'Creating…'; }

        const summaryLines = [];
        try {
            // 1. Create tenant
            const tenantRes = await authFetch(`${this.baseAdminUrl}/tenants`, {
                method: 'POST',
                body: JSON.stringify({ name, lti_issuer: ltiIssuer || `local-${Date.now()}` })
            });
            if (!tenantRes.ok) {
                const err = await tenantRes.json();
                throw new Error(err.error || 'Failed to create tenant');
            }
            const tenantData = await tenantRes.json();
            const tenantId = tenantData.tenant_id;
            summaryLines.push(`✓ Tenant <strong>${escapeHtml(name)}</strong> created`);

            // 2. LTI config
            if (ltiEnabled) {
                const deployRaw = (document.getElementById('wzDeploymentIds')?.value || '').trim();
                const deployIds = deployRaw ? deployRaw.split(',').map(s => s.trim()).filter(Boolean) : [];
                const ltiRes = await authFetch('/api/lti/config', {
                    method: 'POST',
                    body: JSON.stringify({
                        platform_name: document.getElementById('wzPlatformName').value.trim(),
                        issuer: document.getElementById('wzIssuer').value.trim(),
                        client_id: document.getElementById('wzClientId').value.trim(),
                        auth_login_url: document.getElementById('wzAuthLoginUrl').value.trim(),
                        auth_token_url: document.getElementById('wzAuthTokenUrl').value.trim(),
                        key_set_url: document.getElementById('wzKeySetUrl').value.trim(),
                        deployment_ids: deployIds,
                    })
                });
                if (ltiRes.ok) {
                    summaryLines.push(`✓ LTI platform <strong>${escapeHtml(document.getElementById('wzPlatformName').value.trim())}</strong> registered`);
                } else {
                    const e = await ltiRes.json();
                    summaryLines.push(`⚠ LTI config failed: ${escapeHtml(e.error || 'unknown error')}`);
                }
            }

            // 3. SSO provider
            if (ssoEnabled) {
                const ssoType = document.getElementById('wzSsoType').value;
                const domainsRaw = (document.getElementById('wzSsoDomains')?.value || '').trim();
                const domains = domainsRaw ? domainsRaw.split(',').map(s => s.trim()).filter(Boolean) : [];
                const ssoPayload = {
                    tenant_id: tenantId,
                    provider_name: document.getElementById('wzSsoName').value.trim(),
                    provider_type: ssoType,
                    client_id: document.getElementById('wzSsoClientId').value.trim(),
                    client_secret: document.getElementById('wzSsoSecret').value.trim(),
                    discovery_url: ssoType === 'oidc' ? document.getElementById('wzSsoDiscovery').value.trim() : '',
                    allowed_domains: domains,
                    default_role: document.getElementById('wzSsoDefaultRole').value,
                };
                const ssoRes = await authFetch('/api/sso/admin/providers', {
                    method: 'POST',
                    body: JSON.stringify(ssoPayload)
                });
                if (ssoRes.ok) {
                    summaryLines.push(`✓ SSO provider <strong>${escapeHtml(document.getElementById('wzSsoName').value.trim())}</strong> configured`);
                } else {
                    const e = await ssoRes.json();
                    summaryLines.push(`⚠ SSO setup failed: ${escapeHtml(e.error || 'unknown error')}`);
                }
            }

            document.getElementById('wz-done-summary').innerHTML = summaryLines.join('<br>');
            this._wzGoTo('done');
            this.loadTenants();

        } catch (err) {
            showError(err.message || 'Setup failed. Please try again.');
        } finally {
            if (finishBtn) { finishBtn.disabled = false; finishBtn.textContent = 'Finish'; }
        }
    }

    // kept for backward compatibility (e.g. Change Role modal new-tenant flow)
    async createTenant(name, issuer) {
        try {
            const res = await authFetch(`${this.baseAdminUrl}/tenants`, {
                method: 'POST',
                body: JSON.stringify({ name: name, lti_issuer: issuer })
            });
            if (res.ok) {
                showSuccess("Tenant created successfully");
                this.loadTenants();
            } else {
                const err = await res.json();
                showError(err.error || "Failed to create tenant");
            }
        } catch (error) {
            console.error("Failed to create tenant:", error);
            showError(error.message || "Failed to create tenant");
        }
    }

    // ==========================================
    // Impersonation Engine
    // ==========================================

    async impersonateUser(userId) {
        if (!confirm("You are about to impersonate this user's session. All actions will be logged. Continue?")) return;

        try {
            const res = await authFetch(`${this.baseAdminUrl}/users/${userId}/impersonate`, {
                method: 'POST'
            });

            if (res.ok) {
                const data = await res.json();
                if (data && data.token) {
                    // Cache original superadmin credentials so the floating bar can restore them.
                    if (!localStorage.getItem('original_token')) {
                        localStorage.setItem('original_token', localStorage.getItem('authToken'));
                        localStorage.setItem('original_user', localStorage.getItem('currentUser'));
                    }

                    // Swap to the impersonated user's token.
                    localStorage.setItem('authToken', data.token);

                    // Decode payload to determine the destination page.
                    let dest = '/student-classes.html';
                    try {
                        const payload = JSON.parse(
                            atob(data.token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))
                        );
                        const targetUserObj = {
                            user_id: payload.user_id,
                            name:    payload.name,
                            email:   payload.email,
                            role:    payload.role
                        };
                        localStorage.setItem('currentUser', JSON.stringify(targetUserObj));
                        const roleDestMap = {
                            professor:    '/professor-dashboard.html',
                            tenant_admin: '/tenant-admin-dashboard.html',
                            superadmin:   '/superadmin-dashboard.html',
                        };
                        dest = roleDestMap[payload.role] || '/student-classes.html';
                    } catch (e) { console.error("JWT decode failed:", e); }

                    // Record when the session started so the floating bar can enforce
                    // the 60-minute TTL across page navigations.
                    localStorage.setItem('impersonation_started_at', Date.now().toString());

                    // Navigate the current window to the target user's dashboard.
                    window.location.href = dest;
                }
            } else {
                const err = await res.json();
                showError(err.error || "Impersonation failed");
            }
        } catch (error) {
            console.error("Impersonation failed:", error);
            showError(error.message || "Failed to initiate impersonation context.");
        }
    }

    // ==========================================
    // Audit Log
    // ==========================================

    async loadAuditLog(page = 1) {
        this._auditPage = page;
        const action = document.getElementById('audit-action-filter')?.value || '';
        const resource = document.getElementById('audit-resource-filter')?.value || '';
        const from = document.getElementById('audit-from')?.value || '';
        const to = document.getElementById('audit-to')?.value || '';

        const tbody = document.getElementById('audit-table-body');
        if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">Loading…</td></tr>';

        try {
            const params = new URLSearchParams({ page, limit: 50 });
            if (action) params.set('action', action);
            if (resource) params.set('resource_type', resource);
            if (from) params.set('from', from);
            if (to) params.set('to', to);

            const res = await authFetch(`${this.baseAdminUrl}/audit?${params}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load audit log');
            this.renderAuditLog(data.entries || [], data.total, data.pages, page);
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:var(--color-danger, #ef4444);text-align:center;">${err.message}</td></tr>`;
        }
    }

    renderAuditLog(entries, total, pages, currentPage) {
        const tbody = document.getElementById('audit-table-body');
        const pager = document.getElementById('audit-pagination');
        if (!tbody) return;

        if (!entries.length) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No audit entries found.</td></tr>';
            if (pager) pager.innerHTML = '';
            return;
        }

        const actionColors = {
            IMPERSONATE_USER: '#f59e0b', DISABLE_USER: '#ef4444', ENABLE_USER: '#10b981',
            DELETE_USER: '#ef4444', DELETE_CLASS: '#ef4444', DELETE_CHAPTER: '#ef4444',
        };

        tbody.innerHTML = entries.map(e => {
            const ts = e.created_at ? new Date(e.created_at).toLocaleString() : '—';
            const actor = e.actor_name ? `${escapeHtml(e.actor_name)}<br><span style="font-size:0.75rem;color:var(--text-muted)">${escapeHtml(e.actor_email || '')}</span>` : escapeHtml(e.actor_id || '—');
            const color = actionColors[e.action] || 'var(--text-color)';
            const resource = [e.resource_type, e.resource_id].filter(Boolean).join(' / ');
            return `<tr>
              <td style="padding:0.75rem;font-size:0.85rem;color:var(--text-muted);white-space:nowrap;">${ts}</td>
              <td style="padding:0.75rem;font-weight:600;color:${color};white-space:nowrap;">${escapeHtml(e.action)}</td>
              <td style="padding:0.75rem;font-size:0.85rem;">${actor}</td>
              <td style="padding:0.75rem;font-size:0.85rem;color:var(--text-muted);">${escapeHtml(resource)}</td>
              <td style="padding:0.75rem;font-size:0.8rem;color:var(--text-muted);">${escapeHtml(e.ip_address || '—')}</td>
            </tr>`;
        }).join('');

        // Pagination
        if (pager) {
            const totalStr = `<span style="color:var(--text-muted);font-size:0.85rem;">${total.toLocaleString()} entries</span>`;
            const prev = currentPage > 1
                ? `<button class="btn btn-secondary" style="padding:0.3rem 0.75rem" onclick="window.adminApp.loadAuditLog(${currentPage - 1})">← Prev</button>`
                : '';
            const next = currentPage < pages
                ? `<button class="btn btn-secondary" style="padding:0.3rem 0.75rem" onclick="window.adminApp.loadAuditLog(${currentPage + 1})">Next →</button>`
                : '';
            pager.innerHTML = `${prev} ${totalStr} ${next}`;
        }
    }

    // ==========================================
    // Support Ticket Status Update
    // ==========================================

    async updateTicketStatus(submissionId, status) {
        try {
            const res = await authFetch(
                `${this.baseAdminUrl}/contact-submissions/${submissionId}`,
                { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) }
            );
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Update failed');
            await this.loadSupportTickets();
            showSuccess(`Ticket marked as ${status}.`);
        } catch (err) {
            showError(err.message);
        }
    }

    closeImpersonationModal() {
        // Impersonation now runs in the main window (no iframe modal).
        // Delegate to the global exit function defined in base.html.
        if (typeof window._exitImpersonation === 'function') {
            window._exitImpersonation();
        }
    }

    // ==========================================
    // Pending Admin Approvals
    // ==========================================

    /**
     * Load pending approvals.
     * @param {boolean} renderTable – if true, update the approvals table;
     *                                if false, only refresh the badge/stat counter.
     */
    async loadPendingApprovals(renderTable = true) {
        try {
            const res = await authFetch(`${this.baseAdminUrl}/pending-approvals`);
            if (!res.ok) {
                if (renderTable) showError('Failed to load pending approvals. Please refresh.');
                return;
            }
            const data = await res.json();

            const count = data.count || 0;

            // Always update the badge and stat counter
            const badge = document.getElementById('approvals-badge');
            const stat  = document.getElementById('stat-pending-approvals');
            if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'inline' : 'none'; }
            if (stat)  stat.textContent = count;

            if (!renderTable) return;

            const tbody    = document.getElementById('approvals-table-body');
            const empty    = document.getElementById('approvals-empty');
            const wrapper  = document.getElementById('approvals-table-wrapper');
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
                // JSON.stringify produces a safely-quoted JS string; replace " with &quot; so
                // it doesn't terminate the surrounding HTML double-quoted attribute.
                const nameArg = JSON.stringify(u.name).replace(/"/g, '&quot;');
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
                        <button class="btn btn-sm btn-success"
                            style="background:var(--color-success, #10b981);color:#fff;border:none;"
                            onclick="window.adminApp.approveAdmin('${u.user_id}', ${nameArg})">
                            Approve
                        </button>
                        <button class="btn btn-sm btn-danger"
                            onclick="window.adminApp.denyAdmin('${u.user_id}', ${nameArg})">
                            Deny
                        </button>
                    </td>
                </tr>`;
            }).join('');
        } catch (err) {
            console.error('Failed to load pending approvals:', err);
        }
    }

    async approveAdmin(userId, name) {
        if (!confirm(`Approve account for ${name}? They will gain immediate access to the platform.`)) return;
        try {
            const res = await authFetch(`${this.baseAdminUrl}/users/${userId}/approve`, { method: 'PATCH' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Approval failed');
            showSuccess(data.message || `${name} approved successfully.`);
            this.loadPendingApprovals(true);
        } catch (err) {
            showError(err.message);
        }
    }

    async denyAdmin(userId, name) {
        if (!confirm(`Deny account for ${name}? Their account will be set to denied status.`)) return;
        try {
            const res = await authFetch(`${this.baseAdminUrl}/users/${userId}/deny`, { method: 'PATCH' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Denial failed');
            showSuccess(data.message || `${name}'s account has been denied.`);
            this.loadPendingApprovals(true);
        } catch (err) {
            showError(err.message);
        }
    }

    // ==========================================
    // Delete Actions
    // ==========================================

    async deleteUser(userId, name) {
        if (!confirm(`Permanently delete account for "${name}"?\n\nThis removes the user and all associated data. This action cannot be undone.`)) return;
        try {
            const res = await authFetch(`${this.baseAdminUrl}/users/${userId}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Delete failed');
            showSuccess(data.message || `${name} deleted.`);
            this.loadUsers();
        } catch (err) {
            showError(err.message);
        }
    }

    async deleteClass(classId, name) {
        if (!confirm(`Permanently delete class "${name}"?\n\nThis removes all chapters, exercises, and enrollments. This action cannot be undone.`)) return;
        try {
            const res = await authFetch(`${this.baseAdminUrl}/classes/${classId}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Delete failed');
            showSuccess(data.message || `Class "${name}" deleted.`);
            this.loadAllClasses();
        } catch (err) {
            showError(err.message);
        }
    }

    async deleteTenant(tenantId, name) {
        if (!confirm(`Permanently delete tenant "${name}"?\n\nUsers and classes will be detached (not deleted). This action cannot be undone.`)) return;
        try {
            const res = await authFetch(`${this.baseAdminUrl}/tenants/${tenantId}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Delete failed');
            showSuccess(data.message || `Tenant "${name}" deleted.`);
            this.loadTenants();
        } catch (err) {
            showError(err.message);
        }
    }

    // ==========================================
    // User Role & Admin Management
    // ==========================================

    async changeUserRole(userId, currentRole) {
        this._pendingRoleUserId = userId;
        document.getElementById('changeRoleTargetLabel').textContent = `Current role: ${currentRole}`;
        const sel = document.getElementById('changeRoleSelect');
        sel.value = currentRole;
        const nameInput = document.getElementById('changeRoleTenantName');
        if (nameInput) nameInput.value = '';
        // Default to "existing" mode each time the modal opens
        this._onTenantModeChange('existing');
        this._onRoleSelectChange();
        document.getElementById('changeRoleModal').style.display = 'flex';
    }

    _onRoleSelectChange() {
        const isTenantAdmin = document.getElementById('changeRoleSelect').value === 'tenant_admin';
        document.getElementById('tenantSelectSection').style.display = isTenantAdmin ? 'block' : 'none';
        if (isTenantAdmin) this._loadTenantsDropdown();
    }

    _onTenantModeChange(mode) {
        this._tenantMode = mode;
        const existingBtn = document.getElementById('tenantModeExistingBtn');
        const newBtn      = document.getElementById('tenantModeNewBtn');
        const existingSec = document.getElementById('tenantExistingSection');
        const newSec      = document.getElementById('tenantNewSection');
        if (existingBtn) {
            existingBtn.style.background = mode === 'existing' ? 'var(--color-primary,#2569f4)' : 'rgba(17,24,39,0.7)';
            existingBtn.style.color      = mode === 'existing' ? '#fff' : 'var(--text-secondary,#94a3b8)';
        }
        if (newBtn) {
            newBtn.style.background = mode === 'new' ? 'var(--color-primary,#2569f4)' : 'rgba(17,24,39,0.7)';
            newBtn.style.color      = mode === 'new' ? '#fff' : 'var(--text-secondary,#94a3b8)';
        }
        if (existingSec) existingSec.style.display = mode === 'existing' ? 'block' : 'none';
        if (newSec)      newSec.style.display      = mode === 'new'      ? 'block' : 'none';
    }

    async _loadTenantsDropdown() {
        const sel = document.getElementById('changeRoleTenantSelect');
        if (!sel) return;
        sel.innerHTML = '<option value="">Loading tenants…</option>';
        try {
            const res = await authFetch(`${this.baseAdminUrl}/tenants`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data    = await res.json();
            const tenants = data.tenants || [];
            sel.innerHTML = tenants.length
                ? '<option value="">— Select a tenant —</option>'
                  + tenants.map(t => `<option value="${t.tenant_id}">${escapeHtml(t.name)}</option>`).join('')
                : '<option value="">No tenants found</option>';
        } catch (err) {
            console.error('Failed to load tenants dropdown:', err);
            sel.innerHTML = '<option value="">Failed to load tenants</option>';
        }
    }

    async _submitRoleChange() {
        const role    = document.getElementById('changeRoleSelect').value;
        const saveBtn = document.querySelector('#changeRoleModal .btn-primary');

        try {
            let tenantId = null;

            if (role === 'tenant_admin') {
                if (this._tenantMode === 'existing') {
                    // Use the selected existing tenant
                    const sel = document.getElementById('changeRoleTenantSelect');
                    tenantId = sel ? sel.value : '';
                    if (!tenantId) { showError('Please select a tenant.'); return; }
                } else {
                    // Create a new tenant first
                    const tenantName = (document.getElementById('changeRoleTenantName').value || '').trim();
                    if (!tenantName) { showError('Please enter an institution / tenant name.'); return; }
                    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Creating tenant…'; }
                    const tRes  = await authFetch(`${this.baseAdminUrl}/tenants`, {
                        method: 'POST',
                        body: JSON.stringify({ name: tenantName })
                    });
                    const tData = await tRes.json();
                    if (!tRes.ok) throw new Error(tData.error || 'Failed to create tenant');
                    tenantId = tData.tenant.tenant_id;
                }
            }

            // Assign the role (with tenant_id if tenant_admin)
            if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Saving…'; }
            const res  = await authFetch(`${this.baseAdminUrl}/users/${this._pendingRoleUserId}/role`, {
                method: 'PATCH',
                body: JSON.stringify({ role, ...(tenantId && { tenant_id: tenantId }) })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Role update failed');
            document.getElementById('changeRoleModal').style.display = 'none';
            showSuccess(data.message || `Role updated to ${role}.`);
            this.loadUsers();
        } catch (err) {
            showError(err.message);
        } finally {
            if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Save Role'; }
        }
    }

    async forcePasswordReset(userId, name) {
        if (!confirm(`Force password reset for "${name}"?\n\nThey will be redirected to change their password on next login.`)) return;
        try {
            const res = await authFetch(`${this.baseAdminUrl}/users/${userId}/force-reset`, { method: 'POST' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Force reset failed');
            showSuccess(data.message || `Password reset flagged for ${name}.`);
        } catch (err) {
            showError(err.message);
        }
    }

    async exportUserData(userId) {
        try {
            const token = localStorage.getItem('authToken');
            const res = await fetch(`${this.baseAdminUrl}/users/${userId}/export`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) {
                const d = await res.json();
                throw new Error(d.error || 'Export failed');
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `user-export-${userId}.json`;
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(url), 100);
        } catch (err) {
            showError(err.message);
        }
    }

    // ==========================================
    // Classes Admin
    // ==========================================

    async loadAllClasses(page = 1) {
        const tbody = document.getElementById('classes-admin-table-body');
        if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">Loading…</td></tr>';

        try {
            const q = document.getElementById('class-admin-search')?.value || '';
            const params = new URLSearchParams({ page, limit: 50 });
            if (q) params.set('q', q);
            const res = await authFetch(`${this.baseAdminUrl}/classes?${params}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load classes');

            const classes = data.classes || [];
            if (!tbody) return;

            if (!classes.length) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No classes found.</td></tr>';
                return;
            }

            tbody.innerHTML = classes.map(c => {
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
                    <td style="padding:0.75rem 1rem;">
                        <div class="icon-btn-row">
                            <button class="icon-btn" title="Transfer Ownership" onclick="window.adminApp.transferClass('${c.class_id}','${safeName}')">
                                <svg viewBox="0 0 24 24"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 014-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 01-4 4H3"/></svg>
                            </button>
                            <button class="icon-btn icon-btn-danger" title="Delete Class" onclick="window.adminApp.deleteClass('${c.class_id}','${safeName}')">
                                <svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
                            </button>
                        </div>
                    </td>
                </tr>`;
            }).join('');

            // Pagination
            const pager = document.getElementById('classes-admin-pagination');
            if (pager) {
                const prev = page > 1 ? `<button class="btn btn-secondary" onclick="window.adminApp.loadAllClasses(${page-1})">← Prev</button>` : '';
                const next = page < (data.pages || 1) ? `<button class="btn btn-secondary" onclick="window.adminApp.loadAllClasses(${page+1})">Next →</button>` : '';
                const info = `<span style="display:flex;align-items:center;color:var(--text-muted);font-size:0.85rem;">Page ${page} of ${data.pages || 1} (${data.total || classes.length} classes)</span>`;
                pager.innerHTML = `${prev}${info}${next}`;
            }
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:var(--color-danger, #ef4444);text-align:center;">${err.message}</td></tr>`;
        }
    }

    async transferClass(classId, className) {
        const newProfessor = prompt(`Transfer class "${className}" to a different professor.\n\nEnter the new professor's email address:`);
        if (!newProfessor) return;
        try {
            const res = await authFetch(`${this.baseAdminUrl}/classes/${classId}/transfer`, {
                method: 'PATCH',
                body: JSON.stringify({ professor_email: newProfessor.trim() })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Transfer failed');
            showSuccess(data.message || `Class transferred successfully.`);
            this.loadAllClasses();
        } catch (err) {
            showError(err.message);
        }
    }

    // ==========================================
    // Analytics
    // ==========================================

    async loadAnalytics() {
        // Reset stat values
        ['an-total-users','an-new-7d','an-new-30d','an-active-7d','an-active-30d',
         'an-classes','an-chapters','an-exercises','an-completions'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '…';
        });

        try {
            const res = await authFetch(`${this.baseAdminUrl}/analytics`);
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

            // Role breakdown
            const rolesEl = document.getElementById('an-roles');
            if (rolesEl && data.users?.by_role) {
                const roles_breakdown = data.users.by_role;
                const total = Object.values(roles_breakdown).reduce((a, b) => a + b, 0) || 1;
                rolesEl.innerHTML = Object.entries(roles_breakdown).map(([role, count]) => {
                    const pct = Math.round((count / total) * 100);
                    return `<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
                        <span style="min-width:80px;font-size:0.85rem;text-transform:capitalize;">${role}</span>
                        <div style="flex:1;height:8px;background:var(--bg-dark);border-radius:4px;overflow:hidden;">
                            <div style="width:${pct}%;height:100%;background:var(--primary-color);border-radius:4px;"></div>
                        </div>
                        <span style="font-size:0.85rem;color:var(--text-muted);min-width:40px;text-align:right;">${count}</span>
                    </div>`;
                }).join('');
            }

            // Top actions
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
            console.error('Failed to load analytics:', err);
            showError(err.message);
        }
    }

    // ==========================================
    // Announcements
    // ==========================================

    async loadAnnouncements() {
        const tbody = document.getElementById('announcements-table-body');
        if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">Loading…</td></tr>';
        try {
            const res = await authFetch(`${this.baseAdminUrl}/announcements`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load announcements');

            const items = data.announcements || [];
            if (!tbody) return;
            if (!items.length) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No announcements yet.</td></tr>';
                return;
            }

            const typeColor = { info:'#3b82f6', warning:'#eab308', danger:'#ef4444', success:'#10b981' };
            tbody.innerHTML = items.map(a => {
                const exp = a.expires_at ? new Date(a.expires_at).toLocaleDateString() : 'Never';
                const color = typeColor[a.type] || 'var(--text-color)';
                const activeBadge = a.is_active
                    ? '<span class="status-badge active">Active</span>'
                    : '<span class="status-badge disabled">Inactive</span>';
                return `<tr style="border-bottom:1px solid var(--border-color);">
                    <td style="padding:1rem;font-weight:500;">${escapeHtml(a.title)}</td>
                    <td style="padding:1rem;"><span style="color:${color};font-weight:600;text-transform:capitalize;">${escapeHtml(a.type)}</span></td>
                    <td style="padding:1rem;">${activeBadge}</td>
                    <td style="padding:1rem;color:var(--text-muted);font-size:0.9rem;">${exp}</td>
                    <td style="padding:1rem;text-align:right;display:flex;gap:0.4rem;justify-content:flex-end;">
                        <button class="btn btn-sm btn-secondary" onclick="window.adminApp.toggleAnnouncement('${a.id}',${!a.is_active})">${a.is_active ? 'Deactivate' : 'Activate'}</button>
                        <button class="btn btn-sm btn-danger" onclick="window.adminApp.deleteAnnouncement('${a.id}')">Delete</button>
                    </td>
                </tr>`;
            }).join('');
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:var(--color-danger, #ef4444);text-align:center;">${err.message}</td></tr>`;
        }
    }

    async createAnnouncement() {
        const title   = document.getElementById('ann-title')?.value.trim();
        const type    = document.getElementById('ann-type')?.value || 'info';
        const message = document.getElementById('ann-message')?.value.trim();
        const expires = document.getElementById('ann-expires')?.value || null;
        const rolesEl = document.getElementById('ann-roles');
        const roles   = rolesEl ? Array.from(rolesEl.selectedOptions).map(o => o.value) : [];

        if (!title || !message) { showError('Title and message are required.'); return; }

        try {
            const res = await authFetch(`${this.baseAdminUrl}/announcements`, {
                method: 'POST',
                body: JSON.stringify({ title, type, message, target_roles: roles, expires_at: expires || null })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to create announcement');
            showSuccess('Announcement posted.');
            // Clear form
            ['ann-title','ann-message','ann-expires'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            if (rolesEl) Array.from(rolesEl.options).forEach(o => o.selected = false);
            this.loadAnnouncements();
        } catch (err) {
            showError(err.message);
        }
    }

    async toggleAnnouncement(id, active) {
        try {
            const res = await authFetch(`${this.baseAdminUrl}/announcements/${id}`, {
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
        if (!confirm('Delete this announcement?')) return;
        try {
            const res = await authFetch(`${this.baseAdminUrl}/announcements/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Delete failed');
            showSuccess('Announcement deleted.');
            this.loadAnnouncements();
        } catch (err) {
            showError(err.message);
        }
    }

    // ==========================================
    // Platform Settings & IP Blocklist
    // ==========================================

    async loadPlatformSettings() {
        try {
            const res = await authFetch(`${this.baseAdminUrl}/platform-config`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load settings');

            this._maintenanceActive = data.maintenance_mode === 'true' || data.maintenance_mode === true;
            const badge = document.getElementById('maint-status-badge');
            const btn   = document.getElementById('maint-toggle-btn');
            if (badge) {
                badge.className = `status-badge ${this._maintenanceActive ? 'disabled' : 'active'}`;
                badge.textContent = this._maintenanceActive ? 'ON — Maintenance Active' : 'OFF — Platform Running';
            }
            if (btn) btn.textContent = this._maintenanceActive ? 'Disable Maintenance' : 'Enable Maintenance';

            const msgEl = document.getElementById('maint-message');
            if (msgEl) msgEl.value = data.maintenance_message || '';
        } catch (err) {
            showError(err.message);
        }
        this.loadIpBlocklist();
    }

    async toggleMaintenanceMode() {
        const newState = !this._maintenanceActive;
        const action = newState ? 'enable' : 'disable';
        if (!confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} maintenance mode?\n${newState ? 'All non-superadmin API requests will return 503.' : 'The platform will resume normal operation.'}`)) return;
        try {
            const res = await authFetch(`${this.baseAdminUrl}/platform-config`, {
                method: 'PATCH',
                body: JSON.stringify({ maintenance_mode: newState ? 'true' : 'false' })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Update failed');
            showSuccess(`Maintenance mode ${newState ? 'enabled' : 'disabled'}.`);
            this.loadPlatformSettings();
        } catch (err) {
            showError(err.message);
        }
    }

    async savePlatformSettings() {
        const msg = document.getElementById('maint-message')?.value.trim() || '';
        try {
            const res = await authFetch(`${this.baseAdminUrl}/platform-config`, {
                method: 'PATCH',
                body: JSON.stringify({ maintenance_message: msg })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Save failed');
            showSuccess('Maintenance message saved.');
        } catch (err) {
            showError(err.message);
        }
    }

    async loadIpBlocklist() {
        const tbody = document.getElementById('ip-blocklist-body');
        if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">Loading…</td></tr>';
        try {
            const res = await authFetch(`${this.baseAdminUrl}/ip-blocklist`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load IP blocklist');

            const items = data.blocked || [];
            if (!tbody) return;
            if (!items.length) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No blocked IPs.</td></tr>';
                return;
            }
            tbody.innerHTML = items.map(ip => {
                const date = ip.created_at ? new Date(ip.created_at).toLocaleDateString() : '—';
                return `<tr style="border-bottom:1px solid var(--border-color);">
                    <td style="padding:0.75rem;font-family:monospace;">${escapeHtml(ip.ip_address)}</td>
                    <td style="padding:0.75rem;color:var(--text-muted);">${escapeHtml(ip.reason || '—')}</td>
                    <td style="padding:0.75rem;color:var(--text-muted);">${escapeHtml(ip.blocked_by_name || ip.blocked_by || '—')}</td>
                    <td style="padding:0.75rem;color:var(--text-muted);">${date}</td>
                    <td style="padding:0.75rem;text-align:right;">
                        <button class="btn btn-sm btn-danger" onclick="window.adminApp.removeIpBlock('${ip.id}','${escapeHtml(ip.ip_address)}')">Remove</button>
                    </td>
                </tr>`;
            }).join('');
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:var(--color-danger, #ef4444);text-align:center;">${err.message}</td></tr>`;
        }
    }

    async addIpBlock() {
        const ip     = document.getElementById('ip-input')?.value.trim();
        const reason = document.getElementById('ip-reason')?.value.trim() || '';
        if (!ip) { showError('Enter an IP address to block.'); return; }
        // Basic validation
        const ipv4 = /^(\d{1,3}\.){3}\d{1,3}$/.test(ip);
        const ipv6 = ip.includes(':');
        if (!ipv4 && !ipv6) { showError('Enter a valid IPv4 or IPv6 address.'); return; }

        try {
            const res = await authFetch(`${this.baseAdminUrl}/ip-blocklist`, {
                method: 'POST',
                body: JSON.stringify({ ip_address: ip, reason })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to block IP');
            showSuccess(`IP ${ip} blocked.`);
            const ipEl = document.getElementById('ip-input');
            const reasonEl = document.getElementById('ip-reason');
            if (ipEl) ipEl.value = '';
            if (reasonEl) reasonEl.value = '';
            this.loadIpBlocklist();
        } catch (err) {
            showError(err.message);
        }
    }

    async removeIpBlock(id, ip) {
        if (!confirm(`Remove block for IP ${ip}?`)) return;
        try {
            const res = await authFetch(`${this.baseAdminUrl}/ip-blocklist/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Remove failed');
            showSuccess(`IP ${ip} unblocked.`);
            this.loadIpBlocklist();
        } catch (err) {
            showError(err.message);
        }
    }

}

// Initialize when DOM holds
window.adminApp = null;
document.addEventListener('DOMContentLoaded', () => {
    window.adminApp = new SuperAdminDashboard();
});
