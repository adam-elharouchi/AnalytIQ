// API Helper Functions
// Declare API_BASE_URL as a global variable - single source of truth
if (typeof window.API_BASE_URL === 'undefined') {
  window.API_BASE_URL = 'https://analytiq-qbfr.onrender.com/api';
}

// Get current user ID from localStorage
function getCurrentUserId() {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    return currentUser.id;
}

// Conversation API functions
if (typeof window.conversationAPI === 'undefined') {
  window.conversationAPI = {
    async getAll(archived = false) {
        const userId = getCurrentUserId();
        if (!userId) return [];
        
        try {
            const response = await fetch(`${window.API_BASE_URL}/users/conversations?user_id=${userId}&archived=${archived}`);
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
            const response = await fetch(`${window.API_BASE_URL}/users/conversations/${conversationId}?user_id=${userId}`);
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
            const response = await fetch(`${window.API_BASE_URL}/users/ai-digest?user_id=${userId}`);
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
            const response = await fetch(`${window.API_BASE_URL}/users/ai-memory?user_id=${userId}`);
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
        if (!userId) return { currentLanguage: 'python', geminiModel: 'gemini-2.5-flash', aiProvider: 'gemini' };
        
        try {
            const response = await fetch(`${window.API_BASE_URL}/users/preferences?user_id=${userId}`);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Error fetching preferences:', error);
        }
        return { currentLanguage: 'python', geminiModel: 'gemini-2.5-flash', aiProvider: 'gemini' };
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
            return response.ok;
        } catch (error) {
            console.error('Error updating preferences:', error);
        }
        return false;
    }
};
}

