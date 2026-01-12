// Authentication System
// API_BASE_URL should be defined in api-helper.js
if (typeof window.API_BASE_URL === 'undefined') {
  window.API_BASE_URL = 'https://analytiq-qbfr.onrender.com/api';
}

class AuthManager {
  constructor() {
    this.currentUser = null;
    this.loadUser();
  }

  // Load user from localStorage (for session persistence)
  loadUser() {
    const userStr = localStorage.getItem('currentUser');
    if (userStr) {
      this.currentUser = JSON.parse(userStr);
    }
  }

  // Save user to localStorage (for session persistence)
  saveUser(user) {
    localStorage.setItem('currentUser', JSON.stringify(user));
    this.currentUser = user;
  }

  // Sign up new user
  async signUp(name, email, password) {
    try {
      const response = await fetch(`${window.API_BASE_URL}/users/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: name,
          email: email,
          password: password
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Sign up failed');
      }

      // Extract user ID - use user_id if available, otherwise fall back to id
      const userId = data.user_id || data.id || data.user?.user_id || data.user?.id || Date.now().toString();
      
      // Auto sign in - save user with consistent user_id
      const userData = {
        id: userId,  // Store as 'id' for compatibility with existing code
        user_id: userId,  // Also store as 'user_id' for clarity
        name: data.name || data.user?.name || name,
        email: data.email || data.user?.email || email
      };
      
      this.saveUser(userData);
      
      // Log successful signup for debugging
      console.log('User signed up successfully:', { 
        userId: userId, 
        name: userData.name, 
        email: userData.email,
        savedToDB: data.success !== false 
      });

      return { ...data, user: userData };
    } catch (error) {
      throw error;
    }
  }

  // Sign in user
  async signIn(email, password) {
    try {
      const response = await fetch(`${window.API_BASE_URL}/users/signin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: email,
          password: password
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Sign in failed');
      }

      // Extract user ID - use user_id if available, otherwise fall back to id
      const userId = data.user_id || data.id || data.user?.user_id || data.user?.id;
      
      // Save current user (without password) - store user_id consistently
      const userData = {
        id: userId,  // Store as 'id' for compatibility with existing code
        user_id: userId,  // Also store as 'user_id' for clarity
        name: data.name || data.user?.name,
        email: data.email || data.user?.email
      };
      
      this.saveUser(userData);

      return this.currentUser;
    } catch (error) {
      throw error;
    }
  }

  // Sign out
  signOut() {
    localStorage.removeItem('currentUser');
    this.currentUser = null;
  }

  // Check if user is authenticated
  isAuthenticated() {
    return this.currentUser !== null;
  }

  // Get current user
  getCurrentUser() {
    return this.currentUser;
  }


  // Require authentication - redirect to login if not authenticated
  requireAuth() {
    if (!this.isAuthenticated()) {
      window.location.href = 'login.html';
      return false;
    }
    return true;
  }
}

// Global auth manager instance
const authManager = new AuthManager();

// Handle sign in
async function handleSignIn(event) {
  event.preventDefault();
  const email = document.getElementById('signinEmail').value;
  const password = document.getElementById('signinPassword').value;
  const errorDiv = document.getElementById('signinError');

  try {
    await authManager.signIn(email, password);
    // Redirect to home page
    window.location.href = 'index.html';
  } catch (error) {
    errorDiv.textContent = error.message;
    errorDiv.style.display = 'block';
  }
}

// Handle sign up
async function handleSignUp(event) {
  event.preventDefault();
  const name = document.getElementById('signupName').value;
  const email = document.getElementById('signupEmail').value;
  const password = document.getElementById('signupPassword').value;
  const confirmPassword = document.getElementById('signupConfirmPassword').value;
  const errorDiv = document.getElementById('signupError');

  // Clear previous errors
  errorDiv.style.display = 'none';

  // Validate passwords match
  if (password !== confirmPassword) {
    errorDiv.textContent = 'Passwords do not match';
    errorDiv.style.display = 'block';
    return;
  }

  try {
    // Show loading state
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.textContent = 'Creating account...';

    await authManager.signUp(name, email, password);
    
    // Small delay to show notification, then redirect
    setTimeout(() => {
      window.location.href = 'index.html';
    }, 2000);
  } catch (error) {
    errorDiv.textContent = error.message;
    errorDiv.style.display = 'block';
    
    // Re-enable button
    const submitButton = event.target.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = 'Sign Up';
    }
  }
}

// Show tab
function showTab(tabName, buttonElement) {
  // Hide all tabs
  document.querySelectorAll('.login-tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  document.querySelectorAll('.login-tab').forEach(tab => {
    tab.classList.remove('active');
  });

  // Show selected tab
  document.getElementById(tabName + 'Tab').classList.add('active');
  
  // Activate the clicked button
  if (buttonElement) {
    buttonElement.classList.add('active');
  } else {
    // Fallback: find button by tab name
    const buttons = document.querySelectorAll('.login-tab');
    buttons.forEach(btn => {
      if (btn.textContent.trim().toLowerCase().includes(tabName.toLowerCase())) {
        btn.classList.add('active');
      }
    });
  }
}

// Check authentication on page load
document.addEventListener('DOMContentLoaded', function() {
  // If already authenticated and on login page, redirect to home
  if (authManager.isAuthenticated() && window.location.pathname.includes('login.html')) {
    window.location.href = 'index.html';
  }
  
  // If not authenticated and trying to access any page except login, redirect to login
  // This is handled by requireAuth() on each page, but we can add a global check here too
  if (!authManager.isAuthenticated() && !window.location.pathname.includes('login.html')) {
    // This will be handled by individual pages, but we can add a fallback
    const currentPage = window.location.pathname.split('/').pop();
    if (currentPage && currentPage !== 'login.html' && currentPage !== '') {
      // Will be redirected by requireAuth() on each page
    }
  }
});
