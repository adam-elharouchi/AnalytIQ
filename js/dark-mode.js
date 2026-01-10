// Global Dark Mode Manager
// This script should be loaded on all pages to ensure dark mode works across the entire website

(function() {
  'use strict';
  
  // Apply dark mode styling globally - INSTANT (no delay)
  function applyDarkMode(enabled) {
    if (enabled) {
      document.body.classList.add('dark-mode');
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('darkModeEnabled', 'true');
    } else {
      document.body.classList.remove('dark-mode');
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('darkModeEnabled', 'false');
    }
  }
  
  // INSTANT load from localStorage (synchronous, no delay)
  function loadDarkModeInstant() {
    // Check localStorage for darkModeEnabled first (instant, no API call)
    const localDarkMode = localStorage.getItem('darkModeEnabled');
    if (localDarkMode === 'true' || localDarkMode === 'false') {
      applyDarkMode(localDarkMode === 'true');
      return localDarkMode === 'true';
    }
    
    // Fallback to userSettings in localStorage
    try {
      const userSettings = JSON.parse(localStorage.getItem('userSettings') || '{}');
      if (userSettings.darkMode !== undefined) {
        applyDarkMode(userSettings.darkMode);
        localStorage.setItem('darkModeEnabled', userSettings.darkMode ? 'true' : 'false');
        return userSettings.darkMode;
      }
    } catch (e) {
      // Ignore parse errors
    }
    
    return false;
  }
  
  // Apply dark mode IMMEDIATELY (synchronously) from localStorage - NO LAG
  // This runs before page renders to prevent flash
  const instantDarkMode = loadDarkModeInstant();
  
  // Then verify with API (async, but doesn't block rendering)
  function verifyWithAPI() {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    
    if (currentUser.id && typeof window.API_BASE_URL !== 'undefined') {
      // Fetch from API in background (non-blocking)
      fetch(`${window.API_BASE_URL}/users/settings?user_id=${currentUser.id}`)
        .then(response => {
          if (response.ok) {
            return response.json();
          }
          throw new Error('Settings not found');
        })
        .then(settings => {
          if (settings.darkMode !== undefined) {
            const apiDarkMode = settings.darkMode;
            // Only update if API value differs from current
            const currentDarkMode = document.body.classList.contains('dark-mode');
            if (apiDarkMode !== currentDarkMode) {
              applyDarkMode(apiDarkMode);
            }
            localStorage.setItem('darkModeEnabled', apiDarkMode ? 'true' : 'false');
          }
        })
        .catch(error => {
          // Silent fail - we already applied from localStorage
          console.log('API dark mode check failed, using localStorage:', error);
        });
    }
  }
  
  // Apply instantly on page load (runs immediately, no waiting)
  if (document.readyState === 'loading') {
    // Page still loading - already applied above, just verify with API later
    document.addEventListener('DOMContentLoaded', verifyWithAPI);
  } else {
    // DOM already loaded - verify with API
    verifyWithAPI();
  }
  
  // Also verify on DOMContentLoaded (in case API is ready)
  document.addEventListener('DOMContentLoaded', function() {
    verifyWithAPI();
  });
  
  // Listen for dark mode changes from other tabs/pages
  window.addEventListener('storage', function(e) {
    if (e.key === 'darkModeEnabled' || e.key === 'userSettings') {
      loadDarkModeInstant();
    }
  });
  
  // Export function globally so other scripts can use it
  window.applyDarkMode = applyDarkMode;
  window.loadDarkModePreference = loadDarkModeInstant;
  
})();
