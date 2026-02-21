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
      <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
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
        button.textContent = '✓ Copied!';
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
      button.textContent = '✓ Copied!';
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
      uiStates.showEmpty(chaptersList, '📄 No chapters yet', 'No chapters have been uploaded for this class yet.');
      return;
    }

    renderChapters(chapters);

  } catch (error) {
    console.error('Error loading chapters:', error);
    chaptersList.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: #fee2e2; border: 1px solid #ef4444; border-radius: 0.5rem; color: #991b1b;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
        <p>Error loading chapters: ${error.message}</p>
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
      uiStates.showEmpty(exercisesList, '✏️ No exercises yet', 'Exercises will appear here once chapters are uploaded.');
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
      uiStates.showEmpty(exercisesList, '✏️ No exercises yet', 'No exercises have been generated for this class yet.');
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
      <div class="practice-grid">
        ${Object.keys(exercisesByChapter).map(chapterId => {
      const chapterData = exercisesByChapter[chapterId];
      return `
            <div class="chapter-section" style="grid-column: 1 / -1; margin-bottom: 2rem;">
              <h2 style="margin-top: 2rem; margin-bottom: 0.5rem; font-size: 1.75rem; border-bottom: 2px solid var(--color-primary); padding-bottom: 0.5rem;">${escapeHtml(chapterData.chapter_title)}</h2>
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
                  <button class="btn btn-primary start-exercise-btn" 
                    data-exercise-id="${escapeHtml(exercise.exercise_id)}" 
                    data-chapter-id="${escapeHtml(exercise.chapter_id)}"
                    data-title="${escapeHtml(exercise.title)}"
                    data-description="${escapeHtml(exercise.description || '')}"
                    data-difficulty="${escapeHtml(exercise.difficulty || 'medium')}">Start Exercise</button>
                </div>
              </div>
            `).join('')}
          `;
    }).join('')}
      </div>
    `;

  } catch (error) {
    console.error('Error loading exercises:', error);
    exercisesList.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: #fee2e2; border: 1px solid #ef4444; border-radius: 0.5rem; color: #991b1b;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
        <p>Error loading exercises: ${error.message}</p>
        <button class="btn btn-primary" onclick="loadExercises()" style="margin-top: 1rem;">Retry</button>
      </div>
    `;
  }
}

// Render chapters (optimized - loads exercises on demand or lazily)
async function renderChapters(chapters) {
  const chaptersList = document.getElementById('chaptersList');

  if (!chapters || chapters.length === 0) {
    uiStates.showEmpty(chaptersList, '📄 No chapters yet', 'No chapters have been uploaded for this class yet.');
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
      <div class="chapter-card" id="${chapterIdAttr}" style="background: white; border: 1px solid var(--border-color); border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: start; ${isTargetChapter ? 'border: 2px solid var(--color-primary); box-shadow: 0 4px 6px -1px var(--color-primary-light);' : ''}">
          <div style="flex: 1;">
          <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
            <span style="background: var(--color-primary); color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.875rem; font-weight: 600;">Chapter ${chapter.chapter_number || ''}</span>
            <h3 style="margin: 0; font-size: 1.25rem;">${escapeHtml(chapter.title)}</h3>
          </div>
          ${chapter.description ? `<p style="color: #64748b; margin-bottom: 0.5rem;">${escapeHtml(chapter.description)}</p>` : ''}
          <div style="font-size: 0.875rem; color: #64748b;">
            ${chapter.created_at ? `<span>Uploaded: ${new Date(chapter.created_at).toLocaleDateString()}</span>` : ''}
          </div>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          ${chapter.pdf_url || chapter.pdf_filename ? `<a href="chapter-view.html?chapter_id=${encodeURIComponent(chapter.chapter_id)}&class_id=${encodeURIComponent(currentClassId)}" class="btn btn-primary" style="text-decoration: none;">View PDF</a>` : ''}
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
      this.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)';
    });
    card.addEventListener('mouseleave', function () {
      this.style.boxShadow = 'none';
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
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid var(--border-color); border-radius: 0.5rem;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">📖</div>
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

      // Type icons and labels
      const typeLabels = {
        'pdf': { icon: '📄', label: 'PDFs & Documents' },
        'tool': { icon: '🛠️', label: 'Tools' },
        'dataset': { icon: '💾', label: 'Datasets' },
        'video': { icon: '🎥', label: 'Videos' },
        'article': { icon: '📝', label: 'Articles' },
        'link': { icon: '🔗', label: 'Links' },
        'csv': { icon: '📊', label: 'Data Files (CSV)' },
        'excel': { icon: '📊', label: 'Excel Worksheets' },
        'ipynb': { icon: '📓', label: 'Jupyter Notebooks' },
        'json': { icon: '⚙️', label: 'JSON Data' },
        'txt': { icon: '📝', label: 'Text Files' }
      };

      resourcesList.innerHTML = Object.keys(groupedByType).map(type => {
        const typeInfo = typeLabels[type] || { icon: '🔗', label: 'Other Resources' };
        const resources = groupedByType[type];

        return `
          <div style="margin-bottom: 2.5rem;">
            <h3 style="margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--border-color); display: flex; align-items: center; gap: 0.5rem;">
              <span>${typeInfo.icon}</span>
              <span>${typeInfo.label}</span>
            </h3>
            <div class="resources-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
              ${resources.map(resource => {
          // DEBUG: Log resource to inspect URL issues
          if (['csv', 'ipynb', 'excel'].includes(resource.resource_type)) {
            console.log('Rendering Resource:', resource.title, resource);
          }
          // Determine Icon
          let icon = '🔗';
          if (typeLabels[resource.resource_type]) {
            icon = typeLabels[resource.resource_type].icon;
          }

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
                  <div class="resource-card" style="background: white; border: 1px solid var(--border-color); border-radius: 0.75rem; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 1px 3px rgba(0,0,0,0.1)';">
                    <div style="font-size: 2rem; margin-bottom: 0.75rem;">${icon}</div>
                    <h3 style="margin: 0 0 0.5rem 0; font-size: 1.125rem;">${escapeHtml(resource.title)}</h3>
                    <p style="color: #64748b; margin: 0 0 1rem 0; font-size: 0.875rem; line-height: 1.5;">${escapeHtml(resource.description || '')}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                      <a href="${escapeHtml(url)}" ${linkTarget} class="resource-link" style="color: var(--color-primary); text-decoration: none; font-weight: 500; font-size: 0.875rem; display: inline-flex; align-items: center; gap: 0.25rem;">
                        ${isDownload ? '⬇️' : ''} ${linkText} ${!isDownload ? '→' : ''}
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
      <div style="text-align: center; padding: 3rem; background: #fee2e2; border: 1px solid #ef4444; border-radius: 0.5rem; color: #991b1b;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
        <p>Error loading resources: ${error.message}</p>
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
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid var(--border-color); border-radius: 0.5rem;">
          <div style="font-size: 3rem; margin-bottom: 1rem;">👥</div>
          <p style="color: #64748b;">No students enrolled yet.</p>
        </div>
      `;
      studentsCount.textContent = '0 students';
    } else {
      studentsCount.textContent = `${students.length} ${students.length === 1 ? 'student' : 'students'}`;

      studentsList.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem;">
          ${students.map(student => `
            <div style="background: white; border: 1px solid var(--border-color); border-radius: 0.5rem; padding: 1rem;">
              <div style="font-weight: 600; margin-bottom: 0.25rem;">${escapeHtml(student.name || student.email || 'Unknown')}</div>
              <div style="font-size: 0.875rem; color: #64748b;">${escapeHtml(student.email || '')}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

  } catch (error) {
    console.error('Error loading students:', error);
    studentsList.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: #fee2e2; border: 1px solid #ef4444; border-radius: 0.5rem; color: #991b1b;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
        <p>Error loading students: ${error.message}</p>
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
            <div style="background: white; border-radius: 0.5rem; border: 1px solid var(--border-color); overflow: hidden; max-width: 800px; margin: 0 auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background: #f8fafc; border-bottom: 2px solid var(--border-color);">
                         <tr>
                            <th style="padding: 1rem; text-align: center; width: 60px;">Rank</th>
                            <th style="padding: 1rem; text-align: left;">Student</th>
                            <th style="padding: 1rem; text-align: right;">Average Score</th>
                         </tr>
                    </thead>
                    <tbody>
                        ${leaderboard.map(student => `
                            <tr style="border-bottom: 1px solid var(--border-color); ${student.student_id === currentUser.user_id ? 'background-color: #eff6ff;' : ''}">
                                <td style="padding: 1rem; text-align: center; font-weight: bold; color: ${student.rank <= 3 ? '#eab308' : '#64748b'};">
                                    ${student.rank === 1 ? '🥇' : student.rank === 2 ? '🥈' : student.rank === 3 ? '🥉' : student.rank}
                                </td>
                                <td style="padding: 1rem; font-weight: 500;">
                                    ${escapeHtml(student.name)}
                                    ${student.student_id === currentUser.user_id ? '<span style="font-size: 0.75rem; background: var(--color-primary); color: white; padding: 2px 6px; border-radius: 4px; margin-left: 0.5rem;">YOU</span>' : ''}
                                </td>
                                <td style="padding: 1rem; text-align: right; font-weight: 600; color: var(--color-primary);">${student.average_score}%</td>
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
    container.innerHTML = '<div style="text-align: center; padding: 3rem; background: #f8fafc; border: 1px solid var(--border-color); border-radius: 0.5rem;"><p style="color: #64748b;">Select an exercise above to see rankings.</p></div>';
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
            <div style="background: white; border-radius: 0.5rem; border: 1px solid var(--border-color); overflow: hidden; max-width: 800px; margin: 0 auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background: #f8fafc; border-bottom: 2px solid var(--border-color);">
                         <tr>
                            <th style="padding: 1rem; text-align: center; width: 60px;">Rank</th>
                            <th style="padding: 1rem; text-align: left;">Student</th>
                            <th style="padding: 1rem; text-align: right;">Best Score</th>
                         </tr>
                    </thead>
                    <tbody>
                        ${leaderboard.map(student => `
                            <tr style="border-bottom: 1px solid var(--border-color); ${student.student_id === currentUser.user_id ? 'background-color: #eff6ff;' : ''}">
                                <td style="padding: 1rem; text-align: center; font-weight: bold; color: ${student.rank <= 3 ? '#eab308' : '#64748b'};">
                                    ${student.rank === 1 ? '🥇' : student.rank === 2 ? '🥈' : student.rank === 3 ? '🥉' : student.rank}
                                </td>
                                <td style="padding: 1rem; font-weight: 500;">
                                    ${escapeHtml(student.name)}
                                    ${student.student_id === currentUser.user_id ? '<span style="font-size: 0.75rem; background: var(--color-primary); color: white; padding: 2px 6px; border-radius: 4px; margin-left: 0.5rem;">YOU</span>' : ''}
                                </td>
                                <td style="padding: 1rem; text-align: right; font-weight: 600; color: var(--color-primary);">${student.score}%</td>
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
});
