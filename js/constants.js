/**
 * constants.js — centralised magic values (Task 15)
 *
 * Import order: load before other JS modules so they can reference APP_CONSTANTS.
 */
window.APP_CONSTANTS = {
    // Auth
    AUTH_TOKEN_KEY:   'authToken',
    USER_STORAGE_KEY: 'currentUser',

    // API
    DEFAULT_PAGE_SIZE: 10,
    MAX_PAGE_SIZE:     100,

    // UI
    DEBOUNCE_MS:      500,
    TOAST_DURATION_MS: 3000,
    CACHE_TTL_MS:     300000, // 5 min — matches apiCache.TTL in api-helper.js

    // Exercise difficulty colours (mirrors getDifficultyColor in api-helper.js)
    DIFFICULTY_COLORS: {
        easy:   '#10b981',
        medium: '#2569f4',
        hard:   '#ef4444',
    },

    // File upload limits (mirrors config.py)
    MAX_PDF_SIZE_MB: 50,
    ALLOWED_EXTENSIONS: ['pdf'],
};
