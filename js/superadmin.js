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

                <div style="display: flex; gap: 0.75rem; margin-top: auto; padding-top: 0.5rem;">
                    <button class="btn btn-sm ${t.is_active ? 'btn-danger' : 'btn-success'}" style="flex: 1; padding: 0.5rem;" onclick="window.adminApp.toggleTenantStatus('${t.tenant_id}', ${!t.is_active})">
                        ${t.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button class="btn btn-sm btn-secondary" style="flex: 1; padding: 0.5rem; display: flex; justify-content: center; align-items: center; gap: 0.25rem;" onclick="document.getElementById('user-search-input').value = ''; window.adminApp.loadUsers(1, '${t.tenant_id}'); document.querySelector('[data-target=users-section]').click();">
                        <span>👥</span> Users
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
                <td style="padding: 1rem; text-align: right; display: flex; gap: 0.5rem; justify-content: flex-end;">
                    ${!u.is_super_admin ? `<button class="btn btn-sm btn-primary" style="background: linear-gradient(135deg, #10b981, #059669); border: none; box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);" onclick="window.adminApp.impersonateUser('${u.user_id}')" title="Sign in as this user">
                        <span>🎭</span> Impersonate
                    </button>` : ''}
                    <button class="btn btn-sm ${u.account_status === 'disabled' ? 'btn-success' : 'btn-danger'}" onclick="window.adminApp.toggleUserStatus('${u.user_id}', '${u.account_status === 'disabled' ? 'active' : 'disabled'}')">
                        ${u.account_status === 'disabled' ? 'Enable' : 'Disable'}
                    </button>
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
                <td style="padding: 1rem; text-align: right; text-transform: capitalize;">
                    <span class="${badgeClass}">${escapeHtml(t.status || 'new')}</span>
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
        if (!confirm("You are about to securely hijack this user's session without their password. All actions will be logged. Continue?")) return;

        try {
            const res = await authFetch(`${this.baseAdminUrl}/users/${userId}/impersonate`, {
                method: 'POST'
            });

            if (res.ok) {
                const data = await res.json();
                if (data && data.token) {
                    // Safety cache: store original super admin token
                    const currentToken = localStorage.getItem('authToken');
                    if (!localStorage.getItem('original_token')) {
                        // Only save original if we aren't already impersonating
                        localStorage.setItem('original_token', currentToken);
                    }

                    // Swap auth securely
                    localStorage.setItem('authToken', data.token);

                    // We don't have the full user profile, but we can decode the JWT to set localStorage roughly
                    try {
                        const payload = JSON.parse(atob(data.token.split('.')[1]));
                        localStorage.setItem('user_id', payload.user_id);
                        localStorage.setItem('user_role', payload.role);
                        localStorage.setItem('user', JSON.stringify({
                            name: payload.name,
                            email: payload.email,
                            role: payload.role
                        }));
                    } catch (e) { }

                    showSuccess("Impersonation successful. Redirecting...");

                    // Redirect based on role
                    setTimeout(() => {
                        const role = localStorage.getItem('user_role');
                        if (role === 'professor') {
                            window.location.href = '/professor-dashboard.html';
                        } else if (role === 'student') {
                            window.location.href = '/student-dashboard.html';
                        } else {
                            window.location.href = '/';
                        }
                    }, 1000);
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

}

// Initialize when DOM holds
window.adminApp = null;
document.addEventListener('DOMContentLoaded', () => {
    window.adminApp = new SuperAdminDashboard();
});
