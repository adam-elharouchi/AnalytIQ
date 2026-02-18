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
    loadingState.style.display = 'block';
    emptyState.style.display = 'none';
    classesGrid.style.display = 'none';

    const response = await authFetch(`${window.API_BASE_URL}/classes/enrolled`);
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
      <h2 style="color: var(--color-dark); margin-bottom: 0.5rem;">Error Loading Classes</h2>
      <p style="color: #64748b; margin-bottom: 1.5rem;">${error.message}</p>
      <button class="btn btn-primary" onclick="loadEnrolledClasses()">Retry</button>
    `;
  }
}

// Render classes grid
function renderClasses(classes) {
  const classesGrid = document.getElementById('classesGrid');
  classesGrid.innerHTML = classes.map(classItem => `
    <div class="class-card" style="background: white; border: 1px solid var(--border-color); border-radius: 0.5rem; padding: 1.5rem; transition: box-shadow 0.2s;">
      <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
        <div style="flex: 1;">
          <h3 style="margin: 0; color: var(--color-dark); font-size: 1.25rem;">${escapeHtml(classItem.name)}</h3>
          <p style="color: #64748b; font-size: 0.875rem; margin-top: 0.25rem;">${escapeHtml(classItem.professor_name || '')}</p>
        </div>
      </div>
      
      ${classItem.description ? `<p style="color: #64748b; margin-bottom: 1rem; line-height: 1.5;">${escapeHtml(classItem.description)}</p>` : ''}
      
      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem; padding: 1rem; background: #f8fafc; border-radius: 0.375rem;">
        <div>
          <div style="font-size: 1.5rem; font-weight: 600; color: var(--color-primary);">${classItem.chapter_count || 0}</div>
          <div style="font-size: 0.875rem; color: #64748b;">Chapters</div>
        </div>
        <div>
          <div style="font-size: 1.5rem; font-weight: 600; color: var(--color-primary);">${classItem.student_count || 0}</div>
          <div style="font-size: 0.875rem; color: #64748b;">Students</div>
        </div>
      </div>
      
      <button 
        class="btn btn-primary" 
        style="width: 100%;"
        onclick="viewClass('${escapeHtml(classItem.class_id)}')"
      >
        View Class
      </button>
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

// Show join class modal
function showJoinClassModal() {
  const modal = document.getElementById('joinClassModal');
  modal.style.display = 'flex';
  document.getElementById('classCode').focus();

  // Transform input to uppercase as user types
  const classCodeInput = document.getElementById('classCode');
  classCodeInput.addEventListener('input', function () {
    this.value = this.value.toUpperCase();
  });
}

// Hide join class modal
function hideJoinClassModal() {
  const modal = document.getElementById('joinClassModal');
  modal.style.display = 'none';
  document.getElementById('joinClassForm').reset();
  document.getElementById('joinClassError').style.display = 'none';
}

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
    errorDiv.textContent = 'Please enter a valid class code (3-20 characters)';
    errorDiv.style.display = 'block';
    return;
  }

  try {
    errorDiv.style.display = 'none';
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.textContent = 'Joining...';

    const response = await authFetch(`${window.API_BASE_URL}/classes/enroll`, {
      method: 'POST',
      body: JSON.stringify({
        class_id: classCode
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to join class');
    }

    // Success - reload classes and close modal
    hideJoinClassModal();
    loadEnrolledClasses();

    // Show success message
    alert(`Successfully joined "${data.class_name}"!`);

  } catch (error) {
    console.error('Error joining class:', error);
    errorDiv.textContent = error.message;
    errorDiv.style.display = 'block';
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = false;
    submitButton.textContent = 'Join Class';
  }
}

// View class (navigate to student class view page)
function viewClass(classId) {
  window.location.href = `student-class.html?class_id=${encodeURIComponent(classId)}`;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Close modal when clicking outside
document.addEventListener('click', function (event) {
  const modal = document.getElementById('joinClassModal');
  if (event.target === modal) {
    hideJoinClassModal();
  }
});

// Close modal with Escape key
document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape') {
    hideJoinClassModal();
  }
});
