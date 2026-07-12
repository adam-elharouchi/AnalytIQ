// Student Classes - View Enrolled Classes
// API_BASE_URL should be defined in api-helper.js

if (typeof window.API_BASE_URL === 'undefined') {
  window.API_BASE_URL = '/api';
}

// Get current user
function getCurrentUser() {
  try {
    const userStr = localStorage.getItem('currentUser');
    return userStr ? JSON.parse(userStr) : null;
  } catch (e) {
    return null;
  }
}

// Load enrolled classes for student
async function loadEnrolledClasses() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id) {
    console.error('No user found');
    return;
  }

  const loadingState = document.getElementById('loadingState');
  const emptyState = document.getElementById('emptyState');
  const classesGrid = document.getElementById('classesGrid');

  try {
    loadingState.style.display = 'flex';
    emptyState.style.display = 'none';
    classesGrid.style.display = 'none';

    const response = await authFetch(`${window.API_BASE_URL}/classes/enrolled`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to load classes');
    }

    loadingState.style.display = 'none';

    if (!data.classes || data.classes.length === 0) {
      // Update breadcrumb to show 0 nodes
      const countLabel = document.getElementById('classCountLabel');
      if (countLabel) countLabel.textContent = '· 0 classes enrolled';

      // Update status to neutral
      const dot = document.getElementById('wsStatusDot');
      const label = document.getElementById('wsStatusLabel');
      if (dot) { dot.style.background = '#64748b'; dot.style.boxShadow = 'none'; }
      if (label) { label.textContent = 'No Active Nodes'; label.style.color = '#64748b'; }

      emptyState.style.display = 'block';
      classesGrid.style.display = 'none';
    } else {
      emptyState.style.display = 'none';
      renderClasses(data.classes);
    }
  } catch (error) {
    console.error('Error loading classes:', error);
    loadingState.style.display = 'none';
    emptyState.style.display = 'block';
    uiStates.showError(emptyState, 'Error loading classes: ' + error.message, () => loadEnrolledClasses());
  }
}

// Render classes grid with asymmetric layout
function renderClasses(classes) {
  const classesGrid = document.getElementById('classesGrid');
  const count = classes.length;

  // Update breadcrumb count
  const countLabel = document.getElementById('classCountLabel');
  if (countLabel) {
    countLabel.textContent = `· ${count} class${count !== 1 ? 'es' : ''} enrolled`;
  }

  // Set grid based on count
  if (count === 1) {
    classesGrid.style.cssText = 'display: grid; grid-template-columns: 1fr; gap: 1.5rem;';
  } else {
    classesGrid.style.cssText = 'display: grid; grid-template-columns: repeat(12, 1fr); gap: 1.5rem;';
  }

  classesGrid.innerHTML = classes.map((classItem, index) => {
    // Asymmetric spans: 2 cards → 7/5, 3+ → first 8, rest 4
    let spanStyle = '';
    const isFeatured = index === 0 && count > 1;

    if (count === 2) {
      spanStyle = index === 0 ? 'grid-column: span 7;' : 'grid-column: span 5;';
    } else if (count >= 3) {
      spanStyle = index === 0 ? 'grid-column: span 8;' : 'grid-column: span 4;';
    }

    return `
      <div class="class-card neon-hover"
        style="${spanStyle} background: var(--color-dark); border-radius: 1rem; border: 1px solid rgba(255,255,255,0.1); overflow: hidden; display: flex; flex-direction: column; cursor: pointer;"
        onclick="viewClass('${escapeHtml(classItem.class_id)}')">

        <!-- IDE Tab Header -->
        <div style="background: rgba(0,0,0,0.2); padding: 0.65rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.5rem; font-family: var(--font-mono); font-size: 0.75rem; color: #64748b;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
            ${escapeHtml(classItem.class_id || '')}.workspace
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            ${isFeatured ? '<span style="font-family: var(--font-mono); font-size: 0.66rem; color: rgba(37,105,244,0.7); background: rgba(37,105,244,0.1); border: 1px solid rgba(37,105,244,0.25); padding: 0.1rem 0.45rem; border-radius: 0.25rem; text-transform: uppercase; letter-spacing: 0.04em;">PRIMARY</span>' : ''}
            <div class="card-indicator" style="width: 8px; height: 8px; border-radius: 50%; background: var(--color-success); opacity: 0.5; transition: opacity 0.2s, box-shadow 0.2s;"></div>
          </div>
        </div>

        <div style="padding: ${isFeatured ? '2rem' : '1.25rem 1.5rem'}; flex: 1; display: flex; flex-direction: column;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.6rem; gap: 1rem;">
            <h3 style="margin: 0; color: #f8fafc; font-size: ${isFeatured ? '1.4rem' : '1.1rem'}; font-weight: 700; line-height: 1.2;">
              ${escapeHtml(classItem.name)}
            </h3>
          </div>
          <p style="color: var(--color-primary); font-size: 0.75rem; margin: 0 0 ${isFeatured ? '1rem' : '0.65rem'} 0; display: flex; align-items: center; gap: 0.35rem; font-family: var(--font-mono);">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
            </svg>
            Prof. ${escapeHtml(classItem.professor_name || 'Unknown')}
          </p>

          ${classItem.description
            ? `<p style="color: #94a3b8; font-size: ${isFeatured ? '0.9rem' : '0.85rem'}; margin-bottom: ${isFeatured ? '1.25rem' : '1rem'}; line-height: 1.55; flex: 1;">${escapeHtml(classItem.description)}</p>`
            : '<div style="flex:1;"></div>'}

          <div style="display: flex; margin-bottom: ${isFeatured ? '1.25rem' : '1rem'}; border: 1px solid rgba(255,255,255,0.06); border-radius: 0.5rem; overflow: hidden; background: rgba(0,0,0,0.15);">
            <div style="flex: 1; text-align: center; padding: 0.75rem 0.5rem; border-right: 1px solid rgba(255,255,255,0.06);">
              <div style="font-size: ${isFeatured ? '1.75rem' : '1.25rem'}; font-family: var(--font-mono); color: #f8fafc; font-weight: 700; line-height: 1;">${classItem.chapter_count || 0}</div>
              <div style="font-size: 0.65rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.25rem;">Modules</div>
            </div>
            <div style="flex: 1; text-align: center; padding: 0.75rem 0.5rem;">
              <div style="font-size: ${isFeatured ? '1.75rem' : '1.25rem'}; font-family: var(--font-mono); color: #f8fafc; font-weight: 700; line-height: 1;">${classItem.student_count || 0}</div>
              <div style="font-size: 0.65rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.25rem;">Peers</div>
            </div>
          </div>

          <div style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: ${isFeatured ? '1.25rem' : '0.85rem'};">
            <button
              class="btn btn-primary"
              style="width: 100%; font-size: 0.85rem; display: flex; align-items: center; justify-content: center; gap: 0.4rem;"
              onclick="event.stopPropagation(); viewClass('${escapeHtml(classItem.class_id)}')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events:none;"><polyline points="9 18 15 12 9 6"/></svg>
              Enter Class
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  // Activate indicator on hover (using neon-hover class for the glow; this handles the dot)
  classesGrid.querySelectorAll('.class-card').forEach(card => {
    card.addEventListener('mouseenter', function () {
      const dot = this.querySelector('.card-indicator');
      if (dot) { dot.style.opacity = '1'; dot.style.boxShadow = '0 0 8px var(--color-success)'; }
    });
    card.addEventListener('mouseleave', function () {
      const dot = this.querySelector('.card-indicator');
      if (dot) { dot.style.opacity = '0.5'; dot.style.boxShadow = 'none'; }
    });
  });
}

// Show join class drawer (replaces old modal)
function showJoinClassDrawer() {
  document.getElementById('joinDrawerOverlay').classList.add('visible');
  document.getElementById('joinClassDrawer').classList.add('visible');
  const input = document.getElementById('classCode');
  if (input) {
    input.focus();
    input.addEventListener('input', function () {
      this.value = this.value.toUpperCase();
    });
  }
}

// Hide join class drawer
function hideJoinClassDrawer() {
  document.getElementById('joinDrawerOverlay').classList.remove('visible');
  document.getElementById('joinClassDrawer').classList.remove('visible');
  const form = document.getElementById('joinClassForm');
  if (form) form.reset();
  const errorDiv = document.getElementById('joinClassError');
  if (errorDiv) errorDiv.style.display = 'none';
}

// Backward-compat aliases (used by any older HTML references)
function showJoinClassModal() { showJoinClassDrawer(); }
function hideJoinClassModal() { hideJoinClassDrawer(); }

// Handle join class form submission
async function handleJoinClass(event) {
  event.preventDefault();

  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id) {
    alert('Please sign in to join a class');
    return;
  }

  const classCode = document.getElementById('classCode').value.trim().toUpperCase();
  const errorDiv = document.getElementById('joinClassError');

  if (!classCode || classCode.length < 3 || classCode.length > 20) {
    errorDiv.textContent = '> ERROR: Invalid token. Expected 3-20 chars [A-Z, 0-9, -, _]';
    errorDiv.style.display = 'block';
    return;
  }

  try {
    errorDiv.style.display = 'none';
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.textContent = '>_ connecting...';

    const response = await authFetch(`${window.API_BASE_URL}/classes/enroll`, {
      method: 'POST',
      body: JSON.stringify({ class_id: classCode })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to join class');
    }

    hideJoinClassDrawer();
    loadEnrolledClasses();
    alert(`Successfully joined "${data.class_name}"!`);

  } catch (error) {
    console.error('Error joining class:', error);
    const errorDiv = document.getElementById('joinClassError');
    errorDiv.textContent = '> ERROR: ' + error.message;
    errorDiv.style.display = 'block';
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = false;
    submitButton.textContent = '>_ execute: join';
  }
}

// Navigate to class view
function viewClass(classId) {
  window.location.href = `/student-class?class_id=${encodeURIComponent(classId)}`;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Close drawer with Escape key
document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape') {
    hideJoinClassDrawer();
  }
});

// CSP: wire the join-class drawer triggers here instead of inline on* attributes.
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.js-show-join-class').forEach(function (el) {
    el.addEventListener('click', showJoinClassDrawer);
  });
  document.querySelectorAll('.js-hide-join-class').forEach(function (el) {
    el.addEventListener('click', hideJoinClassDrawer);
  });
  const joinClassForm = document.getElementById('joinClassForm');
  if (joinClassForm) joinClassForm.addEventListener('submit', handleJoinClass);
});
