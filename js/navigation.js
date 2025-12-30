// Navigation system for AnalytIQ
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
    // Get profile picture from currentUser or userProfile
    const profileData = JSON.parse(localStorage.getItem('userProfile') || '{}');
    const profilePicture = currentUser.profilePicture || profileData.profilePicture;
    const defaultAvatar = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iIzMzNDE1NSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjQwIiBmaWxsPSIjOTRhM2I4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+8J+RpTwvdGV4dD48L3N2Zz4=';
    const avatarSrc = profilePicture || defaultAvatar;
    
    userMenu = `
      <li class="user-menu">
        <button class="user-menu-toggle profile-picture-btn" onclick="toggleUserMenu()" title="User Menu">
          <img src="${avatarSrc}" alt="Profile" class="nav-profile-picture" />
        </button>
        <div class="user-menu-dropdown" id="userMenuDropdown">
          <div class="user-menu-header">
            <span class="user-name">${userName}</span>
          </div>
          <div class="user-menu-divider"></div>
          <button class="user-menu-item" onclick="handleManageProfile()">
            <span>👤</span>
            <span>Manage Profile</span>
          </button>
          <button class="user-menu-item" onclick="handleSignOut()">
            <span>🚪</span>
            <span>Sign Out</span>
          </button>
        </div>
      </li>
    `;
  } else {
    userMenu = `
      <li><a href="login.html" class="btn-login">Sign In</a></li>
    `;
  }
  
  const navHTML = `
    <div class="nav-container">
      <a href="index.html" class="nav-brand">
        <span class="logo-analyt">Analyt</span><span class="logo-iq">IQ</span>
      </a>
      <button class="mobile-menu-toggle" onclick="toggleMobileMenu()">☰</button>
      <ul class="nav-links" id="navLinks">
        <li><a href="index.html" ${currentPage === 'index.html' ? 'class="active"' : ''}>Home</a></li>
        <li><a href="modules.html" ${currentPage === 'modules.html' ? 'class="active"' : ''}>Modules</a></li>
        <li><a href="practice.html" ${currentPage === 'practice.html' ? 'class="active"' : ''}>Practice</a></li>
        <li><a href="resources.html" ${currentPage === 'resources.html' ? 'class="active"' : ''}>Resources</a></li>
        <li><a href="code-assistant.html" ${currentPage === 'code-assistant.html' ? 'class="active"' : ''}>Code</a></li>
        ${userMenu}
      </ul>
    </div>
  `;
  
  navbar.innerHTML = navHTML;
  
  // Update profile picture in navigation if it changes
  if (isAuthenticated) {
    updateNavProfilePicture();
    
    // Listen for storage changes to update profile picture
    window.addEventListener('storage', function(e) {
      if (e.key === 'currentUser' || e.key === 'userProfile') {
        updateNavProfilePicture();
      }
    });
    
    // Also listen for custom events (for same-tab updates)
    window.addEventListener('profilePictureUpdated', function() {
      updateNavProfilePicture();
    });
  }
});

// Update profile picture in navigation
function updateNavProfilePicture() {
  try {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    const profileData = JSON.parse(localStorage.getItem('userProfile') || '{}');
    const profilePicture = currentUser.profilePicture || profileData.profilePicture;
    const defaultAvatar = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iIzMzNDE1NSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjQwIiBmaWxsPSIjOTRhM2I4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+8J+RpTwvdGV4dD48L3N2Zz4=';
    
    const navProfilePic = document.querySelector('.nav-profile-picture');
    if (navProfilePic) {
      navProfilePic.src = profilePicture || defaultAvatar;
    }
  } catch (e) {
    console.error('Error updating nav profile picture:', e);
  }
}

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

// Toggle user menu dropdown
function toggleUserMenu() {
  const dropdown = document.getElementById('userMenuDropdown');
  if (dropdown) {
    dropdown.classList.toggle('active');
  }
}

// Close user menu when clicking outside
document.addEventListener('click', function(event) {
  const userMenu = document.querySelector('.user-menu');
  const dropdown = document.getElementById('userMenuDropdown');
  if (userMenu && dropdown && !userMenu.contains(event.target)) {
    dropdown.classList.remove('active');
  }
});

// Handle manage profile
function handleManageProfile() {
  window.location.href = 'profile.html';
  const dropdown = document.getElementById('userMenuDropdown');
  if (dropdown) {
    dropdown.classList.remove('active');
  }
}

