// API Helper Functions
// Declare API_BASE_URL as a global variable - single source of truth
if (typeof window.API_BASE_URL === 'undefined') {
    // Use localhost for local testing, production URL for deployed version
    // Check for localhost, 127.0.0.1, or file:// protocol (local development)
    const isLocal = window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1' ||
        window.location.protocol === 'file:';
    window.API_BASE_URL = isLocal
        ? 'http://localhost:5001/api'
        : 'https://analytiq-qbfr.onrender.com/api';
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

// Fetch with Cache Wrapper
async function fetchWithCache(url, options = {}) {
    // Only cache GET requests
    if (options.method && options.method !== 'GET') {
        return fetch(url, options);
    }

    const cacheKey = url;
    const cachedResponse = window.apiCache.get(cacheKey);

    if (cachedResponse) {
        // Return a cloned response to allow reading body multiple times if needed
        // But since we store parsed JSON usually, we wrapping might be needed if caller expects Response object
        // For simplicity, we'll store the JSON data and caller needs to handle it
        // BUT existing code calls .json() on response. So we need to mimic Response object or change callers.
        // Let's change this: We will return a Mock Response object
        return new Response(JSON.stringify(cachedResponse), { status: 200, statusText: 'OK (Cached)' });
    }

    try {
        const response = await fetch(url, options);
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
    return '#2569f4'; // medium
}

// Conversation API functions
if (typeof window.conversationAPI === 'undefined') {
    window.conversationAPI = {
        async getAll(archived = false) {
            const userId = getCurrentUserId();
            if (!userId) return [];

            try {
                const url = `${window.API_BASE_URL}/users/conversations?user_id=${userId}&archived=${archived}`;
                const response = await fetchWithCache(url);
                if (response.ok) {
                    return await response.json();
                }
            } catch (error) {
                console.error('Error fetching conversations:', error);
            }
            return [];
        },

        async get(conversationId) {
            const userId = getCurrentUserId();
            if (!userId) return null;

            try {
                const url = `${window.API_BASE_URL}/users/conversations/${conversationId}?user_id=${userId}`;
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
            const userId = getCurrentUserId();
            if (!userId) return null;

            try {
                const response = await fetch(`${window.API_BASE_URL}/users/conversations`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
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
            const userId = getCurrentUserId();
            if (!userId) return false;

            try {
                const response = await fetch(`${window.API_BASE_URL}/users/conversations/${conversationId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        ...data
                    })
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
            const userId = getCurrentUserId();
            if (!userId) return false;

            try {
                const response = await fetch(`${window.API_BASE_URL}/users/conversations/${conversationId}?user_id=${userId}`, {
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
            const userId = getCurrentUserId();
            if (!userId) return { goal: '', constraints: '', decisions: '', current_state: '', open_questions: '' };

            try {
                const url = `${window.API_BASE_URL}/users/ai-digest?user_id=${userId}`;
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
            const userId = getCurrentUserId();
            if (!userId) return false;

            try {
                const response = await fetch(`${window.API_BASE_URL}/users/ai-digest`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        digest: digest
                    })
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
            const userId = getCurrentUserId();
            if (!userId) return [];

            try {
                const url = `${window.API_BASE_URL}/users/ai-memory?user_id=${userId}`;
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
            const userId = getCurrentUserId();
            if (!userId) return false;

            try {
                const response = await fetch(`${window.API_BASE_URL}/users/ai-memory`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        memory: memory
                    })
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
            const userId = getCurrentUserId();
            if (!userId) return { currentLanguage: 'python', geminiModel: 'gemini-3-pro-preview', aiProvider: 'gemini' };

            try {
                const url = `${window.API_BASE_URL}/users/preferences?user_id=${userId}`;
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
            const userId = getCurrentUserId();
            if (!userId) return false;

            try {
                const response = await fetch(`${window.API_BASE_URL}/users/preferences`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        ...preferences
                    })
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

