// Authentication System
class AuthManager {
  constructor() {
    this.currentUser = null;
    this.loadUser();
  }

  // Load user from localStorage
  loadUser() {
    const userStr = localStorage.getItem('currentUser');
    if (userStr) {
      this.currentUser = JSON.parse(userStr);
    }
  }

  // Save user to localStorage
  saveUser(user) {
    localStorage.setItem('currentUser', JSON.stringify(user));
    this.currentUser = user;
  }

  // Sign up new user
  async signUp(name, email, password) {
    // Check if user already exists
    const users = this.getUsers();
    if (users.find(u => u.email === email)) {
      throw new Error('Email already registered');
    }

    // Create new user
    const user = {
      id: Date.now().toString(),
      name: name,
      email: email,
      password: this.hashPassword(password), // Simple hash for demo
      createdAt: new Date().toISOString()
    };

    // Save user
    users.push(user);
    localStorage.setItem('users', JSON.stringify(users));

    // Auto sign in
    this.saveUser({
      id: user.id,
      name: user.name,
      email: user.email
    });

    // Send welcome email
    try {
      if (typeof emailService !== 'undefined') {
        await emailService.sendWelcomeEmail(email, name);
      }
    } catch (error) {
      console.error('Failed to send welcome email:', error);
      // Don't throw error - email failure shouldn't prevent signup
    }

    return user;
  }

  // Sign in user
  signIn(email, password) {
    const users = this.getUsers();
    const user = users.find(u => u.email === email);
    
    if (!user) {
      throw new Error('Email not found');
    }

    if (user.password !== this.hashPassword(password)) {
      throw new Error('Incorrect password');
    }

    // Save current user (without password)
    this.saveUser({
      id: user.id,
      name: user.name,
      email: user.email
    });

    return this.currentUser;
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

  // Get all users (for demo purposes)
  getUsers() {
    const usersStr = localStorage.getItem('users');
    return usersStr ? JSON.parse(usersStr) : [];
  }

  // Simple password hash (for demo - in production use proper hashing)
  hashPassword(password) {
    // Simple hash for demo purposes
    let hash = 0;
    for (let i = 0; i < password.length; i++) {
      const char = password.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash.toString();
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
function handleSignIn(event) {
  event.preventDefault();
  const email = document.getElementById('signinEmail').value;
  const password = document.getElementById('signinPassword').value;
  const errorDiv = document.getElementById('signinError');

  try {
    authManager.signIn(email, password);
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
    
    // Show success message about email
    showEmailNotification(email);
    
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

// Show email notification
function showEmailNotification(email) {
  // Create notification element
  const notification = document.createElement('div');
  notification.className = 'email-notification';
  notification.innerHTML = `
    <div class="email-notification-content">
      <div class="email-notification-icon">📧</div>
      <div class="email-notification-text">
        <strong>Welcome email sent!</strong>
        <p>We've sent a welcome email to <strong>${email}</strong>. Please check your inbox.</p>
      </div>
    </div>
  `;
  
  // Add to page
  document.body.appendChild(notification);
  
  // Show notification
  setTimeout(() => {
    notification.classList.add('show');
  }, 10);
  
  // Hide and remove after 5 seconds
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => {
      notification.remove();
    }, 300);
  }, 5000);
}

// Show tab
function showTab(tabName) {
  // Hide all tabs
  document.querySelectorAll('.login-tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  document.querySelectorAll('.login-tab').forEach(tab => {
    tab.classList.remove('active');
  });

  // Show selected tab
  document.getElementById(tabName + 'Tab').classList.add('active');
  event.target.classList.add('active');
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

