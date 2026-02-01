// Professor Class Management
// API_BASE_URL should be defined in api-helper.js

// API_BASE_URL is defined in api-helper.js

let currentClassId = null;
let currentClassData = null;
let loadedResources = []; // Store loaded resources for edit functionality

// Performance optimization: Cache for API data
const dataCache = {
  chapters: null,
  exercises: {},
  students: null,
  progress: null,
  totalExercises: null,
  lastFetch: {},
  ttl: 30000, // 30 second cache TTL

  isValid(key) {
    const lastFetch = this.lastFetch[key];
    return lastFetch && (Date.now() - lastFetch) < this.ttl;
  },

  set(key, data) {
    if (key === 'chapters') this.chapters = data;
    else if (key === 'students') this.students = data;
    else if (key === 'progress') this.progress = data;
    else if (key.startsWith('exercises_')) this.exercises[key] = data;
    this.lastFetch[key] = Date.now();
  },

  get(key) {
    if (key === 'chapters') return this.chapters;
    if (key === 'students') return this.students;
    if (key === 'progress') return this.progress;
    if (key.startsWith('exercises_')) return this.exercises[key];
    return null;
  },

  clear() {
    this.chapters = null;
    this.exercises = {};
    this.students = null;
    this.progress = null;
    this.totalExercises = null;
    this.lastFetch = {};
  }
};

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
  document.querySelectorAll('.tab-button').forEach(btn => {
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
  } else if (tabName === 'exercises') {
    loadExercises();
  } else if (tabName === 'resources') {
    loadResources();
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
              <span>📄 ${escapeHtml((chapter.pdf_filename || 'PDF file').replace(/^[A-Za-z0-9]+_\d+_/, ''))}</span>
              ${chapter.created_at ? `<span style="margin-left: 1rem;">Uploaded: ${new Date(chapter.created_at).toLocaleDateString()}</span>` : ''}
            </div>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            ${chapter.pdf_url || chapter.pdf_filename ? `<a href="chapter-view.html?chapter_id=${encodeURIComponent(chapter.chapter_id)}&class_id=${encodeURIComponent(currentClassId)}" class="btn btn-primary" style="text-decoration: none;">View PDF</a>` : ''}
            <button class="btn btn-secondary" onclick="showEditChapterModal('${chapter.chapter_id}')" style="background: white; color: #222c3e; border: 1px solid #cbd5e1; padding: 0.5rem 0.75rem;">✏️</button>
            <button class="btn btn-secondary" onclick="showDeleteChapterModal('${chapter.chapter_id}')" style="background: white; color: #ef4444; border: 1px solid #fca5a5; padding: 0.5rem 0.75rem;">🗑️</button>
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


// Load students with exercise progress
async function loadStudents() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) return;

  const studentsList = document.getElementById('studentsList');
  const studentsCount = document.getElementById('studentsCount');

  try {
    studentsList.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading students...</div>';

    // Fetch students
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/students?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error);

    const students = data.students || [];
    studentsCount.textContent = `${students.length} students`;

    // Fetch progress data for the class
    let progressData = {};
    try {
      const progressResponse = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/progress?user_id=${currentUser.user_id}`);
      if (progressResponse.ok) {
        const pd = await progressResponse.json();
        // Map progress by student ID
        (pd.students || []).forEach(s => {
          const total = Object.keys(s.progress || {}).length;
          const completed = Object.values(s.progress || {}).filter(p => p.completed).length;
          const avgScore = total > 0 ? Math.round(Object.values(s.progress || {}).reduce((acc, p) => acc + (p.score || 0), 0) / total) : 0;
          progressData[s.student_id] = { total, completed, avgScore };
        });
      }
    } catch (e) {
      console.warn('Could not load progress:', e);
    }

    // Get total exercises count (use cache to avoid slow sequential API calls)
    let totalExercises = dataCache.totalExercises || 0;
    if (!totalExercises && !dataCache.isValid('totalExercises')) {
      try {
        const chaptersResponse = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters?user_id=${currentUser.user_id}`);
        if (chaptersResponse.ok) {
          const chaptersData = await chaptersResponse.json();
          const chapters = chaptersData.chapters || [];
          // Fetch all exercises in parallel for speed
          const exercisePromises = chapters.map(chapter =>
            fetch(`${window.API_BASE_URL}/chapters/${encodeURIComponent(chapter.chapter_id)}/exercises?user_id=${currentUser.user_id}`)
              .then(r => r.ok ? r.json() : { exercises: [] })
              .catch(() => ({ exercises: [] }))
          );
          const exerciseResults = await Promise.all(exercisePromises);
          totalExercises = exerciseResults.reduce((sum, r) => sum + (r.exercises || []).length, 0);
          dataCache.totalExercises = totalExercises;
          dataCache.lastFetch['totalExercises'] = Date.now();
        }
      } catch (e) {
        console.warn('Could not count exercises:', e);
      }
    }

    if (students.length === 0) {
      studentsList.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">👥</div>
          <p style="color: #64748b;">No students enrolled yet.</p>
        </div>
      `;
    } else {
      studentsList.innerHTML = `
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; min-width: 700px;">
            <thead style="background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
              <tr>
                <th style="text-align: left; padding: 1rem; color: #64748b; font-weight: 600;">Name</th>
                <th style="text-align: left; padding: 1rem; color: #64748b; font-weight: 600;">Email</th>
                <th style="text-align: left; padding: 1rem; color: #64748b; font-weight: 600;">Exercise Progress</th>
                <th style="text-align: left; padding: 1rem; color: #64748b; font-weight: 600;">Enrolled Date</th>
              </tr>
            </thead>
            <tbody>
              ${students.map(student => {
        const progress = progressData[student.user_id] || { completed: 0, avgScore: 0 };
        const percentage = totalExercises > 0 ? Math.round((progress.completed / totalExercises) * 100) : 0;
        const barColor = percentage >= 80 ? '#10b981' : percentage >= 50 ? '#f59e0b' : '#64748b';
        return `
                <tr style="border-bottom: 1px solid #e2e8f0;">
                  <td style="padding: 1rem; color: #222c3e; font-weight: 500;">${escapeHtml(student.name)}</td>
                  <td style="padding: 1rem; color: #64748b;">${escapeHtml(student.email)}</td>
                  <td style="padding: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                      <div style="flex: 1; background: #e2e8f0; border-radius: 0.5rem; height: 8px; overflow: hidden;">
                        <div style="width: ${percentage}%; height: 100%; background: ${barColor}; transition: width 0.3s;"></div>
                      </div>
                      <span style="font-size: 0.875rem; color: #64748b; min-width: 80px;">${progress.completed}/${totalExercises} (${percentage}%)</span>
                    </div>
                    ${progress.avgScore > 0 ? `<div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">Avg Score: ${progress.avgScore}%</div>` : ''}
                  </td>
                  <td style="padding: 1rem; color: #64748b;">${new Date(student.enrolled_at).toLocaleDateString()}</td>
                </tr>
              `;
      }).join('')}
            </tbody>
          </table>
        </div>
      `;
    }
  } catch (error) {
    console.error('Error loading students:', error);
    studentsList.innerHTML = `<div class="error-message">Error loading students: ${escapeHtml(error.message)}</div>`;
  }
}

// Load progress
async function loadProgress() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) return;

  const progressOverview = document.getElementById('progressOverview');

  try {
    progressOverview.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading progress...</div>';

    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/progress?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error);

    const { students, exercises } = data;

    if (students.length === 0) {
      progressOverview.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
          <p style="color: #64748b;">No student data available yet.</p>
        </div>
      `;
      return;
    }

    if (exercises.length === 0) {
      progressOverview.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <p style="color: #64748b;">No exercises defined yet.</p>
        </div>
      `;
      return;
    }

    // Render Progress Table
    // Modified to target specific container instead of overwriting everything
    const tableContainer = document.getElementById('progressTableContainer');
    tableContainer.innerHTML = `
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; min-width: 800px;">
          <thead style="background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
            <tr>
              <th style="text-align: left; padding: 1rem; position: sticky; left: 0; background: #f8fafc; z-index: 10;">Student</th>
              ${exercises.map(ex => `
                <th style="padding: 1rem; text-align: center; min-width: 100px;">
                  <div style="font-size: 0.875rem; color: #64748b;">${escapeHtml(ex.title)}</div>
                </th>
              `).join('')}
            </tr>
          </thead>
          <tbody>
            ${students.map(student => `
              <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 1rem; font-weight: 500; position: sticky; left: 0; background: white; border-right: 1px solid #e2e8f0;">${escapeHtml(student.name)}</td>
                ${exercises.map(ex => {
      const progress = student.progress[ex.id];
      if (!progress) return '<td style="text-align: center; color: #cbd5e1;">-</td>';
      const color = progress.completed ? '#10b981' : '#f59e0b';
      return `
                    <td style="text-align: center;">
                      <div style="color: ${color}; font-weight: 600;">${progress.score}%</div>
                      ${progress.completed ? '<div style="font-size: 0.75rem; color: #10b981;">Done</div>' : ''}
                    </td>
                  `;
    }).join('')}
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    // Populate leaderboard exercise dropdown
    const lbSelect = document.getElementById('leaderboardExerciseSelect');
    if (lbSelect) {
      lbSelect.innerHTML = '<option value="">-- Choose an Exercise --</option>';
      exercises.forEach(ex => {
        const opt = document.createElement('option');
        opt.value = ex.id;
        opt.textContent = ex.title;
        lbSelect.appendChild(opt);
      });
    }

  } catch (error) {
    console.error('Error loading progress:', error);
    const tableContainer = document.getElementById('progressTableContainer');
    if (tableContainer) tableContainer.innerHTML = `<div class="error-message">Error loading progress: ${escapeHtml(error.message)}</div>`;
  }
}

// Switch between progress views (Table vs Leaderboards)
function switchProgressView(viewName) {
  // Hide all containers
  document.getElementById('progressTableContainer').style.display = 'none';
  document.getElementById('avgLeaderboardContainer').style.display = 'none';
  document.getElementById('exLeaderboardContainer').style.display = 'none';

  // Reset tabs
  document.querySelectorAll('.sub-tab-button').forEach(btn => btn.classList.remove('active'));

  // Show selected
  if (viewName === 'table') {
    document.getElementById('progressTableContainer').style.display = 'block';
    document.getElementById('subTabTable').classList.add('active');
  } else if (viewName === 'avgLeaderboard') {
    document.getElementById('avgLeaderboardContainer').style.display = 'block';
    document.getElementById('subTabAvg').classList.add('active');
    loadAvgLeaderboard();
  } else if (viewName === 'exLeaderboard') {
    document.getElementById('exLeaderboardContainer').style.display = 'block';
    document.getElementById('subTabEx').classList.add('active');
  }
}

// Load Average Leaderboard
async function loadAvgLeaderboard() {
  const container = document.getElementById('avgLeaderboardContainer');
  container.innerHTML = '<div style="text-align: center; padding: 2rem;">Loading leaderboard...</div>';

  try {
    const currentUser = getCurrentUser();
    if (!currentUser) return;

    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/leaderboard/average?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error);

    const leaderboard = data.leaderboard || [];

    if (leaderboard.length === 0) {
      container.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">No data available for leaderboard.</div>';
      return;
    }

    container.innerHTML = `
            <div style="background: white; border-radius: 0.5rem; border: 1px solid #e2e8f0; overflow: hidden; max-width: 800px; margin: 0 auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
                         <tr>
                            <th style="padding: 1rem; text-align: center; width: 60px;">Rank</th>
                            <th style="padding: 1rem; text-align: left;">Student</th>
                            <th style="padding: 1rem; text-align: center;">Exercises Completed</th>
                            <th style="padding: 1rem; text-align: right;">Average Score</th>
                         </tr>
                    </thead>
                    <tbody>
                        ${leaderboard.map(student => `
                            <tr style="border-bottom: 1px solid #e2e8f0;">
                                <td style="padding: 1rem; text-align: center; font-weight: bold; color: ${student.rank <= 3 ? '#eab308' : '#64748b'};">
                                    ${student.rank === 1 ? '🥇' : student.rank === 2 ? '🥈' : student.rank === 3 ? '🥉' : student.rank}
                                </td>
                                <td style="padding: 1rem; font-weight: 500;">${escapeHtml(student.name)}</td>
                                <td style="padding: 1rem; text-align: center;">${student.exercises_completed}</td>
                                <td style="padding: 1rem; text-align: right; font-weight: 600; color: #2569f4;">${student.average_score}%</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

  } catch (error) {
    console.error("Error loading avg leaderboard", error);
    container.innerHTML = `<div class="error-message">Error: ${escapeHtml(error.message)}</div>`;
  }
}

// Load Exercise Leaderboard
async function loadExerciseLeaderboard(exerciseId) {
  const container = document.getElementById('exLeaderboardContent');
  if (!exerciseId) {
    container.innerHTML = '<div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;"><p style="color: #64748b;">Select an exercise above to see the leaderboard.</p></div>';
    return;
  }

  container.innerHTML = '<div style="text-align: center; padding: 2rem;">Loading leaderboard...</div>';

  try {
    const currentUser = getCurrentUser();
    if (!currentUser) return;

    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/leaderboard/exercise/${exerciseId}?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error);

    const leaderboard = data.leaderboard || [];

    if (leaderboard.length === 0) {
      container.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">No submissions yet for this exercise.</div>';
      return;
    }

    container.innerHTML = `
            <div style="background: white; border-radius: 0.5rem; border: 1px solid #e2e8f0; overflow: hidden; max-width: 800px; margin: 0 auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
                         <tr>
                            <th style="padding: 1rem; text-align: center; width: 60px;">Rank</th>
                            <th style="padding: 1rem; text-align: left;">Student</th>
                            <th style="padding: 1rem; text-align: right;">Best Score</th>
                            <th style="padding: 1rem; text-align: right;">Submitted</th>
                         </tr>
                    </thead>
                    <tbody>
                        ${leaderboard.map(student => `
                            <tr style="border-bottom: 1px solid #e2e8f0;">
                                <td style="padding: 1rem; text-align: center; font-weight: bold; color: ${student.rank <= 3 ? '#eab308' : '#64748b'};">
                                    ${student.rank === 1 ? '🥇' : student.rank === 2 ? '🥈' : student.rank === 3 ? '🥉' : student.rank}
                                </td>
                                <td style="padding: 1rem; font-weight: 500;">${escapeHtml(student.name)}</td>
                                <td style="padding: 1rem; text-align: right; font-weight: 600; color: #2569f4;">${student.score}%</td>
                                <td style="padding: 1rem; text-align: right; color: #64748b; font-size: 0.875rem;">${student.submitted_at ? new Date(student.submitted_at).toLocaleDateString() : '-'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

  } catch (error) {
    console.error("Error loading exercise leaderboard", error);
    container.innerHTML = `<div class="error-message">Error: ${escapeHtml(error.message)}</div>`;
  }
}

// Load exercises
async function loadExercises() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    return;
  }

  const exercisesList = document.getElementById('exercisesList');

  try {
    exercisesList.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading exercises...</div>';

    // First, get all chapters to group exercises by chapter
    const chaptersResponse = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters?user_id=${currentUser.user_id}`);
    const chaptersData = await chaptersResponse.json();

    if (!chaptersResponse.ok) {
      throw new Error(chaptersData.error || 'Failed to load chapters');
    }

    const chapters = chaptersData.chapters || [];

    if (chapters.length === 0) {
      exercisesList.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">💪</div>
          <p style="color: #64748b;">No chapters found. Upload chapters to generate exercises.</p>
        </div>
      `;
      return;
    }

    // Load exercises for each chapter
    let allExercises = [];
    for (const chapter of chapters) {
      try {
        const exercisesResponse = await fetch(`${window.API_BASE_URL}/chapters/${encodeURIComponent(chapter.chapter_id)}/exercises?user_id=${currentUser.user_id}`);
        if (exercisesResponse.ok) {
          const exercisesData = await exercisesResponse.json();
          const exercises = exercisesData.exercises || [];
          exercises.forEach(ex => {
            ex.chapter_title = chapter.title;
            ex.chapter_id = chapter.chapter_id;
          });
          allExercises = allExercises.concat(exercises);
        }
      } catch (err) {
        console.warn(`Failed to load exercises for chapter ${chapter.chapter_id}:`, err);
      }
    }

    if (allExercises.length === 0) {
      exercisesList.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">💪</div>
          <p style="color: #64748b;">No exercises found. Exercises will be auto-generated when you upload chapters with auto-generation enabled, or create them manually.</p>
        </div>
      `;
    } else {
      // Group by chapter
      const exercisesByChapter = {};
      allExercises.forEach(ex => {
        if (!exercisesByChapter[ex.chapter_id]) {
          exercisesByChapter[ex.chapter_id] = {
            chapter_title: ex.chapter_title,
            chapter_id: ex.chapter_id,
            exercises: []
          };
        }
        exercisesByChapter[ex.chapter_id].exercises.push(ex);
      });

      // Render in practice grid style, grouped by chapter
      exercisesList.innerHTML = `
        <div class="practice-grid">
          ${Object.keys(exercisesByChapter).map(chapterId => {
        const chapterData = exercisesByChapter[chapterId];
        return `
              <div class="chapter-section" style="grid-column: 1 / -1; margin-bottom: 2rem;">
                <h2 style="margin-top: 2rem; margin-bottom: 0.5rem; color: #222c3e; font-size: 1.75rem; border-bottom: 2px solid #2569f4; padding-bottom: 0.5rem;">${escapeHtml(chapterData.chapter_title)}</h2>
              </div>
              ${chapterData.exercises.map(exercise => `
                <div class="practice-card">
                  <div class="practice-header">
                    <h2>${escapeHtml(exercise.title)}</h2>
                    <span class="difficulty-badge ${exercise.difficulty || 'medium'}">${escapeHtml((exercise.difficulty || 'medium').charAt(0).toUpperCase() + (exercise.difficulty || 'medium').slice(1))}</span>
                  </div>
                  <p class="practice-description">${exercise.description ? escapeHtml(exercise.description) : 'Practice exercise from ' + escapeHtml(chapterData.chapter_title)}</p>
                  <div class="practice-progress" style="margin: 1rem 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                    </div>
                  </div>
                  <div class="practice-actions">
                    <button class="btn btn-primary" onclick="startExerciseFromClass('${escapeHtml(exercise.exercise_id)}', '${escapeHtml(exercise.chapter_id)}', '${escapeHtml(exercise.title)}')">Start Exercise</button>
                    <button class="btn btn-secondary" onclick="editExercise('${escapeHtml(exercise.exercise_id)}')" style="margin-left: 0.5rem;">✏️ Edit</button>
                    <button class="btn btn-secondary" onclick="deleteExercise('${escapeHtml(exercise.exercise_id)}', '${escapeHtml(exercise.title)}')" style="margin-left: 0.5rem; color: #dc2626;">🗑️ Delete</button>
                  </div>
                </div>
              `).join('')}
            `;
      }).join('')}
        </div>
      `;
    }
  } catch (error) {
    console.error('Error loading exercises:', error);
    exercisesList.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: #fee2e2; border: 1px solid #ef4444; border-radius: 0.5rem;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
        <p style="color: #991b1b;">Error loading exercises: ${escapeHtml(error.message)}</p>
        <button class="btn btn-primary" onclick="loadExercises()" style="margin-top: 1rem;">Retry</button>
      </div>
    `;
  }
}

// Show create exercise modal
async function showCreateExerciseModal() {
  const modal = document.getElementById('createExerciseModal');
  const modalTitle = modal.querySelector('h2');
  const submitBtn = modal.querySelector('button[type="submit"]');
  const chapterSelect = document.getElementById('exerciseChapter');

  // Reset to Create Mode
  modal.dataset.mode = 'create';
  delete modal.dataset.exerciseId;
  modalTitle.textContent = "Create New Exercise";
  submitBtn.textContent = "Create Exercise";
  document.getElementById('createExerciseForm').reset();

  // Load chapters for the select dropdown
  await loadChapterOptions();

  modal.style.display = 'flex';
}

// Hide create exercise modal
function hideCreateExerciseModal() {
  const modal = document.getElementById('createExerciseModal');
  const form = document.getElementById('createExerciseForm');
  const errorDiv = document.getElementById('createExerciseError');

  modal.style.display = 'none';
  form.reset();
  errorDiv.style.display = 'none';
  errorDiv.textContent = '';
}

// Handle create exercise form submission
async function handleCreateExercise(event) {
  event.preventDefault();

  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    alert('Error: User not logged in');
    return;
  }

  const chapterId = document.getElementById('exerciseChapter').value;
  const title = document.getElementById('exerciseTitle').value.trim();
  const description = document.getElementById('exerciseDescription').value.trim();
  const difficulty = document.getElementById('exerciseDifficulty').value;
  const solutionCode = document.getElementById('exerciseSolution').value.trim();
  const fileInput = document.getElementById('exerciseFile');
  const exerciseFile = fileInput && fileInput.files.length > 0 ? fileInput.files[0] : null;

  if (!chapterId || !title) {
    showCreateExerciseError('Please fill in all required fields');
    return;
  }

  const errorDiv = document.getElementById('createExerciseError');
  errorDiv.style.display = 'none';

  try {
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;

    let url, method, requestOptions;
    const modal = document.getElementById('createExerciseModal');
    const isEdit = modal.dataset.mode === 'edit';

    if (isEdit) {
      const exerciseId = modal.dataset.exerciseId;
      url = `${window.API_BASE_URL}/exercises/${exerciseId}`;
      method = 'PUT';
      submitButton.textContent = 'Updating...';

      // For edit, use JSON (file changes not supported in edit mode)
      requestOptions = {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: currentUser.user_id,
          title: title,
          description: description,
          difficulty: difficulty,
          solution_code: solutionCode
        })
      };
    } else {
      url = `${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters/${encodeURIComponent(chapterId)}/exercises`;
      method = 'POST';
      submitButton.textContent = 'Creating...';

      // Use FormData if file is attached, otherwise JSON
      if (exerciseFile) {
        const formData = new FormData();
        formData.append('user_id', currentUser.user_id);
        formData.append('title', title);
        formData.append('description', description);
        formData.append('difficulty', difficulty);
        formData.append('solution_code', solutionCode);
        formData.append('exercise_file', exerciseFile);

        requestOptions = {
          method: method,
          body: formData
        };
      } else {
        requestOptions = {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: currentUser.user_id,
            title: title,
            description: description,
            difficulty: difficulty,
            solution_code: solutionCode
          })
        };
      }
    }

    const response = await fetch(url, requestOptions);

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to save exercise');
    }

    // Success - close modal and refresh exercises list
    hideCreateExerciseModal();
    await loadExercises();

    // Show success message
    const exercisesList = document.getElementById('exercisesList');
    const successMsg = document.createElement('div');
    successMsg.style.cssText = 'padding: 1rem; margin-bottom: 1rem; background: #d1fae5; color: #065f46; border-radius: 0.5rem; border: 1px solid #10b981;';
    successMsg.textContent = isEdit ? '✓ Exercise updated successfully!' : '✓ Exercise created successfully!';
    exercisesList.insertBefore(successMsg, exercisesList.firstChild);

    setTimeout(() => {
      successMsg.remove();
    }, 3000);

  } catch (error) {
    console.error('Error saving exercise:', error);
    showCreateExerciseError(error.message || 'Failed to save exercise. Please try again.');

    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = false;
    // Re-select modal as it might not be in scope if not passed
    const modal = document.getElementById('createExerciseModal');
    submitButton.textContent = (modal && modal.dataset.mode === 'edit') ? 'Update Exercise' : 'Create Exercise';
  }
}

// Show error in create exercise modal
function showCreateExerciseError(message) {
  const errorDiv = document.getElementById('createExerciseError');
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
}


function viewExerciseSolution(exerciseId) {
  alert(`View solution for exercise ${exerciseId} - functionality coming soon.`);
}

// Edit exercise - opens modal with existing data
async function editExercise(exerciseId) {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentClassId) return;

  try {
    // Find the exercise in the DOM or fetch it
    // We can fetch details from the API to be sure
    const chapterId = document.querySelector(`button[onclick*="'${exerciseId}'"]`).getAttribute('onclick').match(/'([^']+)', '([^']+)'/)[2]; // Hacky, better to fetch

    // Better: Fetch specific exercise details. Since we don't have a direct GET /exercises/:id, we use the chapter list or iterate
    // However, looking at loadExercises, we have the data in memory if we wanted, but let's just fetch from the new endpoint if we had it, or filter from cache.
    // Let's iterate through the DOM or cache. 'dataCache' has exercises?

    // Simplest approach: We already have the list loaded.
    // Let's fetch the specific exercise details using the chapter endpoint we know exists, or search in our local cache.
    // But we need the chapter_id.

    // Let's just loop through chapters to find it if we don't have it.
    // Or, we can use the `dataCache.exercises` if populated.

    // Actually, let's use the button's data attributes if we added them, but we didn't.
    // Let's try to find it in the `allExercises` array if we made it global, but we didn't.

    // Valid Plan:
    // 1. Show loading state.
    // 2. Fetch all chapters.
    // 3. Search for exercise in each chapter (parallel).
    // 4. Populate modal.

    // OPTIMIZATION: We changed the UI to group by chapter. We can pass the chapter_id to the edit button too!
    // But I can't change the HTML generation easily without reloading.

    // Let's assumes we find it.
    // Actually, I'll search all chapters for now.

    const chaptersResponse = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters?user_id=${currentUser.user_id}`);
    const chaptersData = await chaptersResponse.json();
    const chapters = chaptersData.chapters || [];

    let foundExercise = null;
    let foundChapterId = null;

    for (const chapter of chapters) {
      const exResp = await fetch(`${window.API_BASE_URL}/chapters/${encodeURIComponent(chapter.chapter_id)}/exercises?user_id=${currentUser.user_id}`);
      const exData = await exResp.json();
      const exercises = exData.exercises || [];
      const match = exercises.find(e => e.exercise_id === exerciseId);
      if (match) {
        foundExercise = match;
        foundChapterId = chapter.chapter_id;
        break;
      }
    }

    if (!foundExercise) {
      alert("Exercise not found.");
      return;
    }

    const modal = document.getElementById('createExerciseModal');
    const modalTitle = modal.querySelector('h2');
    const submitBtn = modal.querySelector('button[type="submit"]');

    // Set to Edit Mode
    modal.dataset.mode = 'edit';
    modal.dataset.exerciseId = exerciseId;
    modalTitle.textContent = "Edit Exercise";
    submitBtn.textContent = "Update Exercise";

    // Populate Form
    document.getElementById('exerciseTitle').value = foundExercise.title || '';
    document.getElementById('exerciseDescription').value = foundExercise.description || '';
    document.getElementById('exerciseDifficulty').value = foundExercise.difficulty || 'medium';
    document.getElementById('exerciseSolution').value = foundExercise.solution_code || '';

    // Handle Chapter Select
    await loadChapterOptions();
    document.getElementById('exerciseChapter').value = foundChapterId;
    document.getElementById('exerciseChapter').disabled = true; // Cannot move chapters in edit mode easily

    // File input is optional/hidden for edit
    // (We could clear it)
    document.getElementById('exerciseFile').value = '';

    modal.style.display = 'flex';

  } catch (error) {
    console.error("Error fetching exercise for edit:", error);
    alert("Failed to load exercise details.");
  }
}

// Start exercise from class view - opens practice playground
function startExerciseFromClass(exerciseId, chapterId, exerciseTitle) {
  window.location.href = `practice-playground.html?exercise_id=${encodeURIComponent(exerciseId)}&chapter_id=${encodeURIComponent(chapterId)}&class_id=${encodeURIComponent(currentClassId)}&title=${encodeURIComponent(exerciseTitle)}&page_type=professor`;
}

// Load resources
async function loadResources() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    return;
  }

  const resourcesList = document.getElementById('resourcesList');

  try {
    resourcesList.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading resources...</div>';

    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/resources?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to load resources');
    }

    const allResources = data.all_resources || [];

    // Add default tools and datasets
    const defaultResources = [
      {
        resource_id: 'default_tool_colab',
        title: 'Google Colab',
        description: 'Free cloud-based Jupyter notebook environment for running Python code and data analysis.',
        resource_type: 'tool',
        resource_url: 'https://colab.research.google.com',
        is_default: true
      },
      {
        resource_id: 'default_tool_code_assistant',
        title: 'Code Assistant',
        description: 'AI-powered assistant that helps you write code, analyze data, derive insights, and create visualizations.',
        resource_type: 'tool',
        resource_url: 'code-assistant.html',
        is_default: true
      },
      {
        resource_id: 'default_dataset_kaggle',
        title: 'Kaggle Datasets',
        description: 'Access to thousands of datasets for practice and real-world analysis projects.',
        resource_type: 'dataset',
        resource_url: 'https://www.kaggle.com/datasets',
        is_default: true
      },
      {
        resource_id: 'default_dataset_uci',
        title: 'UCI Machine Learning Repository',
        description: 'Collection of databases, domain theories, and data generators for machine learning.',
        resource_type: 'dataset',
        resource_url: 'https://archive.ics.uci.edu',
        is_default: true
      },
      {
        resource_id: 'default_dataset_nyc',
        title: 'NYC Open Data',
        description: 'Official repository of publicly available datasets from New York City agencies and departments.',
        resource_type: 'dataset',
        resource_url: 'https://opendata.cityofnewyork.us',
        is_default: true
      },
      {
        resource_id: 'default_dataset_worldbank',
        title: 'World Bank Open Data',
        description: 'Free and open access to global development data including economic, social, and environmental indicators.',
        resource_type: 'dataset',
        resource_url: 'https://data.worldbank.org',
        is_default: true
      }
    ];

    // Combine all resources: custom resources, then default tools/datasets
    const combinedResources = [...allResources, ...defaultResources];
    loadedResources = combinedResources; // Store for edit functionality

    if (combinedResources.length === 0) {
      resourcesList.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">📖</div>
          <p style="color: #64748b;">No resources added yet. Add helpful links, documents, or external resources for your students.</p>
        </div>
      `;
    } else {
      // Group by type
      const groupedByType = {};
      combinedResources.forEach(resource => {
        const type = resource.resource_type || 'link';
        if (!groupedByType[type]) {
          groupedByType[type] = [];
        }
        groupedByType[type].push(resource);
      });

      // Type icons and labels
      const typeLabels = {
        'pdf': { icon: '📄', label: 'PDFs & Documents' },
        'chapter': { icon: '📖', label: 'Chapter PDFs' },
        'tool': { icon: '🛠️', label: 'Tools' },
        'dataset': { icon: '💾', label: 'Datasets' },
        'video': { icon: '🎥', label: 'Videos' },
        'article': { icon: '📝', label: 'Articles' },
        'link': { icon: '🔗', label: 'Links' }
      };

      resourcesList.innerHTML = Object.keys(groupedByType).map(type => {
        const typeInfo = typeLabels[type] || { icon: '🔗', label: 'Resources' };
        const resources = groupedByType[type];

        return `
          <div style="margin-bottom: 2.5rem;">
            <h3 style="color: #222c3e; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #e2e8f0; display: flex; align-items: center; gap: 0.5rem;">
              <span>${typeInfo.icon}</span>
              <span>${typeInfo.label}</span>
            </h3>
            <div class="resources-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
              ${resources.map(resource => {
          const icon = resource.resource_type === 'pdf' ? '📄' :
            resource.resource_type === 'chapter' ? '📖' :
              resource.resource_type === 'tool' ? '🛠️' :
                resource.resource_type === 'dataset' ? '💾' :
                  resource.resource_type === 'video' ? '🎥' : '🔗';

          let url = resource.resource_url || resource.url || '#';
          // Fix relative URLs to point to API
          if (url.startsWith('/')) {
            // Remove leading slash to avoid double slash if base has it, though normally base doesn't.
            // Usually API_BASE_URL is '.../api', and url is '/api/resource...'.
            // Wait, if url is '/api/resources/files/...' and API_BASE_URL is '.../api', we might duplicate '/api' if we blindly concat.
            // But window.API_BASE_URL is usually 'https://...onrender.com/api'.
            // If url is '/api/resources...', then 'https://.../api/api/resources' might be wrong.
            // Actually, file uploads returning '/api/resources/files/...' implies they are relative to SERVER ROOT.
            // window.API_BASE_URL includes '/api'.
            // So we should replace the domain part.
            // Safest: Use window.API_BASE_URL's origin + url.

            // Simplest safely:
            if (window.API_BASE_URL && window.API_BASE_URL.startsWith('http')) {
              const apiOrigin = new URL(window.API_BASE_URL).origin;
              url = `${apiOrigin}${url}`;
            }
          }
          let linkTarget = '';
          let linkText = 'Visit Resource';

          // Handle PDFs
          if (resource.resource_type === 'pdf') {
            linkText = 'View PDF';
            const isExternal = url.startsWith('http://') || url.startsWith('https://');
            linkTarget = isExternal ? 'target="_blank"' : '';
          } else if (resource.resource_type === 'chapter') {
            linkText = 'View PDF';
            linkTarget = '_blank';
          } else {
            const isExternal = url.startsWith('http://') || url.startsWith('https://');
            linkTarget = isExternal ? 'target="_blank"' : '';
            linkText = resource.resource_type === 'video' ? 'Watch Video' :
              resource.resource_type === 'dataset' ? 'Browse Dataset' :
                resource.resource_type === 'tool' ? 'Use Tool' : 'Visit Resource';
          }

          return `
                  <div class="resource-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 0.75rem; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 1px 3px rgba(0,0,0,0.1)';">
                    <div style="font-size: 2rem; margin-bottom: 0.75rem;">${icon}</div>
                    <h3 style="margin: 0 0 0.5rem 0; color: #222c3e; font-size: 1.125rem;">${escapeHtml(resource.title)}</h3>
                    <p style="color: #64748b; margin: 0 0 1rem 0; font-size: 0.875rem; line-height: 1.5;">${escapeHtml(resource.description || '')}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                      <a href="${escapeHtml(url)}" ${linkTarget} class="resource-link" style="color: #2569f4; text-decoration: none; font-weight: 500; font-size: 0.875rem;">
                        ${linkText} →
                      </a>
                      ${!resource.is_default ? `
                        <div style="display: flex; gap: 0.25rem;">
                          ${!resource.is_chapter ? `<button class="btn btn-secondary edit-resource-btn" data-resource-id="${resource.resource_id}" style="padding: 0.375rem 0.75rem; font-size: 0.75rem;">✏️</button>` : ''}
                          <button class="btn btn-secondary delete-resource-btn" data-resource-id="${resource.resource_id}" ${resource.is_chapter ? `data-chapter-id="${resource.chapter_id}"` : ''} style="padding: 0.375rem 0.75rem; font-size: 0.75rem; color: #dc2626;">🗑️</button>
                        </div>
                      ` : ''}
                    </div>
                  </div>
                `;
        }).join('')}
            </div>
          </div>
        `;
      }).join('');
    }
  } catch (error) {
    console.error('Error loading resources:', error);
    resourcesList.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: #fee2e2; border: 1px solid #ef4444; border-radius: 0.5rem;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
        <p style="color: #991b1b;">Error loading resources: ${escapeHtml(error.message)}</p>
        <button class="btn btn-primary" onclick="loadResources()" style="margin-top: 1rem;">Retry</button>
      </div>
    `;
  }
}

// Show add resource modal
function showAddResourceModal() {
  const modal = document.getElementById('addResourceModal');
  const form = document.getElementById('addResourceForm');
  const errorDiv = document.getElementById('addResourceError');

  form.reset();
  errorDiv.style.display = 'none';

  // Reset to default state
  document.getElementById('resourceUrl').required = true;
  document.getElementById('resourceFile').required = false;
  document.getElementById('resourceUrlSection').style.display = 'block';
  document.getElementById('resourceFileSection').style.display = 'none';
  document.getElementById('resourceInputTypeSection').style.display = 'none';
  document.querySelector('input[name="resourceInputType"][value="link"]').checked = true;

  updateResourceInputType();
  modal.style.display = 'flex';
}

// Update resource input type based on resource type
function updateResourceInputType() {
  const resourceType = document.getElementById('resourceType').value;
  const inputTypeSection = document.getElementById('resourceInputTypeSection');

  // Show link/upload option for file-based resource types
  const fileBasedTypes = ['pdf', 'csv', 'excel', 'dataset', 'tool', 'ipynb'];
  if (fileBasedTypes.includes(resourceType)) {
    inputTypeSection.style.display = 'block';
    toggleResourceInput();
  } else {
    inputTypeSection.style.display = 'none';
    // Always use link for non-file types
    document.getElementById('resourceUrlSection').style.display = 'block';
    document.getElementById('resourceFileSection').style.display = 'none';
    document.getElementById('resourceUrl').required = true;
    document.getElementById('resourceFile').required = false;
  }
}

// Toggle between link and file upload inputs
function toggleResourceInput() {
  const inputType = document.querySelector('input[name="resourceInputType"]:checked')?.value || 'link';
  const urlSection = document.getElementById('resourceUrlSection');
  const fileSection = document.getElementById('resourceFileSection');
  const urlInput = document.getElementById('resourceUrl');
  const fileInput = document.getElementById('resourceFile');
  const linkLabel = document.getElementById('linkOptionLabel');
  const uploadLabel = document.getElementById('uploadOptionLabel');

  if (inputType === 'link') {
    urlSection.style.display = 'block';
    fileSection.style.display = 'none';
    urlInput.required = true;
    fileInput.required = false;
    fileInput.value = ''; // Clear file selection
    linkLabel.style.borderColor = '#2569f4';
    linkLabel.style.background = '#eff6ff';
    uploadLabel.style.borderColor = '#e2e8f0';
    uploadLabel.style.background = 'transparent';
  } else {
    urlSection.style.display = 'none';
    fileSection.style.display = 'block';
    urlInput.required = false;
    fileInput.required = true;
    urlInput.value = ''; // Clear URL
    linkLabel.style.borderColor = '#e2e8f0';
    linkLabel.style.background = 'transparent';
    uploadLabel.style.borderColor = '#2569f4';
    uploadLabel.style.background = '#eff6ff';
  }

  // Update file input accept attribute based on resource type
  const resourceType = document.getElementById('resourceType').value;
  if (resourceType === 'pdf') {
    fileInput.accept = '.pdf';
  } else if (resourceType === 'csv') {
    fileInput.accept = '.csv';
  } else if (resourceType === 'excel') {
    fileInput.accept = '.xlsx,.xls';
  } else if (resourceType === 'dataset') {
    fileInput.accept = '.csv,.xlsx,.xls,.json';
  } else if (resourceType === 'ipynb') {
    fileInput.accept = '.ipynb';
  } else {
    fileInput.accept = '.pdf,.csv,.xlsx,.xls,.txt,.json,.ipynb';
  }

  // Show file info when selected
  fileInput.onchange = function () {
    const fileInfo = document.getElementById('resourceFileInfo');
    if (this.files && this.files.length > 0) {
      const file = this.files[0];
      fileInfo.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
      fileInfo.style.display = 'block';
    } else {
      fileInfo.style.display = 'none';
    }
  };
}

// Hide add resource modal
function hideAddResourceModal() {
  const modal = document.getElementById('addResourceModal');
  const form = document.getElementById('addResourceForm');
  const errorDiv = document.getElementById('addResourceError');
  const modalTitle = modal.querySelector('h2');
  const submitBtn = modal.querySelector('button[type="submit"]');

  modal.style.display = 'none';
  form.reset();
  errorDiv.style.display = 'none';
  errorDiv.textContent = '';

  // Reset to Add mode
  modalTitle.textContent = 'Add Resource';
  submitBtn.textContent = 'Add Resource';
  resourceToEditId = null;
}

// Handle add resource form submission
async function handleAddResource(event) {
  event.preventDefault();

  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    alert('Error: User not logged in');
    return;
  }

  const title = document.getElementById('resourceTitle').value.trim();
  const description = document.getElementById('resourceDescription').value.trim();
  const resourceType = document.getElementById('resourceType').value;
  const inputType = document.querySelector('input[name="resourceInputType"]:checked')?.value || 'link';
  const resourceUrl = document.getElementById('resourceUrl').value.trim();
  const resourceFile = document.getElementById('resourceFile').files[0];

  if (!title) {
    showAddResourceError('Please enter a resource title');
    return;
  }

  // When editing, URL is optional (resource may already have one)
  if (!resourceToEditId && inputType === 'link' && !resourceUrl) {
    showAddResourceError('Please enter a resource URL');
    return;
  }

  if (!resourceToEditId && inputType === 'upload' && !resourceFile) {
    showAddResourceError('Please select a file to upload');
    return;
  }

  const errorDiv = document.getElementById('addResourceError');
  errorDiv.style.display = 'none';

  try {
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = resourceToEditId ? 'Saving...' : 'Adding...';

    // Check if we're in edit mode
    if (resourceToEditId) {
      // Edit mode - use PUT
      const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/resources/${encodeURIComponent(resourceToEditId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: currentUser.user_id,
          title: title,
          description: description,
          resource_type: resourceType,
          resource_url: resourceUrl
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to update resource');
      }

      // Success
      hideAddResourceModal();
      await loadResources();

      // Show success message
      const resourcesList = document.getElementById('resourcesList');
      const successMsg = document.createElement('div');
      successMsg.style.cssText = 'padding: 1rem; margin-bottom: 1rem; background: #d1fae5; color: #065f46; border-radius: 0.5rem; border: 1px solid #10b981;';
      successMsg.textContent = '✓ Resource updated successfully!';
      resourcesList.insertBefore(successMsg, resourcesList.firstChild);
      setTimeout(() => successMsg.remove(), 3000);

      return;
    }

    // Add mode - existing logic
    let finalResourceUrl = resourceUrl;

    // If uploading a file, upload it first
    if (inputType === 'upload' && resourceFile) {
      // Create FormData for file upload
      const formData = new FormData();
      formData.append('file', resourceFile);
      formData.append('user_id', currentUser.user_id);
      formData.append('class_id', currentClassId);
      formData.append('resource_type', resourceType);
      formData.append('title', title);
      formData.append('description', description);

      // Upload file - this now also creates the database record

      // Set timeout to warn user about large files
      const uploadTimeout = setTimeout(() => {
        const errorDiv = document.getElementById('addResourceError');
        errorDiv.style.cssText = 'display: block; margin-bottom: 1rem; padding: 0.75rem; background: #eff6ff; color: #1e40af; border-radius: 0.375rem; border: 1px solid #bfdbfe;';
        errorDiv.innerHTML = '<strong>Processing Large File...</strong><br>This is a large file and may take longer to process (up to 5 mins). Please wait and do not close this window.';
      }, 30000); // 30 seconds

      try {
        const uploadResponse = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/resources/upload`, {
          method: 'POST',
          body: formData
        });

        clearTimeout(uploadTimeout); // Clear timeout on response

        const uploadData = await uploadResponse.json();

        if (!uploadResponse.ok) {
          throw new Error(uploadData.error || 'Failed to upload file');
        }

        // Upload endpoint now creates the resource record, so we're done
        hideAddResourceModal();
        await loadResources();

        // Show success message
        const resourcesList = document.getElementById('resourcesList');
        const successMsg = document.createElement('div');
        successMsg.style.cssText = 'padding: 1rem; margin-bottom: 1rem; background: #d1fae5; color: #065f46; border-radius: 0.5rem; border: 1px solid #10b981;';
        successMsg.textContent = '✓ Resource uploaded successfully!';
        resourcesList.insertBefore(successMsg, resourcesList.firstChild);
        setTimeout(() => successMsg.remove(), 3000);
        return;
      } catch (err) {
        clearTimeout(uploadTimeout);
        throw err;
      }

      const uploadData = await uploadResponse.json();

      if (!uploadResponse.ok) {
        throw new Error(uploadData.error || 'Failed to upload file');
      }

      // Upload endpoint now creates the resource record, so we're done
      hideAddResourceModal();
      await loadResources();

      // Show success message
      const resourcesList = document.getElementById('resourcesList');
      const successMsg = document.createElement('div');
      successMsg.style.cssText = 'padding: 1rem; margin-bottom: 1rem; background: #d1fae5; color: #065f46; border-radius: 0.5rem; border: 1px solid #10b981;';
      successMsg.textContent = '✓ Resource uploaded successfully!';
      resourcesList.insertBefore(successMsg, resourcesList.firstChild);
      setTimeout(() => successMsg.remove(), 3000);
      return;
    }

    // URL/link mode - create the resource with the provided URL
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/resources`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: currentUser.user_id,
        title: title,
        description: description,
        resource_type: resourceType,
        resource_url: finalResourceUrl
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to add resource');
    }

    // Success - close modal and refresh resources list
    hideAddResourceModal();
    await loadResources();

    // Show success message
    const resourcesList = document.getElementById('resourcesList');
    const successMsg = document.createElement('div');
    successMsg.style.cssText = 'padding: 1rem; margin-bottom: 1rem; background: #d1fae5; color: #065f46; border-radius: 0.5rem; border: 1px solid #10b981;';
    successMsg.textContent = '✓ Resource added successfully!';
    resourcesList.insertBefore(successMsg, resourcesList.firstChild);

    setTimeout(() => {
      successMsg.remove();
    }, 3000);

  } catch (error) {
    console.error('Error saving resource:', error);
    showAddResourceError(error.message || 'Failed to save resource. Please try again.');

    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = false;
    submitButton.textContent = resourceToEditId ? 'Save Changes' : 'Add Resource';
  }
}

// Delete resource
async function deleteResource(resourceId, chapterId = null) {
  if (!confirm('Are you sure you want to delete this resource?')) {
    return;
  }

  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    alert('Error: User not logged in');
    return;
  }

  try {
    let response;

    // If it's a chapter PDF, delete the chapter instead
    if (chapterId || resourceId.startsWith('pdf_')) {
      const actualChapterId = chapterId || resourceId.replace('pdf_', '');
      response = await fetch(`${window.API_BASE_URL}/chapters/${encodeURIComponent(actualChapterId)}?user_id=${currentUser.user_id}`, {
        method: 'DELETE'
      });
    } else {
      // Regular resource deletion
      response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/resources/${encodeURIComponent(resourceId)}?user_id=${currentUser.user_id}`, {
        method: 'DELETE'
      });
    }

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to delete resource');
    }

    // Reload resources and chapters
    await loadResources();
    await loadChapters();
  } catch (error) {
    console.error('Error deleting resource:', error);
    alert('Failed to delete resource: ' + error.message);
  }
}

// Edit resource - variable to track which resource is being edited
let resourceToEditId = null;

function hideAddResourceModal() {
  document.getElementById('addResourceModal').style.display = 'none';
  document.getElementById('addResourceForm').reset();
  document.getElementById('addResourceError').style.display = 'none';
  document.getElementById('resourceInputTypeSection').style.display = 'block'; // Restore visibility
  document.getElementById('resourceType').disabled = false; // Enable resource type selection

  const existingNote = document.getElementById('editSourceNote');
  if (existingNote) existingNote.remove();

  resourceToEditId = null;
}

// Toggle resource input method (Link vs Upload)
function toggleResourceMethod() {
  const isLink = document.getElementById('resourceMethodLink').checked;
  const linkSection = document.getElementById('resourceUrlSection');
  const fileSection = document.getElementById('resourceFileSection');
  const urlInput = document.getElementById('resourceUrl');
  const fileInput = document.getElementById('resourceFile');

  if (isLink) {
    linkSection.style.display = 'block';
    fileSection.style.display = 'none';
    urlInput.required = true;
    fileInput.required = false;
    fileInput.value = ''; // Clear file selection
  } else {
    linkSection.style.display = 'none';
    fileSection.style.display = 'block';
    urlInput.required = false; // Not required when uploading
    fileInput.required = true;
    urlInput.value = ''; // Clear URL
  }
}
window.toggleResourceInput = toggleResourceMethod; // Alias

// Open edit resource modal by looking up resource ID
function openEditResourceModal(resourceId) {
  // Find the resource in loadedResources
  const resource = loadedResources.find(r => r.resource_id === resourceId);
  if (!resource) {
    alert('Resource not found');
    return;
  }

  resourceToEditId = resourceId;

  const modal = document.getElementById('addResourceModal');
  const form = document.getElementById('addResourceForm');
  const modalTitle = modal.querySelector('h2');
  const submitBtn = modal.querySelector('button[type="submit"]');

  // Update modal for edit mode
  modalTitle.textContent = 'Edit Resource';
  submitBtn.textContent = 'Save Changes';

  // Populate form fields
  document.getElementById('resourceTitle').value = resource.title || '';
  document.getElementById('resourceDescription').value = resource.description || '';
  document.getElementById('resourceType').value = resource.resource_type || 'link';
  document.getElementById('resourceType').disabled = true; // Disable resource type in edit mode
  document.getElementById('resourceUrl').value = resource.resource_url || '';

  // Show link mode (can't change file when editing)
  document.getElementById('resourceMethodLink').checked = true;
  toggleResourceMethod();

  // Hide the input type section entirely in edit mode to prevent changing source
  document.getElementById('resourceInputTypeSection').style.display = 'none';
  document.getElementById('resourceUrlSection').style.display = 'none';
  document.getElementById('resourceFileSection').style.display = 'none';

  // Show a note that source cannot be changed
  const existingNote = document.getElementById('editSourceNote');
  if (existingNote) existingNote.remove();

  const note = document.createElement('div');
  note.id = 'editSourceNote';
  note.style.cssText = 'margin-bottom: 1.5rem; padding: 0.75rem; background: #f1f5f9; color: #64748b; border-radius: 0.375rem; font-size: 0.875rem;';
  note.textContent = 'To change the file or URL, please delete this resource and create a new one.';

  const typeSection = document.getElementById('resourceInputTypeSection');
  typeSection.parentNode.insertBefore(note, typeSection);

  // Make URL not required for edit (in case it was originally a file)
  document.getElementById('resourceUrl').required = false;

  // Show modal
  modal.style.display = 'flex';
}

// Legacy edit resource function (kept for compatibility)
function editResource(resourceId, title, description, resourceType, resourceUrl) {
  openEditResourceModal(resourceId);
}

// Handle resource form submission (add or edit)
// function handleResourceFormSubmit removed - replaced by handleAddResource

// Show error in add resource modal
function showAddResourceError(message) {
  const errorDiv = document.getElementById('addResourceError');
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
}

// Progress Page Logic

// Switch between progress views
function switchProgressView(viewName) {
  // Update buttons
  document.querySelectorAll('.sub-tab-button').forEach(btn => btn.classList.remove('active'));

  // Hide all containers
  document.getElementById('progressTableContainer').style.display = 'none';
  document.getElementById('avgLeaderboardContainer').style.display = 'none';
  document.getElementById('exLeaderboardContainer').style.display = 'none';

  // Show selected container and update button
  if (viewName === 'table') {
    document.getElementById('subTabTable').classList.add('active');
    document.getElementById('progressTableContainer').style.display = 'block';
    loadDetailedProgress();
  } else if (viewName === 'avgLeaderboard') {
    document.getElementById('subTabAvg').classList.add('active');
    document.getElementById('avgLeaderboardContainer').style.display = 'block';
    loadAvgLeaderboard();
  } else if (viewName === 'exLeaderboard') {
    document.getElementById('subTabEx').classList.add('active');
    document.getElementById('exLeaderboardContainer').style.display = 'block';
    loadLeaderboardExercises();
  }
}

// Load Progress Tab Main
async function loadProgress() {
  // Reset view to default (Average Leaderboard, matching student view)
  switchProgressView('avgLeaderboard');
}

// Load Detailed Progress Matrix
async function loadDetailedProgress() {
  const container = document.getElementById('progressTableContainer');
  const currentUser = getCurrentUser();

  if (!currentUser || !currentClassId) return;

  // Show loading
  container.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading progress data...</div>';

  try {
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/progress?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error || 'Failed to load progress data');

    if (!data.students || data.students.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">👥</div>
          <p style="color: #64748b;">No students enrolled yet.</p>
        </div>
      `;
      return;
    }

    // Sort exercises by chapter and number
    const exercises = data.exercises || [];

    if (exercises.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">📝</div>
          <p style="color: #64748b;">No exercises created yet.</p>
        </div>
      `;
      return;
    }

    // Build table HTML
    let html = `
      <div style="overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
              <th style="padding: 0.75rem 1rem; text-align: left; position: sticky; left: 0; background: #f8fafc; z-index: 10;">Student</th>
              <th style="padding: 0.75rem 1rem; text-align: center; border-right: 1px solid #e2e8f0;">Avg Score</th>
    `;

    // Header row - Exercises
    exercises.forEach(ex => {
      html += `<th style="padding: 0.75rem; text-align: center; min-width: 80px; border-right: 1px solid #ebf0f5;" title="${ex.title}">
                <div style="font-weight: 600;">${ex.full_label}</div>
              </th>`;
    });

    html += `</tr></thead><tbody>`;

    // Data rows - Students
    data.students.forEach(student => {
      const studentScores = data.scores[student.user_id] || {};

      // Calculate average
      let totalScore = 0;
      let count = 0;
      exercises.forEach(ex => {
        if (studentScores[ex.exercise_id]) {
          totalScore += parseFloat(studentScores[ex.exercise_id]);
          count++;
        }
      });
      const avg = count > 0 ? (totalScore / count).toFixed(1) : '-';

      html += `
        <tr style="border-bottom: 1px solid #e2e8f0; background: white;">
          <td style="padding: 0.75rem 1rem; font-weight: 500; color: #1e293b; position: sticky; left: 0; background: white; border-right: 1px solid #e2e8f0;">${student.name}</td>
          <td style="padding: 0.75rem 1rem; text-align: center; font-weight: 600; color: #2569f4; border-right: 1px solid #e2e8f0;">${avg}</td>
      `;

      // Exercise cells
      exercises.forEach(ex => {
        const score = studentScores[ex.exercise_id];
        let cellContent = '-';
        let cellStyle = 'color: #94a3b8;'; // gray for no data
        let bgColor = '';

        if (score !== undefined) {
          cellContent = score;
          const scoreNum = parseFloat(score);
          if (scoreNum >= 90) {
            cellStyle = 'color: #059669; font-weight: 600;'; // green
            bgColor = 'background-color: #ecfdf5;';
          } else if (scoreNum >= 70) {
            cellStyle = 'color: #0284c7; font-weight: 600;'; // blue
            bgColor = 'background-color: #f0f9ff;';
          } else if (scoreNum >= 50) {
            cellStyle = 'color: #d97706; font-weight: 500;'; // orange
            bgColor = 'background-color: #fffbeb;';
          } else {
            cellStyle = 'color: #dc2626; font-weight: 500;'; // red
            bgColor = 'background-color: #fef2f2;';
          }
        }

        html += `<td style="padding: 0.5rem; text-align: center; ${cellStyle} ${bgColor} border-right: 1px solid #ebf0f5;">${cellContent}</td>`;
      });

      html += `</tr>`;
    });

    html += `</tbody></table></div>`;
    container.innerHTML = html;

  } catch (error) {
    console.error('Error loading detailed progress:', error);
    container.innerHTML = `<div class="error-message">Failed to load data: ${error.message}</div>`;
  }
}

// Load Average Leaderboard
async function loadAvgLeaderboard() {
  const container = document.getElementById('avgLeaderboardContainer');
  const currentUser = getCurrentUser();
  if (!currentUser || !currentClassId) return;

  container.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading leaderboard...</div>';

  try {
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/leaderboard/average?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error || 'Failed to load leaderboard');

    if (!data.leaderboard || data.leaderboard.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <p style="color: #64748b;">No data available for leaderboard yet.</p>
        </div>
      `;
      return;
    }

    // Render list
    let html = `
      <div style="max-width: 800px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 0.5rem; overflow: hidden;">
        <table style="width: 100%; border-collapse: collapse;">
          <thead style="background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
            <tr>
              <th style="padding: 1rem; text-align: center; width: 60px;">Rank</th>
              <th style="padding: 1rem; text-align: left;">Student</th>
              <th style="padding: 1rem; text-align: center;">Exercises Completed</th>
              <th style="padding: 1rem; text-align: right;">Average Score</th>
            </tr>
          </thead>
          <tbody>
    `;

    data.leaderboard.forEach(entry => {
      let rankIcon = entry.rank;
      if (entry.rank === 1) rankIcon = '🥇';
      else if (entry.rank === 2) rankIcon = '🥈';
      else if (entry.rank === 3) rankIcon = '🥉';

      html += `
        <tr style="border-bottom: 1px solid #e2e8f0; background: white;">
          <td style="padding: 1rem; text-align: center; font-size: 1.2rem; font-weight: 600;">${rankIcon}</td>
          <td style="padding: 1rem; font-weight: 500;">${entry.name}</td>
          <td style="padding: 1rem; text-align: center; color: #64748b;">${entry.exercises_completed}</td>
          <td style="padding: 1rem; text-align: right; font-weight: 700; color: #2569f4; font-size: 1.1rem;">${entry.average_score}</td>
        </tr>
      `;
    });

    html += `</tbody></table></div>`;
    container.innerHTML = html;

  } catch (error) {
    container.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
  }
}

// Load List of Exercises for Select Dropdown
async function loadLeaderboardExercises() {
  const select = document.getElementById('leaderboardExerciseSelect');
  const currentUser = getCurrentUser();
  if (!currentUser || !currentClassId) return;

  // Don't reload if already loaded
  if (select.options.length > 2) return;

  select.disabled = true;

  try {
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/progress?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error);

    // Clear and populate
    select.innerHTML = '<option value="">-- Choose an Exercise --</option>';

    (data.exercises || []).forEach(ex => {
      const option = document.createElement('option');
      option.value = ex.exercise_id; // Using exercise_id as the key
      option.textContent = `${ex.full_label}: ${ex.title}`;
      select.appendChild(option);
    });

    select.disabled = false;

  } catch (error) {
    console.error("Error loading exercises for list:", error);
    select.innerHTML = '<option value="">Error loading exercises</option>';
  }
}

// Load Single Exercise Leaderboard
async function loadExerciseLeaderboard(exerciseId) {
  const container = document.getElementById('exLeaderboardContent');
  const currentUser = getCurrentUser();

  if (!exerciseId) {
    container.innerHTML = `<div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;"><p style="color: #64748b;">Select an exercise above to see the leaderboard.</p></div>`;
    return;
  }

  container.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading scores...</div>';

  try {
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/leaderboard/exercise/${encodeURIComponent(exerciseId)}?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) {
      // Handle the case where no scores exist for this exercise gracefully
      if (response.status === 404 || (data.message && data.message.includes('No scores'))) {
        container.innerHTML = `
          <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
            <p style="color: #64748b;">No scores recorded for this exercise yet.</p>
          </div>
        `;
        return;
      }
      throw new Error(data.error || 'Failed to load leaderboard');
    }

    if (!data.leaderboard || data.leaderboard.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem;">
          <p style="color: #64748b;">No scores for this exercise yet.</p>
        </div>
      `;
      return;
    }

    // Render list
    let html = `
      <div style="max-width: 800px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 0.5rem; overflow: hidden;">
        <table style="width: 100%; border-collapse: collapse;">
          <thead style="background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
            <tr>
              <th style="padding: 1rem; text-align: center; width: 60px;">Rank</th>
              <th style="padding: 1rem; text-align: left;">Student</th>
              <th style="padding: 1rem; text-align: center;">Submitted</th>
              <th style="padding: 1rem; text-align: right;">Score</th>
            </tr>
          </thead>
          <tbody>
    `;

    data.leaderboard.forEach(entry => {
      let rankIcon = entry.rank;
      if (entry.rank === 1) rankIcon = '🥇';
      else if (entry.rank === 2) rankIcon = '🥈';
      else if (entry.rank === 3) rankIcon = '🥉';

      const date = entry.submitted_at ? new Date(entry.submitted_at).toLocaleDateString() : '-';

      html += `
        <tr style="border-bottom: 1px solid #e2e8f0; background: white;">
          <td style="padding: 1rem; text-align: center; font-size: 1.2rem; font-weight: 600;">${rankIcon}</td>
          <td style="padding: 1rem; font-weight: 500;">${entry.name}</td>
          <td style="padding: 1rem; text-align: center; color: #64748b;">${date}</td>
          <td style="padding: 1rem; text-align: right; font-weight: 700; color: #2569f4; font-size: 1.1rem;">${entry.score}</td>
        </tr>
      `;
    });

    html += `</tbody></table></div>`;
    container.innerHTML = html;

  } catch (error) {
    container.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
  }
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

    // Reload exercises if any were generated
    if (data.exercises_generated && data.exercises_generated > 0) {
      if (currentClassData) {
        currentClassData.exercise_count = (currentClassData.exercise_count || 0) + data.exercises_generated;
        renderClassHeader(currentClassData);
      }
      // Reload exercises tab
      loadExercises();
      alert(`Chapter "${title}" uploaded successfully!\n${data.exercises_generated} exercises were auto-generated.`);
    } else {
      alert(`Chapter "${title}" uploaded successfully!`);
    }


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
document.addEventListener('click', function (event) {
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
document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape') {
    hideUploadChapterModal();
    hideEditClassModal();
  }
});

// Helper to load chapters for select
async function loadChapterOptions() {
  const chapterSelect = document.getElementById('exerciseChapter');
  const currentUser = getCurrentUser();
  if (!currentUser || !currentClassId) return;

  try {
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (response.ok) {
      chapterSelect.innerHTML = '<option value="">Select a chapter...</option>';
      (data.chapters || []).forEach(chapter => {
        const option = document.createElement('option');
        option.value = chapter.chapter_id;
        option.textContent = `Chapter ${chapter.chapter_number}: ${chapter.title}`;
        chapterSelect.appendChild(option);
      });
    }
  } catch (e) {
    console.error("Error loading chapter options", e);
  }
}

async function editExercise(exerciseId) {
  const modal = document.getElementById('createExerciseModal');
  const titleInput = document.getElementById('exerciseTitle');
  const descInput = document.getElementById('exerciseDescription');
  const difficultyInput = document.getElementById('exerciseDifficulty');
  const solutionInput = document.getElementById('exerciseSolution');
  const chapterSelect = document.getElementById('exerciseChapter');
  const modalTitle = modal.querySelector('h2');
  const submitBtn = modal.querySelector('button[type="submit"]');

  try {
    const currentUser = getCurrentUser();
    if (!currentUser) return;

    // Reset form first
    document.getElementById('createExerciseForm').reset();

    // Fetch exercise details
    const response = await fetch(`${window.API_BASE_URL}/exercises/${exerciseId}?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error);

    const exercise = data.exercise;

    // Load chapters if empty - wait for it
    if (chapterSelect.options.length <= 1) {
      await loadChapterOptions();
    }

    // Populate form
    titleInput.value = exercise.title;
    descInput.value = exercise.description;
    difficultyInput.value = exercise.difficulty;
    solutionInput.value = exercise.solution_code || '';
    chapterSelect.value = exercise.chapter_id;

    // Set Edit Mode
    modalTitle.textContent = "Edit Exercise";
    submitBtn.textContent = "Update Exercise";
    modal.dataset.mode = 'edit';
    modal.dataset.exerciseId = exerciseId;

    modal.style.display = 'flex';

  } catch (error) {
    console.error('Error fetching exercise for edit:', error);
    alert('Failed to load exercise details.');
  }
}

// --- Chapter Management (Edit/Delete) ---

let chapterToDeleteId = null;

// Show Edit Chapter Modal
async function showEditChapterModal(chapterId) {
  const modal = document.getElementById('editChapterModal');
  const form = document.getElementById('editChapterForm');
  const errorDiv = document.getElementById('editChapterError');

  // Reset state
  errorDiv.style.display = 'none';
  form.dataset.chapterId = chapterId;

  // Load current chapter details
  try {
    const currentUser = getCurrentUser();

    // Fetch chapters list to find the chapter
    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters?user_id=${currentUser.user_id}`);
    const data = await response.json();

    if (!response.ok) throw new Error('Failed to load chapter details');

    const chapter = data.chapters.find(c => c.chapter_id === chapterId);
    if (!chapter) throw new Error('Chapter not found');

    document.getElementById('editChapterTitle').value = chapter.title || '';
    document.getElementById('editChapterDescription').value = chapter.description || '';

    modal.style.display = 'flex';

  } catch (error) {
    console.error('Error fetching chapter details:', error);
    alert('Failed to load chapter details');
  }
}

function hideEditChapterModal() {
  document.getElementById('editChapterModal').style.display = 'none';
  document.getElementById('editChapterForm').reset();
}

async function handleEditChapter(event) {
  event.preventDefault();

  const form = event.target;
  const chapterId = form.dataset.chapterId;
  const title = document.getElementById('editChapterTitle').value.trim();
  const description = document.getElementById('editChapterDescription').value.trim();
  const errorDiv = document.getElementById('editChapterError');
  const submitBtn = form.querySelector('button[type="submit"]');

  if (!title) {
    errorDiv.textContent = 'Title is required';
    errorDiv.style.display = 'block';
    return;
  }

  try {
    submitBtn.textContent = 'Saving...';
    submitBtn.disabled = true;
    errorDiv.style.display = 'none';

    const currentUser = getCurrentUser();

    const response = await fetch(`${window.API_BASE_URL}/chapters/${encodeURIComponent(chapterId)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: currentUser.user_id,
        title: title,
        description: description
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to update chapter');
    }

    // Success
    hideEditChapterModal();
    loadChapters(); // Reload list

  } catch (error) {
    console.error('Error updating chapter:', error);
    errorDiv.textContent = error.message;
    errorDiv.style.display = 'block';
  } finally {
    submitBtn.textContent = 'Save Changes';
    submitBtn.disabled = false;
  }
}

// Show Delete Chapter Modal
function showDeleteChapterModal(chapterId) {
  chapterToDeleteId = chapterId;
  const modal = document.getElementById('deleteChapterModal');

  // Attach the click handler for the confirm button
  const confirmBtn = document.getElementById('confirmDeleteChapterBtn');
  confirmBtn.onclick = () => handleDeleteChapter();

  modal.style.display = 'flex';
}

function hideDeleteChapterModal() {
  document.getElementById('deleteChapterModal').style.display = 'none';
  chapterToDeleteId = null;
}

async function handleDeleteChapter() {
  if (!chapterToDeleteId) return;

  const confirmBtn = document.getElementById('confirmDeleteChapterBtn');
  const originalText = confirmBtn.textContent;

  try {
    confirmBtn.textContent = 'Deleting...';
    confirmBtn.disabled = true;

    const currentUser = getCurrentUser();

    const response = await fetch(`${window.API_BASE_URL}/chapters/${encodeURIComponent(chapterToDeleteId)}?user_id=${currentUser.user_id}`, {
      method: 'DELETE'
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to delete chapter');
    }

    // Success
    hideDeleteChapterModal();
    loadChapters(); // Reload list

  } catch (error) {
    console.error('Error deleting chapter:', error);
    alert(`Error: ${error.message}`);
  } finally {
    confirmBtn.textContent = originalText;
    confirmBtn.disabled = false;
  }
}

// Delete Exercise
async function deleteExercise(exerciseId, exerciseTitle) {
  if (!confirm(`Are you sure you want to delete the exercise "${exerciseTitle}"? This action cannot be undone.`)) {
    return;
  }

  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id) {
    alert('Error: User not logged in');
    return;
  }

  try {
    const response = await fetch(`${window.API_BASE_URL}/exercises/${encodeURIComponent(exerciseId)}?user_id=${currentUser.user_id}`, {
      method: 'DELETE'
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to delete exercise');
    }

    // Success - reload exercises
    await loadExercises();

    // Update exercise count in header
    if (currentClassData) {
      currentClassData.exercise_count = Math.max(0, (currentClassData.exercise_count || 1) - 1);
      document.getElementById('exerciseCountStat').textContent = currentClassData.exercise_count;
    }

  } catch (error) {
    console.error('Error deleting exercise:', error);
    alert(`Error deleting exercise: ${error.message}`);
  }
}

// Event delegation for dynamically added buttons
document.addEventListener('DOMContentLoaded', () => {
  document.body.addEventListener('click', (e) => {
    // Handle delete resource button click
    const deleteBtn = e.target.closest('.delete-resource-btn');
    if (deleteBtn) {
      const resourceId = deleteBtn.getAttribute('data-resource-id');
      const chapterId = deleteBtn.getAttribute('data-chapter-id');
      if (resourceId) {
        deleteResource(resourceId, chapterId);
      }
    }

    // Handle edit resource button click
    const editBtn = e.target.closest('.edit-resource-btn');
    if (editBtn) {
      const resourceId = editBtn.getAttribute('data-resource-id');
      if (resourceId) {
        openEditResourceModal(resourceId);
      }
    }
  });
});

// Upload Chapter Modal Functions
function showUploadChapterModal() {
  const modal = document.getElementById('uploadChapterModal');
  document.getElementById('uploadChapterForm').reset();
  document.getElementById('uploadChapterError').style.display = 'none';
  modal.style.display = 'flex';
}

function hideUploadChapterModal() {
  document.getElementById('uploadChapterModal').style.display = 'none';
}

async function handleUploadChapter(event) {
  event.preventDefault();

  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    alert('Error: User not logged in');
    return;
  }

  const title = document.getElementById('chapterTitle').value.trim();
  const description = document.getElementById('chapterDescription').value.trim();
  const pdfFile = document.getElementById('chapterPDF').files[0];
  const exerciseMode = document.querySelector('input[name="exerciseMode"]:checked').value;

  if (!title || !pdfFile) {
    showUploadChapterError('Please fill in all required fields');
    return;
  }

  const errorDiv = document.getElementById('uploadChapterError');
  errorDiv.style.display = 'none';

  const submitButton = event.target.querySelector('button[type="submit"]');
  const originalText = submitButton.textContent;

  try {
    submitButton.disabled = true;
    submitButton.textContent = 'Uploading...';

    const formData = new FormData();
    formData.append('pdf_file', pdfFile);
    formData.append('title', title);
    formData.append('description', description);
    formData.append('exercise_mode', exerciseMode);
    formData.append('user_id', currentUser.user_id);
    formData.append('chapter_number', 999); // Auto-increment

    const response = await fetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters`, {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to upload chapter');
    }

    // Success - close modal and reload chapters
    hideUploadChapterModal();
    await loadChapters();

    // Update chapter count in header
    if (currentClassData) {
      currentClassData.chapter_count = (currentClassData.chapter_count || 0) + 1;
      document.getElementById('chapterCountStat').textContent = currentClassData.chapter_count;
    }

    // If exercises were auto-generated, update exercise count
    if (data.exercises_generated && data.exercises_generated > 0) {
      if (currentClassData) {
        currentClassData.exercise_count = (currentClassData.exercise_count || 0) + data.exercises_generated;
        document.getElementById('exerciseCountStat').textContent = currentClassData.exercise_count;
      }
      alert(`Chapter uploaded successfully! ${data.exercises_generated} exercises were auto-generated.`);
    } else {
      alert('Chapter uploaded successfully!');
    }

  } catch (error) {
    console.error('Error uploading chapter:', error);
    errorDiv.textContent = error.message;
    errorDiv.style.display = 'block';
  } finally {
    submitButton.textContent = originalText;
    submitButton.disabled = false;
  }
}

function showUploadChapterError(message) {
  const errorDiv = document.getElementById('uploadChapterError');
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
}
