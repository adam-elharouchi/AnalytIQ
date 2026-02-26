// Student Class View - View Class Details, Chapters, and Exercises
// API_BASE_URL should be defined in api-helper.js

// API_BASE_URL is defined in api-helper.js

let currentClassId = null;
let currentClassData = null;

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

    // Load class details
    const classResponse = await authFetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(classId)}`);
    const classData = await classResponse.json();

    if (!classResponse.ok) {
      throw new Error(classData.error || 'Failed to load class');
    }

    currentClassData = classData;
    renderClassHeader(classData);

    loadingState.style.display = 'none';
    classHeader.style.display = 'block';
    tabsContainer.style.display = 'block';

    // Check if we should switch to exercises tab from URL
    const urlParams = new URLSearchParams(window.location.search);
    const tab = urlParams.get('tab');

    if (tab === 'exercises') {
      switchTab('exercises');
    } else {
      switchTab('chapters');
    }

  } catch (error) {
    console.error('Error loading class:', error);
    loadingState.style.display = 'none';
    loadingState.innerHTML = `
      <h2 style="margin-bottom: 0.5rem;">Error Loading Class</h2>
      <p style="color: #64748b; margin-bottom: 1.5rem;">${error.message}</p>
      <button class="btn btn-primary" onclick="window.location.href='student-classes.html'">Back to Classes</button>
    `;
  }
}

// Render class header
function renderClassHeader(data) {
  document.getElementById('className').textContent = data.name || 'Unnamed Class';
  document.getElementById('classDescription').textContent = data.description || '';
  document.getElementById('classCode').textContent = data.class_id || '';
  document.getElementById('professorName').textContent = data.professor_name || data.professor_email || 'Unknown';
  document.getElementById('studentCountStat').textContent = data.student_count || 0;
  document.getElementById('chapterCountStat').textContent = data.chapter_count || 0;
  document.getElementById('exerciseCountStat').textContent = data.exercise_count || 0;
}

// Copy class code to clipboard (same function as professor)
function copyClassCodeToClipboard() {
  const classCode = document.getElementById('classCode')?.textContent || '';
  if (!classCode) {
    alert('Class code not available');
    return;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(classCode).then(() => {
      const button = document.getElementById('copyCodeBtn');
      const originalText = button?.textContent || '';
      if (button) {
        button.textContent = 'Copied!';
        setTimeout(() => {
          button.textContent = originalText;
        }, 2000);
      }
    }).catch(err => {
      console.error('Failed to copy:', err);
      fallbackCopyTextToClipboard(classCode);
    });
  } else {
    fallbackCopyTextToClipboard(classCode);
  }
}

// Fallback copy function
function fallbackCopyTextToClipboard(text) {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.top = '0';
  textArea.style.left = '0';
  textArea.style.width = '2em';
  textArea.style.height = '2em';
  textArea.style.padding = '0';
  textArea.style.border = 'none';
  textArea.style.outline = 'none';
  textArea.style.boxShadow = 'none';
  textArea.style.background = 'transparent';

  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    const successful = document.execCommand('copy');
    const button = document.getElementById('copyCodeBtn');
    if (successful && button) {
      const originalText = button.textContent || '';
      button.textContent = 'Copied!';
      setTimeout(() => {
        button.textContent = originalText;
      }, 2000);
    } else {
      alert('Failed to copy class code. Please copy manually: ' + text);
    }
  } catch (err) {
    console.error('Fallback copy failed:', err);
    alert('Failed to copy class code. Please copy manually: ' + text);
  }

  document.body.removeChild(textArea);
}

// Load exercises for a chapter
async function loadExercisesForChapter(chapterId) {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id) {
    console.error('No user found');
    return [];
  }

  try {
    const response = await authFetch(`${window.API_BASE_URL}/chapters/${encodeURIComponent(chapterId)}/exercises`);
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

    const response = await authFetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to load chapters');
    }

    const chapters = data.chapters || [];

    if (chapters.length === 0) {
      uiStates.showEmpty(chaptersList, 'No chapters yet', 'No chapters have been uploaded for this class yet.');
      return;
    }

    renderChapters(chapters);

  } catch (error) {
    console.error('Error loading chapters:', error);
    chaptersList.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: rgba(220,38,38,0.1); border: 1px solid rgba(220,38,38,0.3); border-radius: 0.5rem; color: #f87171;">
        <p>Error loading chapters: ${escapeHtml(error.message)}</p>
        <button class="btn btn-primary" onclick="loadChapters()" style="margin-top: 1rem;">Retry</button>
      </div>
    `;
  }
}

// Load all exercises
async function loadExercises() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    return;
  }

  const exercisesList = document.getElementById('exercisesList');

  try {
    exercisesList.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading exercises...</div>';

    // Load all chapters first
    const chaptersResponse = await authFetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters`);
    const chaptersData = await chaptersResponse.json();

    if (!chaptersResponse.ok) {
      throw new Error(chaptersData.error || 'Failed to load chapters');
    }

    const chapters = chaptersData.chapters || [];

    if (chapters.length === 0) {
      uiStates.showEmpty(exercisesList, 'No exercises yet', 'Exercises will appear here once chapters are uploaded.');
      return;
    }

    // Load exercises for all chapters in parallel (performance optimization)
    const exercisePromises = chapters.map(async (chapter) => {
      try {
        const response = await authFetch(`${window.API_BASE_URL}/chapters/${encodeURIComponent(chapter.chapter_id)}/exercises`);
        if (response.ok) {
          const data = await response.json();
          const exercises = data.exercises || [];
          exercises.forEach(ex => {
            ex.chapter_title = chapter.title;
            ex.chapter_id = chapter.chapter_id;
          });
          return exercises;
        }
        return [];
      } catch (err) {
        console.warn(`Failed to load exercises for chapter ${chapter.chapter_id}:`, err);
        return [];
      }
    });

    const exercisesArrays = await Promise.all(exercisePromises);
    const allExercises = exercisesArrays.flat();

    if (allExercises.length === 0) {
      uiStates.showEmpty(exercisesList, 'No exercises yet', 'No exercises have been generated for this class yet.');
      return;
    }

    // Group by chapter (same format as professor)
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

    // Render in practice grid style, grouped by chapter (same as professor, but without edit button)
    exercisesList.innerHTML = `
      <div style="display: grid; gap: 2rem;">
        ${Object.keys(exercisesByChapter).map(chapterId => {
      const chapterData = exercisesByChapter[chapterId];
      return `
            <div class="chapter-section">
              <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
                <h2 style="margin: 0; font-size: 1.25rem; font-family: var(--font-mono); color: #e2e8f0; font-weight: 500;">
                  <span style="color: var(--color-primary);">~/</span>${escapeHtml(chapterData.chapter_title).toLowerCase().replace(/\\s+/g, '_')}
                </h2>
                <div style="flex: 1; height: 1px; background: rgba(255,255,255,0.1);"></div>
              </div>
              <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem;">
                ${chapterData.exercises.map(exercise => {
        const diffColor = exercise.difficulty === 'hard' ? 'var(--color-danger, #ef4444)' : (exercise.difficulty === 'medium' ? 'var(--color-warning, #f59e0b)' : 'var(--color-success, #10b981)');
        return `
                  <div class="practice-card bento-card" style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 1rem; border: 1px solid rgba(255,255,255,0.1); overflow: hidden; display: flex; flex-direction: column; transition: all 0.2s;" onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 12px 40px rgba(0,0,0,0.4)'; this.style.borderColor='rgba(255,255,255,0.2)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none'; this.style.borderColor='rgba(255,255,255,0.1)';">
                    
                    <div style="padding: 1.5rem; flex: 1; display: flex; flex-direction: column;">
                      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                        <h3 style="margin: 0; color: #f8fafc; font-size: 1.15rem; font-weight: 600;">${escapeHtml(exercise.title)}</h3>
                        <span style="background: rgba(0,0,0,0.3); border: 1px solid ${diffColor}; color: ${diffColor}; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-family: var(--font-mono); font-size: 0.7rem; text-transform: uppercase;">${escapeHtml(exercise.difficulty || 'medium')}</span>
                      </div>
                      
                      <p style="color: #94a3b8; font-size: 0.9rem; margin: 0 0 1.5rem 0; line-height: 1.5; flex: 1;">${exercise.description ? escapeHtml(exercise.description) : 'Interactive exercise session.'}</p>
                      
                      <button class="btn btn-primary start-exercise-btn" 
                        data-exercise-id="${escapeHtml(exercise.exercise_id)}" 
                        data-chapter-id="${escapeHtml(exercise.chapter_id)}"
                        data-title="${escapeHtml(exercise.title)}"
                        data-description="${escapeHtml(exercise.description || '')}"
                        data-difficulty="${escapeHtml(exercise.difficulty || 'medium')}"
                        style="width: 100%; background: rgba(37, 105, 244, 0.1); border: 1px solid var(--color-primary); color: var(--color-primary); font-family: var(--font-mono); font-weight: 600; padding: 0.75rem; border-radius: 0.5rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem; transition: all 0.2s;"
                        onmouseover="this.style.background='var(--color-primary)'; this.style.color='white';" 
                        onmouseout="this.style.background='rgba(37, 105, 244, 0.1)'; this.style.color='var(--color-primary)';">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        Execute
                      </button>
                    </div>
                  </div>
                `}).join('')}
              </div>
            </div>
          `;
    }).join('')}
      </div>
    `;

  } catch (error) {
    console.error('Error loading exercises:', error);
    exercisesList.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: rgba(220,38,38,0.1); border: 1px solid rgba(220,38,38,0.3); border-radius: 0.5rem; color: #f87171;">
        <p>Error loading exercises: ${escapeHtml(error.message)}</p>
        <button class="btn btn-primary" onclick="loadExercises()" style="margin-top: 1rem;">Retry</button>
      </div>
    `;
  }
}

// Render chapters (optimized - loads exercises on demand or lazily)
async function renderChapters(chapters) {
  const chaptersList = document.getElementById('chaptersList');

  if (!chapters || chapters.length === 0) {
    uiStates.showEmpty(chaptersList, 'No chapters yet', 'No chapters have been uploaded for this class yet.');
    return;
  }

  let chaptersHTML = '';

  // Check if we should scroll to a specific chapter from URL params
  const urlParams = new URLSearchParams(window.location.search);
  const scrollToChapterId = urlParams.get('chapter_id');

  for (const chapter of chapters) {
    // Don't load exercises immediately - they're loaded separately in exercises tab or on demand
    const exercises = []; // Empty for now - exercises are shown in the Exercises tab

    const chapterIdAttr = `chapter-${chapter.chapter_id}`;
    const isTargetChapter = scrollToChapterId === chapter.chapter_id;

    chaptersHTML += `
      <div class="chapter-card bento-card" id="${chapterIdAttr}" style="background: var(--color-dark); border-radius: 1rem; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 1.5rem; overflow: hidden; position: relative; display: flex; flex-direction: column; transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s; ${isTargetChapter ? 'border-color: var(--color-primary); box-shadow: 0 0 20px rgba(37, 105, 244, 0.4);' : ''}">
        
        <!-- Tab Header -->
        <div style="background: rgba(0,0,0,0.2); padding: 0.75rem 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 0.75rem; font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-muted);">
                <span style="color: var(--color-primary);">[module_${chapter.chapter_number || '0'}]</span>
                <span style="color: #64748b;">// ${chapter.created_at ? new Date(chapter.created_at).toLocaleDateString() : 'system_init'}</span>
            </div>
            <div class="card-indicator" style="width: 8px; height: 8px; border-radius: 50%; background: var(--color-primary); opacity: 0.5; transition: all 0.2s;"></div>
        </div>

        <!-- Content Body -->
        <div style="padding: 2rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1.5rem;">
            <div style="flex: 1; min-width: 250px;">
                <h3 style="margin: 0 0 0.5rem 0; color: #f8fafc; font-size: 1.5rem; font-weight: 600;">${escapeHtml(chapter.title)}</h3>
                ${chapter.description ? `<p style="color: #94a3b8; margin: 0; line-height: 1.6;">${escapeHtml(chapter.description)}</p>` : ''}
            </div>
            
            <div style="display: flex; gap: 1rem;">
                ${chapter.pdf_url || chapter.pdf_filename ? `
                <a href="chapter-view.html?chapter_id=${encodeURIComponent(chapter.chapter_id)}&class_id=${encodeURIComponent(currentClassId)}" 
                   style="text-decoration: none; padding: 0.75rem 1.5rem; background: rgba(37, 105, 244, 0.1); border: 1px solid var(--color-primary); color: var(--color-primary); border-radius: 0.5rem; font-family: var(--font-mono); font-size: 0.9rem; font-weight: 600; display: inline-flex; align-items: center; gap: 0.5rem; transition: background 0.2s;" onmouseover="this.style.background='var(--color-primary)'; this.style.color='white';" onmouseout="this.style.background='rgba(37, 105, 244, 0.1)'; this.style.color='var(--color-primary)';">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                    Init Module
                </a>` : ''}
            </div>
        </div>
      </div>
    `;
  }

  chaptersList.innerHTML = chaptersHTML;

  // Scroll to target chapter if specified in URL
  if (scrollToChapterId) {
    const targetChapter = document.getElementById(`chapter-${scrollToChapterId}`);
    if (targetChapter) {
      setTimeout(() => {
        targetChapter.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // Remove chapter_id from URL without reload
        const newUrl = new URL(window.location);
        newUrl.searchParams.delete('chapter_id');
        window.history.replaceState({}, '', newUrl);
      }, 500);
    }
  }

  // Add hover effect
  const chapterCards = chaptersList.querySelectorAll('.chapter-card');
  chapterCards.forEach(card => {
    card.addEventListener('mouseenter', function () {
      this.style.transform = 'translateY(-4px)';
      this.style.boxShadow = '0 12px 40px rgba(0,0,0,0.4)';
      this.style.borderColor = 'rgba(255,255,255,0.2)';
      const indicator = this.querySelector('.card-indicator');
      if (indicator) {
        indicator.style.opacity = '1';
        indicator.style.boxShadow = '0 0 8px var(--color-primary)';
      }
    });
    card.addEventListener('mouseleave', function () {
      this.style.transform = 'translateY(0)';
      this.style.boxShadow = 'none';
      this.style.borderColor = 'rgba(255,255,255,0.1)';
      const indicator = this.querySelector('.card-indicator');
      if (indicator) {
        indicator.style.opacity = '0.5';
        indicator.style.boxShadow = 'none';
      }
    });
  });
}



// Start exercise - navigate to practice playground (same as professor portal)
function startExercise(exerciseId, chapterId, exerciseTitle, exerciseDescription, exerciseDifficulty) {
  window.location.href = `practice-playground.html?exercise_id=${encodeURIComponent(exerciseId)}&chapter_id=${encodeURIComponent(chapterId)}&class_id=${encodeURIComponent(currentClassId)}&title=${encodeURIComponent(exerciseTitle)}&page_type=student`;
}

// Load resources (read-only for students)
async function loadResources() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    return;
  }

  const resourcesList = document.getElementById('resourcesList');

  try {
    resourcesList.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading resources...</div>';

    const response = await authFetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/resources`);
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

    if (combinedResources.length === 0) {
      resourcesList.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255,255,255,0.07); border-radius: 0.5rem;">
            <p style="color: #64748b;">No resources available yet.</p>
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

      // Type labels
      const typeLabels = {
        'pdf': { label: 'PDFs & Documents' },
        'tool': { label: 'Tools' },
        'dataset': { label: 'Datasets' },
        'video': { label: 'Videos' },
        'article': { label: 'Articles' },
        'link': { label: 'Links' },
        'csv': { label: 'Data Files (CSV)' },
        'excel': { label: 'Excel Worksheets' },
        'ipynb': { label: 'Jupyter Notebooks' },
        'json': { label: 'JSON Data' },
        'txt': { label: 'Text Files' }
      };

      resourcesList.innerHTML = Object.keys(groupedByType).map(type => {
        const typeInfo = typeLabels[type] || { label: 'Other Resources' };
        const resources = groupedByType[type];

        return `
          <div style="margin-bottom: 2.5rem;">
            <h3 style="margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.08); color: #94a3b8; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;">
              ${typeInfo.label}
            </h3>
            <div class="resources-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
              ${resources.map(resource => {
          // DEBUG: Log resource to inspect URL issues
          if (['csv', 'ipynb', 'excel'].includes(resource.resource_type)) {
            console.log('Rendering Resource:', resource.title, resource);
          }
          // Determine type label
          const typeLabel = (typeLabels[resource.resource_type] || { label: resource.resource_type || 'Resource' }).label;

          let url = resource.resource_url || resource.url || '#';
          // Server-relative resource paths (e.g. /api/resources/files/...) are used as-is
          // because API_BASE_URL is same-origin ('/api'), so no origin prepending is needed.

          // Fix missing protocol for typically external resources (datasets, links, videos)
          // Avoid touching 'tool' which can be relative (e.g. code-assistant.html)
          if (url && !url.startsWith('http') && !url.startsWith('/') && !url.startsWith('#') && !url.startsWith('mailto:')) {
            // If it's a dataset, link, video, or article, we assume it's external
            const externalTypes = ['dataset', 'link', 'video', 'article', 'csv', 'excel', 'ipynb', 'json', 'txt'];
            if (externalTypes.includes(resource.resource_type)) {
              url = `https://${url}`;
            }
          }

          let linkTarget = '_blank'; // Default to new tab for everything
          let linkText = 'Visit Resource';
          let isDownload = false;

          // Check if it's a backend download file
          if (url && url.includes('/download')) {
            isDownload = true;
            linkTarget = ''; // Downloads don't need new tab necessarily, but it's fine either way
          }

          // Case 1: Chapter PDF
          if (resource.resource_type === 'pdf' && resource.is_chapter && resource.chapter_id) {
            url = `chapter-view.html?chapter_id=${encodeURIComponent(resource.chapter_id)}&class_id=${encodeURIComponent(currentClassId)}`;
            linkText = 'View PDF';
            linkTarget = ''; // Same tab for app navigation
            isDownload = false;
          }
          // Case 2: Regular PDF
          else if (resource.resource_type === 'pdf') {
            linkText = 'View PDF';
            isDownload = false; // PDFs usually viewed in browser
          }
          // Case 3: File Types (Explicit Download Label)
          else if (['csv', 'excel', 'ipynb', 'json', 'txt', 'dataset'].includes(resource.resource_type)) {
            isDownload = true; // Treat as download for icon purposes unless it's clearly a viewable link
            if (resource.resource_type === 'ipynb') linkText = 'Download Notebook';
            else if (resource.resource_type === 'csv') linkText = 'Download CSV';
            else if (resource.resource_type === 'excel') linkText = 'Download Excel';
            else if (resource.resource_type === 'json') linkText = 'Download JSON';
            else if (resource.resource_type === 'txt') linkText = 'Download Text';
            else if (resource.resource_type === 'dataset') linkText = 'Access Dataset';

            // If it's NOT a backend download (e.g. external link to CSV), still keep new tab
            if (!url.includes('/download')) {
              linkTarget = '_blank';
              // Adjust text if it's likely a viewable external link? 
              // User asked for "Download [Type]", so we stick to that or "Access".
            }
          }
          // Case 4: Link Types
          else {
            linkText = 'Visit Resource';
            if (resource.resource_type === 'video') linkText = 'Watch Video';
            else if (resource.resource_type === 'tool') linkText = 'Open Tool';
            else if (resource.resource_type === 'article') linkText = 'Read Article';

            isDownload = false;
          }

          return `
                  <div class="resource-card" style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 0.75rem; padding: 1.5rem; box-shadow: 0 4px 16px rgba(0,0,0,0.2); transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 24px rgba(0,0,0,0.3)'; this.style.borderColor='rgba(255,255,255,0.15)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 16px rgba(0,0,0,0.2)'; this.style.borderColor='rgba(255,255,255,0.08)';">
                    <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 0.75rem;">${typeLabel}</div>
                    <h3 style="margin: 0 0 0.5rem 0; font-size: 1.125rem; color: #f8fafc;">${escapeHtml(resource.title)}</h3>
                    <p style="color: #94a3b8; margin: 0 0 1rem 0; font-size: 0.875rem; line-height: 1.5;">${escapeHtml(resource.description || '')}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                      <a href="${escapeHtml(url)}" ${linkTarget} class="resource-link" style="color: var(--color-primary); text-decoration: none; font-weight: 500; font-size: 0.875rem; display: inline-flex; align-items: center; gap: 0.25rem;">
                        ${linkText} ${!isDownload ? '→' : ''}
                      </a>
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
      <div style="text-align: center; padding: 3rem; background: rgba(220,38,38,0.1); border: 1px solid rgba(220,38,38,0.3); border-radius: 0.5rem; color: #f87171;">
        <p>Error loading resources: ${escapeHtml(error.message)}</p>
        <button class="btn btn-primary" onclick="loadResources()" style="margin-top: 1rem;">Retry</button>
      </div>
    `;
  }
}

// Load students (read-only for students - shows class roster)
async function loadStudents() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) {
    return;
  }

  const studentsList = document.getElementById('studentsList');
  const studentsCount = document.getElementById('studentsCount');

  try {
    studentsList.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">Loading students...</div>';

    const response = await authFetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/students`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to load students');
    }

    const students = data.students || [];

    if (students.length === 0) {
      studentsList.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255,255,255,0.07); border-radius: 0.5rem;">
          <p style="color: #64748b;">No students enrolled yet.</p>
        </div>
      `;
      studentsCount.textContent = '0 students';
    } else {
      studentsCount.textContent = `${students.length} ${students.length === 1 ? 'student' : 'students'}`;

      studentsList.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem;">
          ${students.map(student => `
            <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 0.5rem; padding: 1rem;">
              <div style="font-weight: 600; margin-bottom: 0.25rem; color: #f8fafc;">${escapeHtml(student.name || student.email || 'Unknown')}</div>
              <div style="font-size: 0.875rem; color: #64748b;">${escapeHtml(student.email || '')}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

  } catch (error) {
    console.error('Error loading students:', error);
    studentsList.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: rgba(220,38,38,0.1); border: 1px solid rgba(220,38,38,0.3); border-radius: 0.5rem; color: #f87171;">
        <p>Error loading students: ${escapeHtml(error.message)}</p>
        <button class="btn btn-primary" onclick="loadStudents()" style="margin-top: 1rem;">Retry</button>
      </div>
    `;
    studentsCount.textContent = '0 students';
  }
}

// Load progress (shows student's own progress)
// Load Progress (Initializes Leaderboard View)
async function loadProgress() {
  const currentUser = getCurrentUser();
  if (!currentUser || !currentUser.user_id || !currentClassId) return;

  // Default to average leaderboard
  switchLeaderboardView('avg');

  // Also populate exercise dropdown for the specific view
  await populateExerciseDropdown();
}

async function populateExerciseDropdown() {
  const dropdown = document.getElementById('studentLbExerciseSelect');
  if (!dropdown) return;

  try {
    const currentUser = getCurrentUser();
    // Fetch exercises using existing logic or endpoint
    // We'll re-use the strategy from loadExercises: fetch chapters then exercises
    const chaptersResponse = await authFetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/chapters`);
    const chaptersData = await chaptersResponse.json();
    const chapters = chaptersData.chapters || [];

    const exercisePromises = chapters.map(async (chapter) => {
      const resp = await authFetch(`${window.API_BASE_URL}/chapters/${encodeURIComponent(chapter.chapter_id)}/exercises`);
      if (!resp.ok) return [];
      const data = await resp.json();
      return data.exercises || [];
    });

    const exercisesArrays = await Promise.all(exercisePromises);
    const allExercises = exercisesArrays.flat();

    dropdown.innerHTML = '<option value="">-- Choose an Exercise --</option>';
    allExercises.forEach(ex => {
      const opt = document.createElement('option');
      opt.value = ex.exercise_id;
      opt.textContent = ex.title;
      dropdown.appendChild(opt);
    });

  } catch (err) {
    console.error("Error populating dropdown", err);
  }
}

// Switch between Average and Exercise Leaderboard
function switchLeaderboardView(viewName) {
  // Hide all
  document.getElementById('lbAvgContainer').style.display = 'none';
  document.getElementById('lbExContainer').style.display = 'none';

  // Reset tabs
  document.getElementById('lbTabAvg').classList.remove('active');
  document.getElementById('lbTabEx').classList.remove('active');

  if (viewName === 'avg') {
    document.getElementById('lbAvgContainer').style.display = 'block';
    document.getElementById('lbTabAvg').classList.add('active');
    loadAvgLeaderboard();
  } else if (viewName === 'exercise') {
    document.getElementById('lbExContainer').style.display = 'block';
    document.getElementById('lbTabEx').classList.add('active');
  }
}

// Load Average Leaderboard
async function loadAvgLeaderboard() {
  const container = document.getElementById('lbAvgContainer');
  container.innerHTML = '<div style="text-align: center; padding: 2rem;">Loading ranking...</div>';

  try {
    const currentUser = getCurrentUser();
    if (!currentUser) return;

    const response = await authFetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/leaderboard/average`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error);

    const leaderboard = data.leaderboard || [];

    if (leaderboard.length === 0) {
      container.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">No data available.</div>';
      return;
    }

    container.innerHTML = `
            <div style="background: rgba(30, 41, 59, 0.6); border-radius: 0.5rem; border: 1px solid rgba(255,255,255,0.08); overflow: hidden; max-width: 800px; margin: 0 auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background: rgba(0,0,0,0.2); border-bottom: 1px solid rgba(255,255,255,0.08);">
                         <tr>
                            <th style="padding: 1rem; text-align: center; width: 60px; color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">Rank</th>
                            <th style="padding: 1rem; text-align: left; color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">Student</th>
                            <th style="padding: 1rem; text-align: right; color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">Average Score</th>
                         </tr>
                    </thead>
                    <tbody>
                        ${leaderboard.map(student => `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); ${student.student_id === currentUser.user_id ? 'background-color: rgba(37, 105, 244, 0.1);' : ''}">
                                <td style="padding: 1rem; text-align: center; font-weight: bold; font-family: var(--font-mono); color: ${student.rank <= 3 ? '#eab308' : '#64748b'};">
                                    ${student.rank === 1 ? '<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:rgba(234,179,8,0.2);border:1px solid rgba(234,179,8,0.5);color:#fbbf24;font-size:0.75rem;font-weight:700;">1</span>' : student.rank === 2 ? '<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:rgba(148,163,184,0.2);border:1px solid rgba(148,163,184,0.5);color:#cbd5e1;font-size:0.75rem;font-weight:700;">2</span>' : student.rank === 3 ? '<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:rgba(180,120,60,0.2);border:1px solid rgba(180,120,60,0.5);color:#c4885a;font-size:0.75rem;font-weight:700;">3</span>' : '<span style="color:#64748b;font-family:var(--font-mono);">#' + student.rank + '</span>'}
                                </td>
                                <td style="padding: 1rem; font-weight: 500; color: #e2e8f0;">
                                    ${escapeHtml(student.name)}
                                    ${student.student_id === currentUser.user_id ? '<span style="font-size: 0.7rem; background: var(--color-primary); color: white; padding: 2px 6px; border-radius: 4px; margin-left: 0.5rem; font-weight: 600;">YOU</span>' : ''}
                                </td>
                                <td style="padding: 1rem; text-align: right; font-weight: 600; color: var(--color-primary); font-family: var(--font-mono);">${student.average_score}%</td>
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
async function loadStudentExerciseLeaderboard(exerciseId) {
  const container = document.getElementById('lbExContent');
  if (!exerciseId) {
    container.innerHTML = '<div style="text-align: center; padding: 3rem; background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255,255,255,0.07); border-radius: 0.5rem;"><p style="color: #64748b;">Select an exercise above to see rankings.</p></div>';
    return;
  }

  container.innerHTML = '<div style="text-align: center; padding: 2rem;">Loading ranking...</div>';

  try {
    const currentUser = getCurrentUser();
    if (!currentUser) return;

    const response = await authFetch(`${window.API_BASE_URL}/classes/${encodeURIComponent(currentClassId)}/leaderboard/exercise/${exerciseId}`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error);

    const leaderboard = data.leaderboard || [];

    if (leaderboard.length === 0) {
      container.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">No submissions yet for this exercise.</div>';
      return;
    }

    container.innerHTML = `
            <div style="background: rgba(30, 41, 59, 0.6); border-radius: 0.5rem; border: 1px solid rgba(255,255,255,0.08); overflow: hidden; max-width: 800px; margin: 0 auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background: rgba(0,0,0,0.2); border-bottom: 1px solid rgba(255,255,255,0.08);">
                         <tr>
                            <th style="padding: 1rem; text-align: center; width: 60px; color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">Rank</th>
                            <th style="padding: 1rem; text-align: left; color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">Student</th>
                            <th style="padding: 1rem; text-align: right; color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">Best Score</th>
                         </tr>
                    </thead>
                    <tbody>
                        ${leaderboard.map(student => `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); ${student.student_id === currentUser.user_id ? 'background-color: rgba(37, 105, 244, 0.1);' : ''}">
                                <td style="padding: 1rem; text-align: center; font-weight: bold; font-family: var(--font-mono); color: ${student.rank <= 3 ? '#eab308' : '#64748b'};">
                                    ${student.rank === 1 ? '<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:rgba(234,179,8,0.2);border:1px solid rgba(234,179,8,0.5);color:#fbbf24;font-size:0.75rem;font-weight:700;">1</span>' : student.rank === 2 ? '<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:rgba(148,163,184,0.2);border:1px solid rgba(148,163,184,0.5);color:#cbd5e1;font-size:0.75rem;font-weight:700;">2</span>' : student.rank === 3 ? '<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:rgba(180,120,60,0.2);border:1px solid rgba(180,120,60,0.5);color:#c4885a;font-size:0.75rem;font-weight:700;">3</span>' : '<span style="color:#64748b;font-family:var(--font-mono);">#' + student.rank + '</span>'}
                                </td>
                                <td style="padding: 1rem; font-weight: 500; color: #e2e8f0;">
                                    ${escapeHtml(student.name)}
                                    ${student.student_id === currentUser.user_id ? '<span style="font-size: 0.7rem; background: var(--color-primary); color: white; padding: 2px 6px; border-radius: 4px; margin-left: 0.5rem; font-weight: 600;">YOU</span>' : ''}
                                </td>
                                <td style="padding: 1rem; text-align: right; font-weight: 600; color: var(--color-primary); font-family: var(--font-mono);">${student.score}%</td>
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

// Event delegation for dynamically added buttons
document.addEventListener('DOMContentLoaded', () => {
  document.body.addEventListener('click', (e) => {
    // Handle start exercise button click
    const startBtn = e.target.closest('.start-exercise-btn');
    if (startBtn) {
      const exerciseId = startBtn.getAttribute('data-exercise-id');
      const chapterId = startBtn.getAttribute('data-chapter-id');
      const title = startBtn.getAttribute('data-title');
      const description = startBtn.getAttribute('data-description');
      const difficulty = startBtn.getAttribute('data-difficulty');
      if (exerciseId && chapterId) {
        startExercise(exerciseId, chapterId, title, description, difficulty);
      }
    }
  });

  // Close embedded playground
  const closeBtn = document.getElementById('closePlaygroundBtn');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      const container = document.getElementById('embeddedPlaygroundContainer');
      const iframe = document.getElementById('playgroundIframe');
      if (container) container.style.display = 'none';
      if (iframe) iframe.src = '';
    });
  }
});
