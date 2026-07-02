// API Helper Functions
// Declare API_BASE_URL as a global variable - single source of truth.
// Use /api for same-origin. For split deployment (e.g. static site + separate API host),
// set <meta name="api-base-url" content="https://your-api-host.com/api"> so the login and API calls hit the correct server.
if (typeof window.API_BASE_URL === 'undefined') {
    const meta = typeof document !== 'undefined' && document.querySelector('meta[name="api-base-url"]');
    window.API_BASE_URL = (meta && meta.getAttribute('content')) || '/api';
}

// Simple Cache Implementation
if (typeof apiCache === 'undefined') {
    window.apiCache = {
        data: new Map(),
        // Default TTL: 5 minutes (300,000 ms)
        TTL: 300000,

        set(key, value, customTTL = null) {
            const expiresAt = Date.now() + (customTTL !== null ? customTTL : this.TTL);
            this.data.set(key, { value, expiresAt });
        },

        get(key) {
            if (!this.data.has(key)) return null;

            const item = this.data.get(key);
            if (Date.now() > item.expiresAt) {
                this.data.delete(key);
                return null;
            }
            return item.value;
        },

        clear(keyPattern) {
            if (!keyPattern) {
                this.data.clear();
                return;
            }
            // Delete keys matching pattern (string or regex)
            for (const key of this.data.keys()) {
                if (key.includes(keyPattern)) {
                    this.data.delete(key);
                }
            }
        }
    };
}

// CSRF Token Management
window._csrfToken = window._csrfToken || null;
window._csrfFetchPromise = null;

async function getCsrfToken() {
    if (window._csrfToken) return window._csrfToken;
    // Deduplicate concurrent fetches
    if (!window._csrfFetchPromise) {
        window._csrfFetchPromise = fetch('/api/csrf-token')
            .then(function(r) { return r.ok ? r.json() : null; })
            .then(function(data) {
                if (data && data.csrf_enabled && data.csrf_token) {
                    window._csrfToken = data.csrf_token;
                }
                window._csrfFetchPromise = null;
                return window._csrfToken;
            })
            .catch(function() { window._csrfFetchPromise = null; return null; });
    }
    return window._csrfFetchPromise;
}

// Get auth headers for API requests
function getAuthHeaders(extraHeaders = {}) {
    const headers = { 'Content-Type': 'application/json', ...extraHeaders };
    const token = localStorage.getItem('authToken');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

// Single in-flight refresh so a burst of 401s triggers only one /refresh call.
window._refreshPromise = window._refreshPromise || null;

async function refreshAccessToken() {
    if (window._refreshPromise) return window._refreshPromise;
    const rt = localStorage.getItem('refreshToken');
    if (!rt) return false;
    window._refreshPromise = fetch(window.API_BASE_URL + '/users/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt })
    }).then(async function (r) {
        if (!r.ok) return false;
        const data = await r.json();
        if (data.token) localStorage.setItem('authToken', data.token);
        if (data.refresh_token) localStorage.setItem('refreshToken', data.refresh_token);
        return !!data.token;
    }).catch(function () { return false; })
      .finally(function () { window._refreshPromise = null; });
    return window._refreshPromise;
}

// Authenticated fetch wrapper - adds JWT token + CSRF, and on a 401 transparently
// refreshes the access token once and retries the request.
async function authFetch(url, options = {}, _retried) {
    options.headers = options.headers || {};
    // Always set Content-Type for non-FormData requests (including unauthenticated ones like sign-in)
    if (!(options.body instanceof FormData)) {
        options.headers['Content-Type'] = options.headers['Content-Type'] || 'application/json';
    }
    const token = localStorage.getItem('authToken');
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    // Attach CSRF token for state-changing requests
    const method = (options.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        const csrfToken = await getCsrfToken();
        if (csrfToken) {
            options.headers['X-CSRFToken'] = csrfToken;
        }
    }
    const resp = await fetch(url, options);
    // Transparent refresh: on the first 401, try to mint a new access token and
    // retry once. Skip the auth endpoints themselves to avoid loops.
    if (resp.status === 401 && !_retried
        && url.indexOf('/users/refresh') === -1
        && url.indexOf('/users/signin') === -1
        && url.indexOf('/users/signup') === -1) {
        const ok = await refreshAccessToken();
        if (ok) {
            return authFetch(url, options, true);
        }
    }
    return resp;
}

// Fetch with Cache Wrapper
async function fetchWithCache(url, options = {}) {
    // Only cache GET requests
    if (options.method && options.method !== 'GET') {
        return authFetch(url, options);
    }

    const cacheKey = url;
    const cachedResponse = window.apiCache.get(cacheKey);

    if (cachedResponse) {
        return new Response(JSON.stringify(cachedResponse), { status: 200, statusText: 'OK (Cached)' });
    }

    try {
        const response = await authFetch(url, options);
        if (response.ok) {
            // Clone response to read it and cache it, while returning original to caller
            const clone = response.clone();
            const data = await clone.json();
            window.apiCache.set(cacheKey, data);
        }
        return response;
    } catch (error) {
        throw error;
    }
}

// Get current user ID from localStorage
function getCurrentUserId() {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    return currentUser.id;
}

// Get full current user object
function getCurrentUser() {
    try {
        const userStr = localStorage.getItem('currentUser');
        return userStr ? JSON.parse(userStr) : null;
    } catch (e) {
        return null;
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Get difficulty color
function getDifficultyColor(difficulty) {
    const diff = (difficulty || 'medium').toLowerCase();
    if (diff === 'easy') return '#10b981';
    if (diff === 'hard') return '#ef4444';
    return 'var(--color-primary)'; // medium
}

// Global UI Feedback Helpers
function showError(message) {
    if (typeof window.uiStates !== 'undefined' && window.uiStates.showConfirmModal) {
        // Use custom modal if available
        console.error("UI Error:", message);
        alert("Error: " + message);
    } else {
        alert("Error: " + message);
    }
}

function showSuccess(message) {
    console.log("UI Success:", message);
    alert("Success: " + message);
}

// Conversation API functions
if (typeof window.conversationAPI === 'undefined') {
    window.conversationAPI = {
        async getAll(archived = false) {
            if (!getCurrentUserId()) return [];

            try {
                const url = `${window.API_BASE_URL}/users/conversations?archived=${archived}`;
                const response = await fetchWithCache(url);
                if (response.ok) {
                    const data = await response.json();
                    return Array.isArray(data) ? data : (data.conversations || []);
                }
            } catch (error) {
                console.error('Error fetching conversations:', error);
            }
            return [];
        },

        async get(conversationId) {
            if (!getCurrentUserId()) return null;

            try {
                const url = `${window.API_BASE_URL}/users/conversations/${conversationId}`;
                const response = await fetchWithCache(url);
                if (response.ok) {
                    return await response.json();
                }
            } catch (error) {
                console.error('Error fetching conversation:', error);
            }
            return null;
        },

        async create(conversationId, title) {
            if (!getCurrentUserId()) return null;

            try {
                const response = await authFetch(`${window.API_BASE_URL}/users/conversations`, {
                    method: 'POST',
                    body: JSON.stringify({
                        conversation_id: conversationId,
                        title: title
                    })
                });
                if (response.ok) {
                    // Invalidate conversations cache
                    apiCache.clear('/users/conversations');
                    const data = await response.json();
                    return data.conversation_id;
                }
            } catch (error) {
                console.error('Error creating conversation:', error);
            }
            return null;
        },

        async update(conversationId, data) {
            if (!getCurrentUserId()) return false;

            try {
                const response = await authFetch(`${window.API_BASE_URL}/users/conversations/${conversationId}`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
                // Invalidate specific conversation and list
                apiCache.clear(`/users/conversations/${conversationId}`);
                apiCache.clear('/users/conversations');
                return response.ok;
            } catch (error) {
                console.error('Error updating conversation:', error);
            }
            return false;
        },

        async delete(conversationId) {
            if (!getCurrentUserId()) return false;

            try {
                const response = await authFetch(`${window.API_BASE_URL}/users/conversations/${conversationId}`, {
                    method: 'DELETE'
                });
                // Invalidate specific conversation and list
                apiCache.clear(`/users/conversations/${conversationId}`);
                apiCache.clear('/users/conversations');
                return response.ok;
            } catch (error) {
                console.error('Error deleting conversation:', error);
            }
            return false;
        },

        async appendMessage(conversationId, role, content) {
            if (!getCurrentUserId()) return false;

            try {
                const response = await authFetch(`${window.API_BASE_URL}/users/conversations/${conversationId}/messages`, {
                    method: 'POST',
                    body: JSON.stringify({ role, content })
                });
                // Invalidate this conversation's cache so next GET fetches fresh data
                apiCache.clear(`/users/conversations/${conversationId}`);
                return response.ok;
            } catch (error) {
                console.error('Error appending message:', error);
            }
            return false;
        }
    };
}

// AI Agent API functions
if (typeof window.aiAgentAPI === 'undefined') {
    window.aiAgentAPI = {
        async getDigest() {
            if (!getCurrentUserId()) return { goal: '', constraints: '', decisions: '', current_state: '', open_questions: '' };

            try {
                const url = `${window.API_BASE_URL}/users/ai-digest`;
                const response = await fetchWithCache(url);
                if (response.ok) {
                    return await response.json();
                }
            } catch (error) {
                console.error('Error fetching digest:', error);
            }
            return { goal: '', constraints: '', decisions: '', current_state: '', open_questions: '' };
        },

        async saveDigest(digest) {
            if (!getCurrentUserId()) return false;

            try {
                const response = await authFetch(`${window.API_BASE_URL}/users/ai-digest`, {
                    method: 'PUT',
                    body: JSON.stringify({ digest: digest })
                });
                // Invalidate digest cache
                apiCache.clear('/users/ai-digest');
                return response.ok;
            } catch (error) {
                console.error('Error saving digest:', error);
            }
            return false;
        },

        async getMemory() {
            if (!getCurrentUserId()) return [];

            try {
                const url = `${window.API_BASE_URL}/users/ai-memory`;
                const response = await fetchWithCache(url);
                if (response.ok) {
                    const data = await response.json();
                    return data.memory || [];
                }
            } catch (error) {
                console.error('Error fetching memory:', error);
            }
            return [];
        },

        async saveMemory(memory) {
            if (!getCurrentUserId()) return false;

            try {
                const response = await authFetch(`${window.API_BASE_URL}/users/ai-memory`, {
                    method: 'PUT',
                    body: JSON.stringify({ memory: memory })
                });
                // Invalidate memory cache
                apiCache.clear('/users/ai-memory');
                return response.ok;
            } catch (error) {
                console.error('Error saving memory:', error);
            }
            return false;
        }
    };
}

// Preferences API functions
if (typeof window.preferencesAPI === 'undefined') {
    window.preferencesAPI = {
        async get() {
            if (!getCurrentUserId()) return { currentLanguage: 'python', geminiModel: 'gemini-3.5-flash', aiProvider: 'gemini' };

            try {
                const url = `${window.API_BASE_URL}/users/preferences`;
                const response = await fetchWithCache(url);
                if (response.ok) {
                    return await response.json();
                }
            } catch (error) {
                console.error('Error fetching preferences:', error);
            }
            return { currentLanguage: 'python', geminiModel: 'gemini-3.5-flash', aiProvider: 'gemini' };
        },

        async update(preferences) {
            if (!getCurrentUserId()) return false;

            try {
                const response = await authFetch(`${window.API_BASE_URL}/users/preferences`, {
                    method: 'PUT',
                    body: JSON.stringify(preferences)
                });
                // Invalidate preferences cache
                apiCache.clear('/users/preferences');
                return response.ok;
            } catch (error) {
                console.error('Error updating preferences:', error);
            }
            return false;
        }
    };
}

// ---------------------------------------------------------------------------
// Capability-token interceptor for media downloads
// ---------------------------------------------------------------------------
// Resource downloads are plain <a href> links that cannot send an Authorization
// header. The backend now protects /api/resources/<id>/download with a
// short-lived capability token. Intercept clicks on those links, mint a token,
// and navigate with ?token= appended so downloads keep working for authorized
// users while remaining closed to anonymous callers.
async function fetchResourceAccessToken(resourceId) {
    try {
        const resp = await authFetch(
            `${window.API_BASE_URL}/resources/${encodeURIComponent(resourceId)}/access-token`
        );
        if (resp.ok) return (await resp.json()).token || '';
    } catch (e) { /* ignore — navigation will 401 without a token */ }
    return '';
}

if (typeof document !== 'undefined' && !window.__mediaTokenInterceptor) {
    window.__mediaTokenInterceptor = true;
    document.addEventListener('click', async function (e) {
        const anchor = e.target && e.target.closest && e.target.closest('a[href]');
        if (!anchor) return;
        const href = anchor.getAttribute('href') || '';
        if (href.indexOf('token=') !== -1) return; // already tokenized

        const dl = href.match(/\/api\/resources\/([^/?#]+)\/download/);
        const legacy = href.match(/\/api\/resources\/files\//);
        if (!dl && !legacy) return;

        e.preventDefault();
        const target = anchor.getAttribute('target') || '_self';
        let token = '';
        if (dl) {
            token = await fetchResourceAccessToken(dl[1]);
        } else {
            token = localStorage.getItem('authToken') || ''; // legacy /files/ accepts a JWT
        }
        const sep = href.indexOf('?') !== -1 ? '&' : '?';
        window.open(href + sep + 'token=' + encodeURIComponent(token), target);
    }, true);
}

// Get a Supabase presigned upload URL for direct browser-to-storage PDF uploads (Task 34)
async function getPresignedUploadUrl(filename) {
    try {
        const response = await authFetch(
            `${window.API_BASE_URL}/chapters/upload-url?filename=${encodeURIComponent(filename)}`
        );
        if (response.ok) {
            return await response.json(); // { upload_url, storage_path }
        }
    } catch (error) {
        console.error('Error getting presigned upload URL:', error);
    }
    return null;
}

