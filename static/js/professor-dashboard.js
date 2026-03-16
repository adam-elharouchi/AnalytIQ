// Professor Dashboard - Class Management
// API_BASE_URL should be defined in api-helper.js

// API_BASE_URL and getCurrentUser are defined in api-helper.js

// Load classes for professor
async function loadClasses() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id) {
    console.error('No user found');
    return;
  }

  const loadingState = document.getElementById('loadingState');
  const emptyState = document.getElementById('emptyState');
  const classesGrid = document.getElementById('classesGrid');

  try {
    loadingState.style.display = 'block';
    emptyState.style.display = 'none';
    classesGrid.style.display = 'none';

    const response = await authFetch(`${window.API_BASE_URL}/classes`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to load classes');
    }

    loadingState.style.display = 'none';

    const dot = document.getElementById('wsStatusDot');
    const label = document.getElementById('wsStatusLabel');

    if (!data.classes || data.classes.length === 0) {
      emptyState.style.display = 'block';
      classesGrid.style.display = 'none';
      const countLabel = document.getElementById('classCountLabel');
      if (countLabel) countLabel.textContent = '· 0 classes';
      if (dot) { dot.style.background = '#64748b'; dot.style.boxShadow = 'none'; }
      if (label) { label.textContent = 'No Classes Yet'; label.style.color = '#64748b'; }
    } else {
      emptyState.style.display = 'none';
      classesGrid.style.display = 'grid';
      const count = data.classes.length;
      const countLabel = document.getElementById('classCountLabel');
      if (countLabel) countLabel.textContent = `· ${count} class${count !== 1 ? 'es' : ''}`;
      renderClasses(data.classes);
    }
  } catch (error) {
    console.error('Error loading classes:', error);
    loadingState.style.display = 'none';
    emptyState.style.display = 'block';
    uiStates.showError(emptyState, 'Error loading classes: ' + error.message, () => loadClasses());
  }
}

// Render classes grid — asymmetric bento layout with neon hover
function renderClasses(classes) {
  const classesGrid = document.getElementById('classesGrid');
  const count = classes.length;

  // Set grid based on count
  if (count === 1) {
    classesGrid.style.cssText = 'display: grid; grid-template-columns: 1fr; gap: 1.5rem;';
  } else {
    classesGrid.style.cssText = 'display: grid; grid-template-columns: repeat(12, 1fr); gap: 1.5rem;';
  }

  classesGrid.innerHTML = classes.map((classItem, index) => {
    const isFeatured = index === 0 && count > 1;

    // Asymmetric: first card span 8 (primary node), rest span 4
    let spanStyle = '';
    if (count === 2) {
      spanStyle = index === 0 ? 'grid-column: span 8;' : 'grid-column: span 4;';
    } else if (count >= 3) {
      spanStyle = index === 0 ? 'grid-column: span 8;' : 'grid-column: span 4;';
    }

    return `
    <div class="class-card bento-card neon-hover"
      style="${spanStyle} display: flex; flex-direction: column; cursor: default; overflow: hidden; padding: 0;">

      <!-- IDE-style tab header -->
      <div style="background: rgba(0,0,0,0.25); padding: 0.65rem 1.25rem; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;">
        <div style="display: flex; align-items: center; gap: 0.5rem; font-family: var(--font-mono); font-size: 0.75rem; color: #64748b;">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          ${escapeHtml(classItem.class_id)}.node
        </div>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          ${isFeatured ? '<span style="font-family: var(--font-mono); font-size: 0.66rem; color: rgba(37,105,244,0.7); background: rgba(37,105,244,0.1); border: 1px solid rgba(37,105,244,0.25); padding: 0.1rem 0.45rem; border-radius: 0.25rem; text-transform: uppercase; letter-spacing: 0.04em;">PRIMARY NODE</span>' : ''}
          <div class="card-indicator" style="width: 8px; height: 8px; border-radius: 50%; background: var(--color-success); opacity: 0.5; transition: opacity 0.2s, box-shadow 0.2s;"></div>
        </div>
      </div>

      <div style="padding: ${isFeatured ? '2rem' : '1.25rem 1.5rem'}; flex: 1; display: flex; flex-direction: column;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem; gap: 1rem;">
          <h3 style="margin: 0; font-size: ${isFeatured ? '1.45rem' : '1.1rem'}; color: #f8fafc; font-weight: 700; line-height: 1.2;">
            ${escapeHtml(classItem.name)}
          </h3>
          <span style="flex-shrink: 0; background: rgba(37,105,244,0.08); border: 1px solid rgba(37,105,244,0.25); color: rgba(37,105,244,0.8); padding: 0.2rem 0.55rem; border-radius: 0.25rem; font-size: 0.75rem; font-family: var(--font-mono); white-space: nowrap;">
            ${escapeHtml(classItem.class_id)}
          </span>
        </div>

        ${classItem.description
          ? `<p style="color: #94a3b8; margin-bottom: ${isFeatured ? '1.5rem' : '1rem'}; line-height: 1.55; font-size: ${isFeatured ? '0.95rem' : '0.875rem'}; flex: 1;">${escapeHtml(classItem.description)}</p>`
          : '<div style="flex: 1;"></div>'}

        <div style="display: flex; margin-bottom: ${isFeatured ? '1.5rem' : '1rem'}; border: 1px solid rgba(255,255,255,0.06); border-radius: 0.5rem; overflow: hidden; background: rgba(0,0,0,0.15);">
          <div style="flex: 1; text-align: center; padding: 0.75rem 0.5rem; border-right: 1px solid rgba(255,255,255,0.06);">
            <div style="font-size: ${isFeatured ? '1.75rem' : '1.25rem'}; font-family: var(--font-mono); color: #f8fafc; font-weight: 700; line-height: 1;">${classItem.student_count || 0}</div>
            <div style="font-size: 0.65rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.25rem;">Enrolled</div>
          </div>
          <div style="flex: 1; text-align: center; padding: 0.75rem 0.5rem;">
            <div style="font-size: ${isFeatured ? '1.75rem' : '1.25rem'}; font-family: var(--font-mono); color: #f8fafc; font-weight: 700; line-height: 1;">${classItem.chapter_count || 0}</div>
            <div style="font-size: 0.65rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.25rem;">Modules</div>
          </div>
        </div>

        <div style="display: flex; gap: 0.5rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: ${isFeatured ? '1.25rem' : '0.85rem'};">
          <button
            class="btn btn-primary"
            style="flex: 1; font-size: 0.85rem; display: flex; align-items: center; justify-content: center; gap: 0.4rem;"
            onclick="viewClass('${escapeHtml(classItem.class_id)}')"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events:none;"><polyline points="9 18 15 12 9 6"/></svg>
            Open Class
          </button>
          <button
            class="btn btn-secondary"
            style="background: transparent; border-color: rgba(255,255,255,0.1); color: #94a3b8; font-size: 0.82rem; padding: 0.5rem 0.65rem; flex-shrink: 0;"
            onclick="copyClassCode('${escapeHtml(classItem.class_id)}')"
            title="Copy class code"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events:none;">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          </button>
          <button
            class="btn btn-secondary"
            onclick="deleteClass('${escapeHtml(classItem.class_id)}', '${escapeHtml(classItem.name)}')"
            title="Delete class"
            style="background: transparent; border-color: rgba(239,68,68,0.3); color: #ef4444; font-size: 0.82rem; padding: 0.5rem 0.65rem; flex-shrink: 0;"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="pointer-events:none;"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
          </button>
        </div>
      </div>
    </div>
    `;
  }).join('');

  // Card indicator hover effect
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

// Show create class modal (Sliding Drawer)
function showCreateClassModal() {
  document.getElementById('drawerOverlay').classList.add('visible');
  document.getElementById('createClassModal').classList.add('visible');
  document.getElementById('className').focus();
}

// Hide create class modal (Sliding Drawer)
function hideCreateClassModal() {
  document.getElementById('drawerOverlay').classList.remove('visible');
  document.getElementById('createClassModal').classList.remove('visible');
  document.getElementById('createClassForm').reset();
  document.getElementById('createClassError').style.display = 'none';
}

// Handle create class form submission
async function handleCreateClass(event) {
  event.preventDefault();

  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id) {
    alert('Please sign in to create a class');
    return;
  }

  const name = document.getElementById('className').value.trim();
  const classCode = document.getElementById('classCode').value.trim().toUpperCase();
  const description = document.getElementById('classDescription').value.trim();
  const errorDiv = document.getElementById('createClassError');

  if (!name) {
    errorDiv.textContent = 'Class name is required';
    errorDiv.style.display = 'block';
    return;
  }

  if (!classCode) {
    errorDiv.textContent = 'Class code/ID is required';
    errorDiv.style.display = 'block';
    return;
  }

  // Validate class code format (3-20 alphanumeric characters, hyphens, underscores)
  if (!/^[A-Za-z0-9_-]{3,20}$/.test(classCode)) {
    errorDiv.textContent = 'Class code must be 3-20 characters (letters, numbers, hyphens, underscores only)';
    errorDiv.style.display = 'block';
    return;
  }

  try {
    errorDiv.style.display = 'none';
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.textContent = 'Creating...';

    const response = await authFetch(`${window.API_BASE_URL}/classes`, {
      method: 'POST',
      body: JSON.stringify({
        class_code: classCode.toUpperCase(),
        name: name,
        description: description
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to create class');
    }

    // Success - reload classes and close modal
    hideCreateClassModal();
    loadClasses();

    // Show success message
    alert(`Class "${name}" created successfully! Class Code: ${data.class_id}`);

  } catch (error) {
    console.error('Error creating class:', error);
    errorDiv.textContent = error.message;
    errorDiv.style.display = 'block';
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = false;
    submitButton.textContent = 'Create Class';
  }
}

// View class (navigate to class management page)
function viewClass(classId) {
  window.location.href = `/professor-class?class_id=${encodeURIComponent(classId)}`;
}

// Copy class code to clipboard
function copyClassCode(classId) {
  navigator.clipboard.writeText(classId).then(() => {
    // Show temporary feedback
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    button.innerHTML = 'Copied';
    button.style.background = 'var(--color-success, #10b981)';
    setTimeout(() => {
      button.innerHTML = originalText;
      button.style.background = '';
    }, 2000);
  }).catch(err => {
    console.error('Failed to copy:', err);
    alert(`Class Code: ${classId}`);
  });
}

// Delete class with confirmation
async function deleteClass(classId, className) {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id) {
    alert('Please sign in to delete a class');
    return;
  }

  uiStates.showConfirmModal(
    `Are you sure you want to delete "${className}"? This will permanently delete all chapters, exercises, and student enrollments. This action cannot be undone.`,
    async function () {
      try {
        const response = await authFetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(classId)}`, {
          method: 'DELETE'
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || 'Failed to delete class');
        }

        // Reload classes to reflect deletion
        loadClasses();
        alert(`Class "${className}" has been deleted.`);

      } catch (error) {
        console.error('Error deleting class:', error);
        alert('Error deleting class: ' + error.message);
      }
    }
  );
}


// Close modal when clicking outside
document.addEventListener('click', function (event) {
  const modal = document.getElementById('createClassModal');
  if (event.target === modal) {
    hideCreateClassModal();
  }
});

// Close modal with Escape key
document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape') {
    hideCreateClassModal();
  }
});
