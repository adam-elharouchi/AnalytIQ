// Student Class View - View Class Details, Chapters, and Exercises
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
  const chaptersContainer = document.getElementById('chaptersContainer');
  
  try {
    loadingState.style.display = 'block';
    classHeader.style.display = 'none';
    chaptersContainer.style.display = 'none';
    
    // Load class details
    const classResponse = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(classId)}?user_id=${currentUser.user_id}`);
    const classData = await classResponse.json();
    
    if (!classResponse.ok) {
      throw new Error(classData.error || 'Failed to load class');
    }
    
    currentClassData = classData;
    renderClassHeader(classData);
    
    // Load chapters
    const chaptersResponse = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(classId)}/chapters?user_id=${currentUser.user_id}`);
    const chaptersData = await chaptersResponse.json();
    
    if (!chaptersResponse.ok) {
      throw new Error(chaptersData.error || 'Failed to load chapters');
    }
    
    loadingState.style.display = 'none';
    classHeader.style.display = 'block';
    chaptersContainer.style.display = 'block';
    
    renderChapters(chaptersData.chapters || []);
    
  } catch (error) {
    console.error('Error loading class:', error);
    loadingState.style.display = 'none';
    loadingState.innerHTML = `
      <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
      <h2 style="color: #222c3e; margin-bottom: 0.5rem;">Error Loading Class</h2>
      <p style="color: #64748b; margin-bottom: 1.5rem;">${error.message}</p>
      <button class="btn btn-primary" onclick="window.location.href='student-classes.html'">Back to Classes</button>
    `;
  }
}

// Render class header
function renderClassHeader(data) {
  document.getElementById('className').textContent = data.name || 'Unnamed Class';
  document.getElementById('classDescription').textContent = data.description || '';
  document.getElementById('professorName').textContent = data.professor_name || data.professor_email || 'Unknown';
  document.getElementById('chapterCountStat').textContent = data.chapter_count || 0;
  document.getElementById('exerciseCountStat').textContent = data.exercise_count || 0;
}

// Load exercises for a chapter
async function loadExercisesForChapter(chapterId) {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id) {
    console.error('No user found');
    return [];
  }
  
  try {
    const response = await fetch(`${window.API_BASE_URL}/chapters/${encodeURIComponent(chapterId)}/exercises?user_id=${currentUser.user_id}`);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to load exercises');
    }
    
    return data.exercises || [];
  } catch (error) {
    console.error('Error loading exercises:', error);
    return [];
  }
}

// Render chapters
async function renderChapters(chapters) {
  const chaptersList = document.getElementById('chaptersList');
  
  if (!chapters || chapters.length === 0) {
    chaptersList.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
        <p style="color: #64748b;">No chapters available yet.</p>
      </div>
    `;
    return;
  }
  
  let chaptersHTML = '';
  
  for (const chapter of chapters) {
    // Load exercises for this chapter
    const exercises = await loadExercisesForChapter(chapter.chapter_id);
    
    chaptersHTML += `
      <div class="chapter-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
          <div style="flex: 1;">
            <h3 style="margin: 0; color: #222c3e; font-size: 1.25rem;">${escapeHtml(chapter.title)}</h3>
            ${chapter.pdf_filename ? `
              <a href="Course Content/${escapeHtml(chapter.pdf_filename)}" target="_blank" style="color: #2569f4; text-decoration: none; font-size: 0.875rem; margin-top: 0.25rem; display: inline-flex; align-items: center; gap: 0.25rem;">
                📄 View PDF
              </a>
            ` : ''}
          </div>
        </div>
        
        ${exercises.length > 0 ? `
          <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;">
            <h4 style="margin: 0 0 1rem 0; color: #222c3e; font-size: 1rem;">Exercises (${exercises.length})</h4>
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              ${exercises.map((exercise, index) => `
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 1rem;">
                  <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <div style="flex: 1;">
                      <div style="font-weight: 600; color: #222c3e; margin-bottom: 0.25rem;">${escapeHtml(exercise.title)}</div>
                      <div style="font-size: 0.875rem; color: #64748b;">${escapeHtml(exercise.description || '')}</div>
                    </div>
                    <span style="background: ${getDifficultyColor(exercise.difficulty)}; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 600; text-transform: capitalize;">
                      ${escapeHtml(exercise.difficulty || 'medium')}
                    </span>
                  </div>
                  <button 
                    class="btn btn-primary" 
                    style="width: 100%; margin-top: 0.5rem;"
                    onclick="startExercise('${escapeHtml(exercise.exercise_id)}', '${escapeHtml(chapter.chapter_id)}', '${escapeHtml(exercise.title)}')"
                  >
                    Start Exercise
                  </button>
                </div>
              `).join('')}
            </div>
          </div>
        ` : `
          <div style="margin-top: 1rem; padding: 1rem; background: #f8fafc; border-radius: 0.375rem; text-align: center;">
            <p style="color: #64748b; font-size: 0.875rem; margin: 0;">No exercises available for this chapter yet.</p>
          </div>
        `}
      </div>
    `;
  }
  
  chaptersList.innerHTML = chaptersHTML;
  
  // Add hover effect
  const chapterCards = chaptersList.querySelectorAll('.chapter-card');
  chapterCards.forEach(card => {
    card.addEventListener('mouseenter', function() {
      this.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)';
    });
    card.addEventListener('mouseleave', function() {
      this.style.boxShadow = 'none';
    });
  });
}

// Get difficulty color
function getDifficultyColor(difficulty) {
  const diff = (difficulty || 'medium').toLowerCase();
  if (diff === 'easy') return '#10b981';
  if (diff === 'hard') return '#ef4444';
  return '#2569f4'; // medium
}

// Start exercise (navigate to practice playground)
function startExercise(exerciseId, chapterId, exerciseTitle) {
  // Navigate to practice playground with exercise data
  window.location.href = `practice-playground.html?exercise_id=${encodeURIComponent(exerciseId)}&chapter_id=${encodeURIComponent(chapterId)}&title=${encodeURIComponent(exerciseTitle)}`;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
