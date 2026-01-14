// Professor Class Management
// API_BASE_URL should be defined in api-helper.js

if (typeof window.API_BASE_URL === 'undefined') {
  window.API_BASE_URL = 'https://analytiq-qbfr.onrender.com/api';
}

let currentClassId = null;
let currentClassData = null;

// Get current user
function getCurrentUser() {
  try {
    const userStr = localStorage.getItem('currentUser');
    return userStr ? JSON.parse(userStr) : null;
  } catch (e) {
    return null;
  }
}

// Load class data
async function loadClassData(classId) {
  currentClassId = classId;
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id) {
    console.error('No user found');
    return;
  }
  
  const loadingState = document.getElementById('loadingState');
  const classHeader = document.getElementById('classHeader');
  const tabsContainer = document.getElementById('tabsContainer');
  
  try {
    loadingState.style.display = 'block';
    classHeader.style.display = 'none';
    tabsContainer.style.display = 'none';
    
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(classId)}?user_id=${currentUser.user_id}`);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to load class');
    }
    
    currentClassData = data;
    loadingState.style.display = 'none';
    classHeader.style.display = 'block';
    tabsContainer.style.display = 'block';
    
    // Render class header
    renderClassHeader(data);
    
    // Load default tab (chapters)
    switchTab('chapters');
    
  } catch (error) {
    console.error('Error loading class:', error);
    loadingState.innerHTML = `
      <div style="text-align: center; padding: 3rem;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
        <h2 style="color: #222c3e; margin-bottom: 0.5rem;">Error Loading Class</h2>
        <p style="color: #64748b; margin-bottom: 1.5rem;">${error.message}</p>
        <button class="btn btn-primary" onclick="window.location.href='professor-dashboard.html'">Back to Dashboard</button>
      </div>
    `;
  }
}

// Render class header
function renderClassHeader(data) {
  document.getElementById('className').textContent = data.name || 'Untitled Class';
  document.getElementById('classDescription').textContent = data.description || 'No description';
  document.getElementById('classCode').textContent = data.class_id || '';
  document.getElementById('studentCountStat').textContent = data.student_count || 0;
  document.getElementById('chapterCountStat').textContent = data.chapter_count || 0;
  document.getElementById('exerciseCountStat').textContent = data.exercise_count || 0;
}

// Switch tabs
function switchTab(tabName) {
  // Hide all tab contents
  document.querySelectorAll('.tab-content').forEach(tab => {
    tab.style.display = 'none';
  });
  
  // Remove active class from all tab buttons
  document.querySelectorAll('.login-tab').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Show selected tab content
  const tabContent = document.getElementById(`tabContent${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
  if (tabContent) {
    tabContent.style.display = 'block';
  }
  
  // Add active class to selected tab button
  const tabButton = document.getElementById(`tab${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
  if (tabButton) {
    tabButton.classList.add('active');
  }
  
  // Load tab data
  if (tabName === 'chapters') {
    loadChapters();
  } else if (tabName === 'students') {
    loadStudents();
  } else if (tabName === 'progress') {
    loadProgress();
  }
}

// Load chapters
async function loadChapters() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    return;
  }
  
  const chaptersList = document.getElementById('chaptersList');
  
  try {
    chaptersList.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading chapters...</div>';
    
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters?user_id=${currentUser.user_id}`);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to load chapters');
    }
    
    const chapters = data.chapters || [];
    
    if (chapters.length === 0) {
      chaptersList.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
          <p style="color: #64748b;">No chapters yet. Upload your first chapter to get started.</p>
        </div>
      `;
    } else {
      chaptersList.innerHTML = chapters.map(chapter => `
        <div class="chapter-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: start;">
          <div style="flex: 1;">
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
              <span style="background: #2569f4; color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.875rem; font-weight: 600;">Chapter ${chapter.chapter_number}</span>
              <h3 style="margin: 0; color: #222c3e; font-size: 1.25rem;">${escapeHtml(chapter.title)}</h3>
            </div>
            ${chapter.description ? `<p style="color: #64748b; margin-bottom: 0.5rem;">${escapeHtml(chapter.description)}</p>` : ''}
            <div style="font-size: 0.875rem; color: #64748b;">
              <span>📄 ${escapeHtml(chapter.pdf_filename || 'PDF file')}</span>
              ${chapter.created_at ? `<span style="margin-left: 1rem;">Uploaded: ${new Date(chapter.created_at).toLocaleDateString()}</span>` : ''}
            </div>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            ${chapter.pdf_url ? `<a href="${escapeHtml(chapter.pdf_url)}" target="_blank" class="btn btn-primary" style="text-decoration: none;">View PDF</a>` : ''}
          </div>
        </div>
      `).join('');
    }
  } catch (error) {
    console.error('Error loading chapters:', error);
    chaptersList.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: #fee2e2; border: 1px solid #ef4444; border-radius: 0.5rem;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
        <p style="color: #991b1b;">Error loading chapters: ${escapeHtml(error.message)}</p>
        <button class="btn btn-primary" onclick="loadChapters()" style="margin-top: 1rem;">Retry</button>
      </div>
    `;
  }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Load students
async function loadStudents() {
  // TODO: Implement when student enrollment APIs are ready
  const studentsList = document.getElementById('studentsList');
  const studentsCount = document.getElementById('studentsCount');
  
  // For now, show empty state
  studentsList.innerHTML = `
    <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
      <div style="font-size: 3rem; margin-bottom: 1rem;">👥</div>
      <p style="color: #64748b;">Student enrollment coming soon.</p>
    </div>
  `;
  studentsCount.textContent = '0 students';
}

// Load progress
async function loadProgress() {
  // TODO: Implement when progress APIs are ready
  const progressOverview = document.getElementById('progressOverview');
  progressOverview.innerHTML = `
    <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
      <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
      <p style="color: #64748b;">Progress tracking coming soon.</p>
    </div>
  `;
}

// Show upload chapter modal
function showUploadChapterModal() {
  const modal = document.getElementById('uploadChapterModal');
  modal.style.display = 'flex';
  document.getElementById('chapterTitle').focus();
}

// Hide upload chapter modal
function hideUploadChapterModal() {
  const modal = document.getElementById('uploadChapterModal');
  modal.style.display = 'none';
  document.getElementById('uploadChapterForm').reset();
  document.getElementById('uploadChapterError').style.display = 'none';
}

// Handle upload chapter form submission
async function handleUploadChapter(event) {
  event.preventDefault();
  
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    alert('Please sign in to upload chapters');
    return;
  }
  
  const errorDiv = document.getElementById('uploadChapterError');
  errorDiv.style.display = 'none';
  
  const title = document.getElementById('chapterTitle').value.trim();
  const description = document.getElementById('chapterDescription').value.trim();
  const pdfFile = document.getElementById('chapterPDF').files[0];
  const exerciseMode = document.querySelector('input[name="exerciseMode"]:checked')?.value || 'auto';
  
  if (!title) {
    errorDiv.textContent = 'Chapter title is required';
    errorDiv.style.display = 'block';
    return;
  }
  
  if (!pdfFile) {
    errorDiv.textContent = 'Please select a PDF file';
    errorDiv.style.display = 'block';
    return;
  }
  
  // Check file type
  if (!pdfFile.name.toLowerCase().endsWith('.pdf')) {
    errorDiv.textContent = 'Please select a PDF file';
    errorDiv.style.display = 'block';
    return;
  }
  
  try {
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.textContent = 'Uploading...';
    
    // Create FormData
    const formData = new FormData();
    formData.append('user_id', currentUser.user_id);
    formData.append('title', title);
    formData.append('description', description);
    formData.append('pdf_file', pdfFile);
    formData.append('exercise_mode', exerciseMode);
    
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters`, {
      method: 'POST',
      body: formData
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to upload chapter');
    }
    
    // Success - reload chapters and close modal
    hideUploadChapterModal();
    loadChapters();
    
    // Update chapter count in header
    if (currentClassData) {
      currentClassData.chapter_count = (currentClassData.chapter_count || 0) + 1;
      renderClassHeader(currentClassData);
    }
    
    // Show success message
    alert(`Chapter "${title}" uploaded successfully!`);
    
  } catch (error) {
    console.error('Error uploading chapter:', error);
    errorDiv.textContent = error.message;
    errorDiv.style.display = 'block';
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = false;
    submitButton.textContent = 'Upload Chapter';
  }
}

// Show edit class modal
function showEditClassModal() {
  if (!currentClassData) return;
  
  const modal = document.getElementById('editClassModal');
  document.getElementById('editClassName').value = currentClassData.name || '';
  document.getElementById('editClassDescription').value = currentClassData.description || '';
  modal.style.display = 'flex';
}

// Hide edit class modal
function hideEditClassModal() {
  const modal = document.getElementById('editClassModal');
  modal.style.display = 'none';
  document.getElementById('editClassError').style.display = 'none';
}

// Handle edit class form submission
async function handleEditClass(event) {
  event.preventDefault();
  
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    alert('Please sign in to edit class');
    return;
  }
  
  const name = document.getElementById('editClassName').value.trim();
  const description = document.getElementById('editClassDescription').value.trim();
  const errorDiv = document.getElementById('editClassError');
  
  if (!name) {
    errorDiv.textContent = 'Class name is required';
    errorDiv.style.display = 'block';
    return;
  }
  
  try {
    errorDiv.style.display = 'none';
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.textContent = 'Saving...';
    
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: currentUser.user_id,
        name: name,
        description: description
      })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to update class');
    }
    
    // Success - reload class data
    hideEditClassModal();
    loadClassData(currentClassId);
    
  } catch (error) {
    console.error('Error updating class:', error);
    errorDiv.textContent = error.message;
    errorDiv.style.display = 'block';
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = false;
    submitButton.textContent = 'Save Changes';
  }
}

// Copy class code to clipboard
function copyClassCodeToClipboard() {
  if (!currentClassData || !currentClassData.class_id) return;
  
  navigator.clipboard.writeText(currentClassData.class_id).then(() => {
    alert(`Class code "${currentClassData.class_id}" copied to clipboard!`);
  }).catch(err => {
    console.error('Failed to copy:', err);
    alert(`Class Code: ${currentClassData.class_id}`);
  });
}

// Close modals when clicking outside
document.addEventListener('click', function(event) {
  const uploadModal = document.getElementById('uploadChapterModal');
  const editModal = document.getElementById('editClassModal');
  
  if (event.target === uploadModal) {
    hideUploadChapterModal();
  }
  if (event.target === editModal) {
    hideEditClassModal();
  }
});

// Close modals with Escape key
document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') {
    hideUploadChapterModal();
    hideEditClassModal();
  }
});
