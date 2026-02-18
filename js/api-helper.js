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

// Get auth headers for API requests
function getAuthHeaders(extraHeaders = {}) {
    const headers = { 'Content-Type': 'application/json', ...extraHeaders };
    const token = localStorage.getItem('authToken');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

// Authenticated fetch wrapper - adds JWT token to all requests
async function authFetch(url, options = {}) {
    // Add Authorization header
    const token = localStorage.getItem('authToken');
    if (token) {
        options.headers = options.headers || {};
        // Don't override Content-Type for FormData (multipart)
        if (!(options.body instanceof FormData)) {
            options.headers['Content-Type'] = options.headers['Content-Type'] || 'application/json';
        }
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    return fetch(url, options);
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
            if (!getCurrentUserId()) return { currentLanguage: 'python', geminiModel: 'gemini-3-pro-preview', aiProvider: 'gemini' };

            try {
                const url = `${window.API_BASE_URL}/users/preferences`;
                const response = await fetchWithCache(url);
                if (response.ok) {
                    return await response.json();
                }
            } catch (error) {
                console.error('Error fetching preferences:', error);
            }
            return { currentLanguage: 'python', geminiModel: 'gemini-3-pro-preview', aiProvider: 'gemini' };
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

