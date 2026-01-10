// Global Dark Mode Manager
// This script should be loaded on all pages to ensure dark mode works across the entire website

(function() {
  'use strict';
  
  // Apply dark mode styling globally
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
  
  // Load dark mode preference on page load
  function loadDarkModePreference() {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    
    // If user is logged in, prioritize API settings
    if (currentUser.id && typeof window.API_BASE_URL !== 'undefined') {
      // Fetch user settings from API first (this is the source of truth)
      fetch(`${window.API_BASE_URL}/users/settings?user_id=${currentUser.id}`)
        .then(response => {
          if (response.ok) {
            return response.json();
          }
          throw new Error('Settings not found');
        })
        .then(settings => {
          if (settings.darkMode !== undefined) {
            applyDarkMode(settings.darkMode);
            localStorage.setItem('darkModeEnabled', settings.darkMode ? 'true' : 'false');
            return; // Exit early if API returned settings
          }
          // Fall through to localStorage if API doesn't have darkMode setting
          checkLocalStorage();
        })
        .catch(error => {
          console.log('Could not fetch dark mode from API, using localStorage:', error);
          checkLocalStorage();
        });
    } else {
      // No user logged in, use localStorage only
      checkLocalStorage();
    }
    
    function checkLocalStorage() {
      // Check localStorage for darkModeEnabled first (fastest)
      const localDarkMode = localStorage.getItem('darkModeEnabled');
      if (localDarkMode === 'true' || localDarkMode === 'false') {
        applyDarkMode(localDarkMode === 'true');
        return;
      }
      
      // Fallback to userSettings in localStorage
      const userSettings = JSON.parse(localStorage.getItem('userSettings') || '{}');
      if (userSettings.darkMode !== undefined) {
        applyDarkMode(userSettings.darkMode);
        localStorage.setItem('darkModeEnabled', userSettings.darkMode ? 'true' : 'false');
      }
    }
  }
  
  // Apply dark mode immediately on page load (before DOM is ready for instant application)
  if (document.readyState === 'loading') {
    loadDarkModePreference();
  } else {
    // DOM already loaded
    loadDarkModePreference();
  }
  
  // Also apply on DOMContentLoaded (in case settings load async)
  document.addEventListener('DOMContentLoaded', function() {
    loadDarkModePreference();
  });
  
  // Listen for dark mode changes from other tabs/pages
  window.addEventListener('storage', function(e) {
    if (e.key === 'darkModeEnabled' || e.key === 'userSettings') {
      loadDarkModePreference();
    }
  });
  
  // Export function globally so other scripts can use it
  window.applyDarkMode = applyDarkMode;
  window.loadDarkModePreference = loadDarkModePreference;
  
})();
