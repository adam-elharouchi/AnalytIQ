// Navigation system for AnalytIQ
document.addEventListener('DOMContentLoaded', function () {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const currentPage = window.location.pathname.split('/').pop() || 'index';

  // Check authentication
  let currentUser = null;
  try {
    const userStr = localStorage.getItem('currentUser');
    currentUser = userStr ? JSON.parse(userStr) : null;
  } catch (e) {
    currentUser = null;
  }

  const isAuthenticated = currentUser !== null;
  const userRole = currentUser ? currentUser.role : null;
  const isProfessor = userRole === 'professor';
  const isSuperAdmin = userRole === 'superadmin';
  const isTenantAdmin = userRole === 'tenant_admin';

  // Build user menu (lives outside nav-links for centering)
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
        <button class="user-menu-toggle profile-picture-btn" onclick="toggleUserMenu()" title="User Menu" aria-label="User menu" aria-expanded="false" aria-controls="userMenuDropdown">
          <img src="${avatarSrc}" alt="Profile picture" class="nav-profile-picture" />
        </button>
        <div class="user-menu-dropdown" id="userMenuDropdown">
          <div class="user-menu-header">
            <span class="user-name">${userName}</span>
          </div>
          <div class="user-menu-divider"></div>
          <button class="user-menu-item" onclick="handleManageProfile()">
            <span>Manage Profile</span>
          </button>
          <button class="user-menu-item" onclick="handleSignOut()">
            <span>Sign Out</span>
          </button>
        </div>
      </li>
    `;
  } else {
    userMenu = `
      <li><a href="/login" class="btn-login">Sign In</a></li>
    `;
  }

  // Build role-based navigation links
  let roleLinks = '';
  let commonLinks = '';

  if (isAuthenticated) {
    if (isSuperAdmin) {
      // Superadmin: Management Portals
      roleLinks = `<li><a href="/superadmin-dashboard" ${currentPage === 'superadmin-dashboard' ? 'class="active"' : ''}>Super Admin</a></li>`;
      commonLinks = '';
    } else if (isTenantAdmin) {
      roleLinks = `<li><a href="/tenant-admin-dashboard" ${currentPage === 'tenant-admin-dashboard' ? 'class="active"' : ''}>Admin Dashboard</a></li>`;
      commonLinks = '';
    } else if (isProfessor) {
      // Professors: Dashboard, Code
      roleLinks = `<li><a href="/professor-dashboard" ${currentPage === 'professor-dashboard' || currentPage === 'professor-class' ? 'class="active"' : ''}>Dashboard</a></li>`;
      commonLinks = `
        <li><a href="/code-assistant" ${currentPage === 'code-assistant' ? 'class="active"' : ''}>Code</a></li>
      `;
    } else {
      // Students: My Classes, Code
      roleLinks = `<li><a href="/student-classes" ${currentPage === 'student-classes' || currentPage === 'student-class' ? 'class="active"' : ''}>My Classes</a></li>`;
      commonLinks = `
        <li><a href="/code-assistant" ${currentPage === 'code-assistant' ? 'class="active"' : ''}>Code</a></li>
      `;
    }
  } else {
    // Not authenticated - show all links including Modules (Practice removed - now integrated into classes)
    commonLinks = `
      <li><a href="/modules" ${currentPage === 'modules' ? 'class="active"' : ''}>Modules</a></li>
      <li><a href="/resources" ${currentPage === 'resources' ? 'class="active"' : ''}>Resources</a></li>
      <li><a href="/code-assistant" ${currentPage === 'code-assistant' ? 'class="active"' : ''}>Code</a></li>
    `;
  }

  const navHTML = `
    <div class="nav-container" role="navigation" aria-label="Main navigation">
      <a href="/home" class="nav-brand" aria-label="AnalytIQ home">
        <span class="logo-analyt" aria-hidden="true">Analyt</span><span class="logo-iq" aria-hidden="true">IQ</span>
      </a>
      <button class="mobile-menu-toggle" onclick="toggleMobileMenu()" aria-label="Open navigation menu" aria-expanded="false" aria-controls="navLinks">Menu</button>
      <ul class="nav-links" id="navLinks">
        <li><a href="/home" ${currentPage === 'home' ? 'class="active"' : ''}>Home</a></li>
        ${roleLinks}
        ${commonLinks}
        ${userMenu}
      </ul>
    </div>
  `;

  navbar.innerHTML = navHTML;

  // Update profile picture in navigation if it changes
  if (isAuthenticated) {
    updateNavProfilePicture();

    // Listen for storage changes to update profile picture
    window.addEventListener('storage', function (e) {
      if (e.key === 'currentUser' || e.key === 'userProfile') {
        updateNavProfilePicture();
      }
    });

    // Also listen for custom events (for same-tab updates)
    window.addEventListener('profilePictureUpdated', function () {
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
  if (localStorage.getItem('original_token')) {
    exitImpersonation();
    return;
  }

  if (typeof uiStates !== 'undefined' && uiStates.showConfirmModal) {
    uiStates.showConfirmModal('Are you sure you want to sign out?', function () {
      localStorage.removeItem('currentUser');
      window.location.href = '/login';
    });
  } else {
    localStorage.removeItem('currentUser');
    window.location.href = '/login';
  }
}

// --- Impersonation Global Logic ---
function exitImpersonation() {
  const originalToken = localStorage.getItem('original_token');
  if (originalToken) {
    // Restore Super Admin session
    localStorage.setItem('authToken', originalToken);
    localStorage.removeItem('original_token');

    try {
      const payload = JSON.parse(atob(originalToken.split('.')[1]));
      localStorage.setItem('user_id', payload.user_id);
      localStorage.setItem('user_role', payload.role);
      localStorage.setItem('user', JSON.stringify({
        name: payload.name,
        email: payload.email,
        role: payload.role
      }));
      localStorage.setItem('currentUser', localStorage.getItem('user'));
    } catch (e) { }

    if (typeof showSuccess !== 'undefined') {
      showSuccess("Exited impersonation. Restoring Super Admin session...");
    } else {
      alert("Exited impersonation. Restoring Super Admin session...");
    }

    setTimeout(() => {
      window.location.href = '/superadmin-dashboard';
    }, 1000);
  }
}

// Impersonation banner is handled globally by templates/base.html

function toggleMobileMenu() {
  const navLinks = document.getElementById('navLinks');
  const toggle = document.querySelector('.mobile-menu-toggle');
  if (navLinks) {
    const expanded = navLinks.classList.toggle('active');
    if (toggle) toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }
}

// Toggle user menu dropdown
function toggleUserMenu() {
  const dropdown = document.getElementById('userMenuDropdown');
  const toggle = document.querySelector('.user-menu-toggle');
  if (dropdown) {
    const expanded = dropdown.classList.toggle('active');
    if (toggle) toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }
}

// Close user menu when clicking outside
document.addEventListener('click', function (event) {
  const userMenu = document.querySelector('.user-menu');
  const dropdown = document.getElementById('userMenuDropdown');
  if (userMenu && dropdown && !userMenu.contains(event.target)) {
    dropdown.classList.remove('active');
  }
});

// Handle manage profile
function handleManageProfile() {
  window.location.href = '/profile';
  const dropdown = document.getElementById('userMenuDropdown');
  if (dropdown) {
    dropdown.classList.remove('active');
  }
}

