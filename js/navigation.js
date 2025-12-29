// Navigation system for AnalyticaLearn
document.addEventListener('DOMContentLoaded', function() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  
  // Check authentication
  let currentUser = null;
  try {
    const userStr = localStorage.getItem('currentUser');
    currentUser = userStr ? JSON.parse(userStr) : null;
  } catch (e) {
    currentUser = null;
  }
  
  const isAuthenticated = currentUser !== null;
  
  // Build user menu
  let userMenu = '';
  if (isAuthenticated) {
    const userName = currentUser.name || currentUser.email || 'User';
    userMenu = `
      <li class="user-menu">
        <span class="user-name">${userName}</span>
        <button class="btn-signout" onclick="handleSignOut()">Sign Out</button>
      </li>
    `;
  } else {
    userMenu = `
      <li><a href="login.html" class="btn-login">Sign In</a></li>
    `;
  }
  
  const navHTML = `
    <div class="nav-container">
      <a href="index.html" class="nav-brand">AnalyticaLearn</a>
      <button class="mobile-menu-toggle" onclick="toggleMobileMenu()">☰</button>
      <ul class="nav-links" id="navLinks">
        <li><a href="index.html" ${currentPage === 'index.html' ? 'class="active"' : ''}>Home</a></li>
        <li><a href="modules.html" ${currentPage === 'modules.html' ? 'class="active"' : ''}>Modules</a></li>
        <li><a href="practice.html" ${currentPage === 'practice.html' ? 'class="active"' : ''}>Practice</a></li>
        <li><a href="resources.html" ${currentPage === 'resources.html' ? 'class="active"' : ''}>Resources</a></li>
        <li><a href="code-assistant.html" ${currentPage === 'code-assistant.html' ? 'class="active"' : ''}>Code Assistant</a></li>
        ${userMenu}
      </ul>
    </div>
  `;
  
  navbar.innerHTML = navHTML;
});

// Handle sign out
function handleSignOut() {
  if (confirm('Are you sure you want to sign out?')) {
    localStorage.removeItem('currentUser');
    window.location.href = 'login.html';
  }
}

function toggleMobileMenu() {
  const navLinks = document.getElementById('navLinks');
  if (navLinks) {
    navLinks.classList.toggle('active');
  }
}

