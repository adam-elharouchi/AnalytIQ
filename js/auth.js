// Authentication System
// API_BASE_URL should be defined in api-helper.js
if (typeof window.API_BASE_URL === 'undefined') {
  window.API_BASE_URL = '/api';
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

  // Get JWT token
  getToken() {
    return localStorage.getItem('authToken');
  }

  // Save JWT token
  saveToken(token) {
    localStorage.setItem('authToken', token);
  }

  // Remove JWT token
  removeToken() {
    localStorage.removeItem('authToken');
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

      // Save JWT token
      if (data.token) {
        this.saveToken(data.token);
      }

      // Auto sign in - save user with consistent user_id
      const userData = {
        id: userId,  // Store as 'id' for compatibility with existing code
        user_id: userId,  // Also store as 'user_id' for clarity
        name: data.name || data.user?.name || name,
        email: data.email || data.user?.email || email,
        role: data.role || 'student'  // Store role
      };

      this.saveUser(userData);

      // Flag pending accounts so the caller can show the appropriate message.
      return { ...data, user: userData, pending_approval: !!data.pending_approval };
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

      const contentType = response.headers.get('Content-Type') || '';
      let data = {};
      if (contentType.includes('application/json')) {
        try {
          data = await response.json();
        } catch (_) {
          data = { error: 'Invalid response from server.' };
        }
      } else {
        const text = await response.text();
        if (response.status === 405) {
          throw new Error('Sign-in request was rejected (Method Not Allowed). The server may not be configured to handle login. Try again or contact support.');
        }
        if (!response.ok) {
          throw new Error(text && text.length < 200 ? text : `Sign in failed (${response.status}). Please try again or contact support.`);
        }
        throw new Error('Unexpected response from server. Please try again.');
      }

      if (!response.ok) {
        throw new Error(data.error || 'Sign in failed');
      }

      // Extract user ID - use user_id if available, otherwise fall back to id
      const userId = data.user_id || data.id || data.user?.user_id || data.user?.id;

      // Save JWT token
      if (data.token) {
        this.saveToken(data.token);
      }

      // Save current user (without password) - store user_id consistently
      const userData = {
        id: userId,  // Store as 'id' for compatibility with existing code
        user_id: userId,  // Also store as 'user_id' for clarity
        name: data.name || data.user?.name,
        email: data.email || data.user?.email,
        role: data.role || 'student'  // Store role
      };

      this.saveUser(userData);

      // Pass requires_password_reset flag to callers
      return { ...this.currentUser, requires_password_reset: !!data.requires_password_reset };
    } catch (error) {
      throw error;
    }
  }

  // Sign out
  signOut() {
    localStorage.removeItem('currentUser');
    this.removeToken();
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

  // Show loading state
  const submitButton = event.target.querySelector('button[type="submit"]');
  const originalButtonText = submitButton.textContent;
  submitButton.disabled = true;
  submitButton.textContent = 'Signing in...';
  errorDiv.style.display = 'none';

  try {
    const signInResult = await authManager.signIn(email, password);
    // Force password reset if flagged by admin
    if (signInResult && signInResult.requires_password_reset) {
      window.location.href = 'change-password.html?forced=true';
      return;
    }
    // Always redirect to home page
    window.location.href = 'index.html';
  } catch (error) {
    errorDiv.textContent = error.message;
    errorDiv.style.display = 'block';
    // Re-enable button on error
    submitButton.disabled = false;
    submitButton.textContent = originalButtonText;
  }
}

// Validate Hult email domain
function isValidHultEmail(email) {
  const allowedDomains = ['hult.edu', 'faculty.hult.edu', 'student.hult.edu', 'myanalytiq.org'];
  const emailDomain = email.toLowerCase().split('@')[1];
  return allowedDomains.includes(emailDomain);
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

  // Validate email domain
  if (!isValidHultEmail(email)) {
    errorDiv.textContent = 'Please use a Hult or AnalytIQ email address (e.g., hult.edu, myanalytiq.org, etc.)';
    errorDiv.style.display = 'block';
    return;
  }

  // Validate password length
  if (password.length < 8) {
    errorDiv.textContent = 'Password must be at least 8 characters';
    errorDiv.style.display = 'block';
    return;
  }
  if (password.length > 72) {
    errorDiv.textContent = 'Password must be at most 72 characters';
    errorDiv.style.display = 'block';
    return;
  }

  // Validate passwords match
  if (password !== confirmPassword) {
    errorDiv.textContent = 'Passwords do not match';
    errorDiv.style.display = 'block';
    return;
  }

  try {
    // Show loading state
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Creating account...';

    const result = await authManager.signUp(name, email, password);

    if (result && result.pending_approval) {
      // Account created but needs admin approval — show message, do not redirect yet.
      errorDiv.style.color = '#10b981';
      errorDiv.textContent = result.message ||
        'Account created! Your account is pending approval by an administrator. ' +
        'You will be notified once approved.';
      errorDiv.style.display = 'block';
      submitButton.disabled = false;
      submitButton.textContent = 'Sign Up';
      return;
    }

    // Normal path — redirect to home page
    window.location.href = 'index.html';
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

// ---------------------------------------------------------------------------
// SSO helpers
// ---------------------------------------------------------------------------

/**
 * Load SSO providers from the API and render sign-in buttons.
 * Called on DOMContentLoaded when on the login page.
 */
async function loadSSOProviders() {
  try {
    const resp = await fetch(`${window.API_BASE_URL}/sso/providers`);
    if (!resp.ok) return;
    const data = await resp.json();
    const providers = data.providers || [];
    if (providers.length === 0) return;

    const section = document.getElementById('ssoSection');
    const container = document.getElementById('ssoButtons');
    if (!section || !container) return;

    const providerIcons = { google: '🔵', microsoft: '🟦', oidc: '🔐' };

    providers.forEach(p => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-secondary btn-full';
      btn.style.cssText = 'display:flex;align-items:center;justify-content:center;gap:0.5rem;';
      const icon = providerIcons[p.provider_type] || '🔐';
      btn.innerHTML = `${icon} ${p.provider_name}`;
      btn.onclick = () => initSSOLogin(p.provider_id);
      container.appendChild(btn);
    });

    section.style.display = 'block';
  } catch (_) {
    // SSO unavailable — degrade gracefully, don't break the login page
  }
}

/**
 * Initiate SSO login for a given provider.
 * Fetches the IdP authorization URL from the backend, then redirects the browser.
 */
async function initSSOLogin(providerId) {
  try {
    const resp = await fetch(`${window.API_BASE_URL}/sso/init/${providerId}`);
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      alert(data.error || 'SSO is not available right now. Please try again.');
      return;
    }
    const data = await resp.json();
    if (data.auth_url) {
      window.location.href = data.auth_url;
    }
  } catch (_) {
    alert('SSO is not available right now. Please try again.');
  }
}

/**
 * Handle an SSO callback token delivered as ?sso_token= in the URL.
 * The backend redirects here after a successful OIDC callback.
 */
function handleSSOTokenParam() {
  const params = new URLSearchParams(window.location.search);
  const ssoToken = params.get('sso_token');
  const ssoError = params.get('sso_error');

  if (ssoError) {
    const errorDiv = document.getElementById('signinError');
    if (errorDiv) {
      errorDiv.textContent = decodeURIComponent(ssoError.replace(/\+/g, ' '));
      errorDiv.style.display = 'block';
    }
    window.history.replaceState({}, '', window.location.pathname);
    return;
  }

  if (ssoToken) {
    try {
      const payloadB64 = ssoToken.split('.')[1];
      const payload = JSON.parse(atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/')));
      authManager.saveToken(ssoToken);
      authManager.saveUser({
        id: payload.user_id,
        user_id: payload.user_id,
        name: payload.name || '',
        email: payload.email || '',
        role: payload.role || 'student',
      });
    } catch (_) {
      authManager.saveToken(ssoToken);
    }
    window.location.href = 'index.html';
  }
}

// ---------------------------------------------------------------------------
// Page load
// ---------------------------------------------------------------------------

// Check authentication on page load
document.addEventListener('DOMContentLoaded', function () {
  // Handle SSO callback token before the auth redirect check
  if (window.location.pathname.includes('login.html')) {
    handleSSOTokenParam();
  }

  // If already authenticated and on login page, redirect to home
  if (authManager.isAuthenticated() && window.location.pathname.includes('login.html')) {
    window.location.href = 'index.html';
    return;
  }

  // Load SSO provider buttons on the login page
  if (window.location.pathname.includes('login.html')) {
    loadSSOProviders();
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

// Forgot Password Functions
function showForgotPasswordModal(event) {
  if (event) event.preventDefault();
  document.getElementById('forgotPasswordModal').style.display = 'flex';
  document.getElementById('resetEmail').value = '';
  document.getElementById('resetSuccess').style.display = 'none';
  document.getElementById('resetError').style.display = 'none';
}

function closeForgotPasswordModal() {
  document.getElementById('forgotPasswordModal').style.display = 'none';
}

async function handleForgotPassword(event) {
  event.preventDefault();
  const email = document.getElementById('resetEmail').value;
  const successDiv = document.getElementById('resetSuccess');
  const errorDiv = document.getElementById('resetError');

  // Clear previous messages
  successDiv.style.display = 'none';
  errorDiv.style.display = 'none';

  // Show loading state
  const submitButton = event.target.querySelector('button[type="submit"]');
  const originalButtonText = submitButton.textContent;
  submitButton.disabled = true;
  submitButton.textContent = 'Sending...';

  try {
    const response = await fetch(`${window.API_BASE_URL}/users/forgot-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email: email })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to send reset link');
    }

    // Show success message
    successDiv.textContent = 'Password reset instructions have been sent to your email address. Please check your inbox.';
    successDiv.style.display = 'block';

    // Clear form
    document.getElementById('resetEmail').value = '';

    // Close modal after 3 seconds
    setTimeout(() => {
      closeForgotPasswordModal();
    }, 3000);

  } catch (error) {
    errorDiv.textContent = error.message;
    errorDiv.style.display = 'block';
  } finally {
    // Re-enable button
    submitButton.disabled = false;
    submitButton.textContent = originalButtonText;
  }
}
