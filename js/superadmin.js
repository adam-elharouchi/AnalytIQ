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
        const links = document.querySelectorAll('.admin-nav-link');
        const sections = document.querySelectorAll('.admin-section');

        links.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();

                // Active states
                links.forEach(l => l.classList.remove('active'));
                e.currentTarget.classList.add('active');

                // Show section
                const targetId = e.currentTarget.getAttribute('data-target');
                sections.forEach(s => {
                    s.style.display = s.id === targetId ? 'block' : 'none';
                });

                // Lazy-load data for sections that need it
                switch (targetId) {
                    case 'analytics-section':      this.loadAnalytics(); break;
                    case 'classes-admin-section':  this.loadAllClasses(); break;
                    case 'announcements-section':  this.loadAnnouncements(); break;
                    case 'platform-settings-section': this.loadPlatformSettings(); break;
                    case 'audit-section':          this.loadAuditLog(1); break;
                    case 'approvals-section':      this.loadPendingApprovals(true); break;
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
            const card = document.createElement('div');
            card.style.background = 'var(--bg-card)';
            card.style.border = '1px solid var(--border-color)';
            card.style.borderRadius = '0.75rem';
            card.style.padding = '1.5rem';
            card.style.display = 'flex';
            card.style.flexDirection = 'column';
            card.style.gap = '1.25rem';
            card.style.transition = 'transform 0.2s, box-shadow 0.2s';
            card.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';

            // Hover effect
            card.addEventListener('mouseenter', () => { card.style.transform = 'translateY(-2px)'; card.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)'; });
            card.addEventListener('mouseleave', () => { card.style.transform = 'translateY(0)'; card.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)'; });

            const badgeClass = t.is_active ? 'status-badge active' : 'status-badge disabled';
            const badgeText = t.is_active ? 'Active' : 'Disabled';

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="display: flex; gap: 1rem; align-items: center;">
                        <div style="width: 48px; height: 48px; border-radius: 0.5rem; background: var(--bg-dark); display: flex; align-items: center; justify-content: center; font-size: 1.5rem; border: 1px solid var(--border-color);">
                            🏢
                        </div>
                        <div>
                            <h3 style="margin: 0 0 0.25rem 0; font-size: 1.1rem; color: var(--text-color);">${escapeHtml(t.name)}</h3>
                            <span class="${badgeClass}" style="display: inline-block;">${badgeText}</span>
                        </div>
                    </div>
                </div>
                
                <div style="background: rgba(255, 255, 255, 0.02); padding: 1rem; border-radius: 0.5rem; border: 1px solid var(--border-color); font-size: 0.875rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; align-items: center;">
                        <span style="color: var(--text-muted);">LTI Issuer</span>
                        <span style="color: var(--primary-color); font-family: monospace; background: rgba(59, 130, 246, 0.1); padding: 2px 6px; border-radius: 4px;" title="${escapeHtml(t.lti_issuer)}">${escapeHtml(t.lti_issuer).length > 25 ? escapeHtml(t.lti_issuer).substring(0, 25) + '...' : escapeHtml(t.lti_issuer)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="color: var(--text-muted);">Total Users</span>
                        <span style="font-weight: 600; color: var(--text-color);">${t.total_users}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: var(--text-muted);">Total Classes</span>
                        <span style="font-weight: 600; color: var(--text-color);">${t.total_classes || 0}</span>
                    </div>
                </div>

                <div style="display: flex; gap: 0.75rem; margin-top: auto; padding-top: 0.5rem; flex-wrap:wrap;">
                    <button class="btn btn-sm ${t.is_active ? 'btn-danger' : 'btn-success'}" style="flex: 1; padding: 0.5rem;" onclick="window.adminApp.toggleTenantStatus('${t.tenant_id}', ${!t.is_active})">
                        ${t.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button class="btn btn-sm btn-secondary" style="flex: 1; padding: 0.5rem; display: flex; justify-content: center; align-items: center; gap: 0.25rem;" onclick="document.getElementById('user-search-input').value = ''; window.adminApp.loadUsers(1, '${t.tenant_id}'); document.querySelector('[data-target=users-section]').click();">
                        <span>👥</span> Users
                    </button>
                    <button class="btn btn-sm btn-danger" style="padding: 0.5rem 0.75rem;" onclick="window.adminApp.deleteTenant('${t.tenant_id}', '${escapeHtml(t.name).replace(/'/g,"\\'")}')">
                        🗑 Delete
                    </button>
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
                ? '<span style="background: #eab308; color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold;">Super Admin</span>'
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
                <td style="padding: 1rem;">
                    <div style="display:flex;gap:0.4rem;justify-content:flex-end;flex-wrap:wrap;">
                        ${!u.is_super_admin ? `<button class="btn btn-sm btn-primary" style="background:linear-gradient(135deg,#10b981,#059669);border:none;" onclick="window.adminApp.impersonateUser('${u.user_id}')" title="Impersonate">🎭</button>` : ''}
                        <button class="btn btn-sm btn-secondary" onclick="window.adminApp.changeUserRole('${u.user_id}','${escapeHtml(u.role)}')" title="Change Role">👤 Role</button>
                        <button class="btn btn-sm ${u.account_status === 'disabled' ? 'btn-success' : 'btn-secondary'}" onclick="window.adminApp.toggleUserStatus('${u.user_id}','${u.account_status === 'disabled' ? 'active' : 'disabled'}')" title="${u.account_status === 'disabled' ? 'Enable' : 'Disable'}">
                            ${u.account_status === 'disabled' ? '✅' : '⏸'}
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="window.adminApp.forcePasswordReset('${u.user_id}','${safeName}')" title="Force password reset">🔑</button>
                        <button class="btn btn-sm btn-secondary" onclick="window.adminApp.exportUserData('${u.user_id}')" title="Export data">⬇️</button>
                        <button class="btn btn-sm btn-danger" onclick="window.adminApp.deleteUser('${u.user_id}','${safeName}')" title="Delete user">🗑</button>
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
            const badgeClass = t.status === 'new' ? 'status-badge active' : 'status-badge role';

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

    showCreateTenantModal() {
        // For MVP, a prompt is functional. A real modal is better for production.
        const name = prompt("Enter Tenant/Institution Name:");
        if (!name) return;
        const issuer = prompt("Enter LTI Issuer URL (e.g. https://canvas.instructure.com) or leave blank for local:");

        if (name) {
            this.createTenant(name, issuer || `local-${Date.now()}`);
        }
    }

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
                        dest = (payload.role === 'professor') ? '/professor-dashboard.html' : '/student-classes.html';
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
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:#ef4444;text-align:center;">${err.message}</td></tr>`;
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
            if (!res.ok) return;
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
                            style="background:#10b981;color:#fff;border:none;"
                            onclick="window.adminApp.approveAdmin('${u.user_id}', '${escapeHtml(u.name)}')">
                            ✅ Approve
                        </button>
                        <button class="btn btn-sm btn-danger"
                            onclick="window.adminApp.denyAdmin('${u.user_id}', '${escapeHtml(u.name)}')">
                            ✗ Deny
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
        const roles = ['student', 'professor', 'superadmin'];
        const roleLabels = { student: 'Student', professor: 'Professor', superadmin: 'Super Admin' };
        const options = roles.map(r => `${r === currentRole ? '● ' : '○ '}${roleLabels[r]}`).join('\n');
        const input = prompt(`Select new role for user:\n\n${options}\n\nType role name (student / professor / superadmin):`);
        if (!input) return;
        const newRole = input.trim().toLowerCase();
        if (!roles.includes(newRole)) { showError('Invalid role. Must be student, professor, or superadmin.'); return; }
        if (newRole === currentRole) { showError('User already has that role.'); return; }
        try {
            const res = await authFetch(`${this.baseAdminUrl}/users/${userId}/role`, {
                method: 'PATCH',
                body: JSON.stringify({ role: newRole })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Role update failed');
            showSuccess(data.message || `Role updated to ${newRole}.`);
            this.loadUsers();
        } catch (err) {
            showError(err.message);
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
            a.click();
            URL.revokeObjectURL(url);
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
                const safeName = escapeHtml(c.class_name).replace(/'/g, "\\'");
                return `<tr style="border-bottom:1px solid var(--border-color);">
                    <td style="padding:1rem;">
                        <div style="font-weight:500;">${escapeHtml(c.class_name)}</div>
                        <div style="font-size:0.8rem;color:var(--text-muted);">${escapeHtml(c.class_id)}</div>
                    </td>
                    <td style="padding:1rem;">
                        <div>${escapeHtml(c.professor_name || '—')}</div>
                        <div style="font-size:0.8rem;color:var(--text-muted);">${escapeHtml(c.professor_email || '')}</div>
                    </td>
                    <td style="padding:1rem;text-align:center;">${c.student_count || 0}</td>
                    <td style="padding:1rem;text-align:center;">${c.chapter_count || 0}</td>
                    <td style="padding:1rem;text-align:right;display:flex;gap:0.4rem;justify-content:flex-end;">
                        <button class="btn btn-sm btn-secondary" onclick="window.adminApp.transferClass('${c.class_id}','${safeName}')">🔄 Transfer</button>
                        <button class="btn btn-sm btn-danger" onclick="window.adminApp.deleteClass('${c.class_id}','${safeName}')">🗑 Delete</button>
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
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:#ef4444;text-align:center;">${err.message}</td></tr>`;
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
            set('an-total-users',  data.total_users);
            set('an-new-7d',       data.new_users_7d);
            set('an-new-30d',      data.new_users_30d);
            set('an-active-7d',    data.active_users_7d);
            set('an-active-30d',   data.active_users_30d);
            set('an-classes',      data.total_classes);
            set('an-chapters',     data.total_chapters);
            set('an-exercises',    data.total_exercises);
            set('an-completions',  data.total_completions);

            // Role breakdown
            const rolesEl = document.getElementById('an-roles');
            if (rolesEl && data.roles_breakdown) {
                const total = Object.values(data.roles_breakdown).reduce((a, b) => a + b, 0) || 1;
                rolesEl.innerHTML = Object.entries(data.roles_breakdown).map(([role, count]) => {
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
                            <div style="width:${pct}%;height:100%;background:#10b981;border-radius:4px;"></div>
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
                        <button class="btn btn-sm btn-secondary" onclick="window.adminApp.toggleAnnouncement('${a.announcement_id}',${!a.is_active})">${a.is_active ? 'Deactivate' : 'Activate'}</button>
                        <button class="btn btn-sm btn-danger" onclick="window.adminApp.deleteAnnouncement('${a.announcement_id}')">🗑</button>
                    </td>
                </tr>`;
            }).join('');
        } catch (err) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:#ef4444;text-align:center;">${err.message}</td></tr>`;
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

            const items = data.blocklist || [];
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
            if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color:#ef4444;text-align:center;">${err.message}</td></tr>`;
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
