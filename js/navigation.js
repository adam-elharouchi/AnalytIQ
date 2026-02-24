// Navigation system for AnalytIQ
document.addEventListener('DOMContentLoaded', function () {
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
  const userRole = currentUser ? currentUser.role : null;
  const isProfessor = userRole === 'professor';
  const isSuperAdmin = userRole === 'superadmin';

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
      <li><a href="login.html" class="btn-login">Sign In</a></li>
    `;
  }

  // Build role-based navigation links
  let roleLinks = '';
  let commonLinks = '';

  if (isAuthenticated) {
    if (isSuperAdmin) {
      // Superadmin: Management Portals
      roleLinks = `<li><a href="superadmin-dashboard.html" ${currentPage === 'superadmin-dashboard.html' ? 'class="active"' : ''} style="color: #eab308; font-weight: bold;">Super Admin</a></li>`;
      commonLinks = '';
    } else if (isProfessor) {
      // Professors: Dashboard, Code
      roleLinks = `<li><a href="professor-dashboard.html" ${currentPage === 'professor-dashboard.html' || currentPage === 'professor-class.html' ? 'class="active"' : ''}>Dashboard</a></li>`;
      commonLinks = `
        <li><a href="code-assistant.html" ${currentPage === 'code-assistant.html' ? 'class="active"' : ''}>Code</a></li>
      `;
    } else {
      // Students: My Classes, Code
      roleLinks = `<li><a href="student-classes.html" ${currentPage === 'student-classes.html' || currentPage === 'student-class.html' ? 'class="active"' : ''}>My Classes</a></li>`;
      commonLinks = `
        <li><a href="code-assistant.html" ${currentPage === 'code-assistant.html' ? 'class="active"' : ''}>Code</a></li>
      `;
    }
  } else {
    // Not authenticated - show all links including Modules (Practice removed - now integrated into classes)
    commonLinks = `
      <li><a href="modules.html" ${currentPage === 'modules.html' ? 'class="active"' : ''}>Modules</a></li>
      <li><a href="resources.html" ${currentPage === 'resources.html' ? 'class="active"' : ''}>Resources</a></li>
      <li><a href="code-assistant.html" ${currentPage === 'code-assistant.html' ? 'class="active"' : ''}>Code</a></li>
    `;
  }

  const navHTML = `
    <div class="nav-container" role="navigation" aria-label="Main navigation">
      <a href="index.html" class="nav-brand" aria-label="AnalytIQ home">
        <span class="logo-analyt" aria-hidden="true">Analyt</span><span class="logo-iq" aria-hidden="true">IQ</span>
      </a>
      <button class="mobile-menu-toggle" onclick="toggleMobileMenu()" aria-label="Open navigation menu" aria-expanded="false" aria-controls="navLinks">Menu</button>
      <ul class="nav-links" id="navLinks">
        <li><a href="index.html" ${currentPage === 'index.html' ? 'class="active"' : ''}>Home</a></li>
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
      window.location.href = 'login.html';
    });
  } else {
    localStorage.removeItem('currentUser');
    window.location.href = 'login.html';
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
      window.location.href = 'superadmin-dashboard.html';
    }, 1000);
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const originalToken = localStorage.getItem('original_token');
  if (originalToken) {
    let currentUser = {};
    try {
      currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
      // Sometimes stored as 'user' depending on the auth flow
      if (!currentUser.name) {
        currentUser = JSON.parse(localStorage.getItem('user') || '{}');
      }
    } catch (e) { }

    const userName = currentUser.name || currentUser.email || 'User';

    const banner = document.createElement('div');
    banner.id = 'global-impersonation-banner';
    banner.style.cssText = 'background: linear-gradient(90deg, #f59e0b, #d97706); color: white; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3); text-align: center; padding: 12px; font-weight: 600; z-index: 9999; display: flex; justify-content: center; align-items: center; gap: 1rem; position: relative; width: 100%;';

    banner.innerHTML = `
            <span>You are currently impersonating <span>${userName}</span>.</span>
            <button onclick="exitImpersonation()" class="btn btn-secondary btn-sm"
                style="background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.2); color: white; cursor: pointer; padding: 0.25rem 0.75rem; border-radius: 0.25rem;">Exit
                Impersonation</button>
        `;

    document.body.prepend(banner);
  }
});

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
  window.location.href = 'profile.html';
  const dropdown = document.getElementById('userMenuDropdown');
  if (dropdown) {
    dropdown.classList.remove('active');
  }
}

