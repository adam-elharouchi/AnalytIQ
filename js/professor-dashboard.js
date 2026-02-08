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

    if (!data.classes || data.classes.length === 0) {
      emptyState.style.display = 'block';
      classesGrid.style.display = 'none';
    } else {
      emptyState.style.display = 'none';
      classesGrid.style.display = 'grid';
      renderClasses(data.classes);
    }
  } catch (error) {
    console.error('Error loading classes:', error);
    loadingState.style.display = 'none';
    emptyState.style.display = 'block';
    emptyState.innerHTML = `
      <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
      <h2 style="color: #222c3e; margin-bottom: 0.5rem;">Error Loading Classes</h2>
      <p style="color: #64748b; margin-bottom: 1.5rem;">${error.message}</p>
      <button class="btn btn-primary" onclick="loadClasses()">Retry</button>
    `;
  }
}

// Render classes grid
function renderClasses(classes) {
  const classesGrid = document.getElementById('classesGrid');
  classesGrid.innerHTML = classes.map(classItem => `
    <div class="class-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 1.5rem; transition: box-shadow 0.2s;">
      <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
        <h3 style="margin: 0; color: #222c3e; font-size: 1.25rem;">${escapeHtml(classItem.name)}</h3>
        <span style="background: #2569f4; color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.875rem; font-weight: 600;">${escapeHtml(classItem.class_id)}</span>
      </div>
      
      ${classItem.description ? `<p style="color: #64748b; margin-bottom: 1rem; line-height: 1.5;">${escapeHtml(classItem.description)}</p>` : ''}
      
      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem; padding: 1rem; background: #f8fafc; border-radius: 0.375rem;">
        <div>
          <div style="font-size: 1.5rem; font-weight: 600; color: #2569f4;">${classItem.student_count || 0}</div>
          <div style="font-size: 0.875rem; color: #64748b;">Students</div>
        </div>
        <div>
          <div style="font-size: 1.5rem; font-weight: 600; color: #2569f4;">${classItem.chapter_count || 0}</div>
          <div style="font-size: 0.875rem; color: #64748b;">Chapters</div>
        </div>
      </div>
      
      <div style="display: flex; gap: 0.5rem;">
        <button 
          class="btn btn-primary" 
          style="flex: 1;"
          onclick="viewClass('${escapeHtml(classItem.class_id)}')"
        >
          View Class
        </button>
        <button 
          class="btn btn-secondary" 
          onclick="copyClassCode('${escapeHtml(classItem.class_id)}')"
          title="Copy Class Code"
        >
          📋
        </button>
        <button 
          class="btn btn-secondary" 
          onclick="deleteClass('${escapeHtml(classItem.class_id)}', '${escapeHtml(classItem.name)}')"
          title="Delete Class"
          style="color: #dc2626;"
        >
          🗑️
        </button>
      </div>
    </div>
  `).join('');

  // Add hover effect
  const classCards = classesGrid.querySelectorAll('.class-card');
  classCards.forEach(card => {
    card.addEventListener('mouseenter', function () {
      this.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)';
    });
    card.addEventListener('mouseleave', function () {
      this.style.boxShadow = 'none';
    });
  });
}

// Show create class modal
function showCreateClassModal() {
  const modal = document.getElementById('createClassModal');
  modal.style.display = 'flex';
  document.getElementById('className').focus();
}

// Hide create class modal
function hideCreateClassModal() {
  const modal = document.getElementById('createClassModal');
  modal.style.display = 'none';
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
  window.location.href = `professor-class.html?class_id=${encodeURIComponent(classId)}`;
}

// Copy class code to clipboard
function copyClassCode(classId) {
  navigator.clipboard.writeText(classId).then(() => {
    // Show temporary feedback
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    button.innerHTML = '✓';
    button.style.background = '#10b981';
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

  // Confirm deletion
  const confirmed = confirm(`Are you sure you want to delete "${className}"?\n\nThis will permanently delete:\n• All chapters\n• All exercises\n• All student enrollments\n\nThis action cannot be undone.`);

  if (!confirmed) return;

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
