document.addEventListener('DOMContentLoaded', () => {
    const authManager = new AuthManager();
    if (!authManager.requireAuth()) return;

    // Get class_id from URL
    const urlParams = new URLSearchParams(window.location.search);
    const classId = urlParams.get('class_id');

    if (!classId) {
        alert('Class ID is required');
        window.location.href = 'professor-dashboard.html';
        return;
    }

    // Setup drag and drop
    setupDragAndDrop();

    // Load existing chapters
    loadExistingChapters();
});

let currentClassId = new URLSearchParams(window.location.search).get('class_id');
let generatedExercises = [];
let uploadedFile = null;
let selectedChapterId = null; // For existing chapter selection
let chapterSource = 'new'; // 'new' or 'existing'

function goBack() {
    window.location.href = `professor-class.html?class_id=${currentClassId}`;
}

// Toggle between existing chapter and new upload
function toggleChapterSource(source) {
    chapterSource = source;
    const existingSection = document.getElementById('existingChapterSection');
    const newSection = document.getElementById('newChapterSection');
    const existingActions = document.getElementById('existingChapterActions');
    const existingOption = document.getElementById('existingChapterOption');
    const newOption = document.getElementById('newChapterOption');

    if (source === 'existing') {
        existingSection.style.display = 'block';
        newSection.style.display = 'none';
        existingActions.style.display = 'block';
        existingOption.style.borderColor = 'var(--color-primary)';
        existingOption.style.background = 'rgba(37,105,244,0.12)';
        newOption.style.borderColor = 'var(--border-color)';
        newOption.style.background = '';
    } else {
        existingSection.style.display = 'none';
        newSection.style.display = 'block';
        existingActions.style.display = 'none';
        newOption.style.borderColor = 'var(--color-primary)';
        newOption.style.background = 'rgba(37,105,244,0.12)';
        existingOption.style.borderColor = 'var(--border-color)';
        existingOption.style.background = '';
    }
}

// Load existing chapters for selection
async function loadExistingChapters() {
    const select = document.getElementById('existingChapterSelect');
    try {
        const response = await authFetch(`${API_BASE_URL}/classes/${currentClassId}/chapters`);
        const data = await response.json();

        if (!response.ok) throw new Error(data.error);

        const chapters = data.chapters || [];

        if (chapters.length === 0) {
            select.innerHTML = '<option value="">No chapters available - upload a new one</option>';
        } else {
            select.innerHTML = '<option value="">-- Select a chapter --</option>' +
                chapters.map(ch => `<option value="${ch.chapter_id}">${ch.title}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading chapters:', error);
        select.innerHTML = '<option value="">Error loading chapters</option>';
    }
}

// Generate exercises from existing chapter
async function generateFromExisting() {
    const select = document.getElementById('existingChapterSelect');
    selectedChapterId = select.value;

    if (!selectedChapterId) {
        alert('Please select a chapter');
        return;
    }

    // Switch to process view
    document.getElementById('uploadView').style.display = 'none';
    document.getElementById('processView').style.display = 'block';
    updateStep(2);

    try {
        await processExistingChapter(selectedChapterId);
    } catch (error) {
        console.error("Processing error:", error);
        showProcessError(error.message);
    }
}

// Process existing chapter - generate exercises without re-uploading
async function processExistingChapter(chapterId) {
    updateStage('stageUpload', 'completed'); // Skip upload - already done
    updateStage('stageExtract', 'active');
    updateStage('stageAnalyze', 'active');

    // Generate exercises (backend stores them and returns IDs)
    const response = await authFetch(`${API_BASE_URL}/chapters/${chapterId}/generate-exercises`, {
        method: 'POST',
        body: JSON.stringify({})
    });

    if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to generate exercises');
    }

    const genData = await response.json();

    if (!genData.exercises_generated || genData.exercises_generated === 0) {
        throw new Error('No exercises were generated. Please check if the chapter has valid content.');
    }

    // Fetch the generated exercises from the database
    const exercisesResponse = await authFetch(`${API_BASE_URL}/chapters/${chapterId}/exercises`);
    if (!exercisesResponse.ok) {
        throw new Error('Failed to fetch generated exercises');
    }

    const exercisesData = await exercisesResponse.json();
    generatedExercises = exercisesData.exercises || [];

    if (generatedExercises.length === 0) {
        throw new Error('Exercises were generated but could not be retrieved.');
    }

    updateStage('stageExtract', 'completed');
    updateStage('stageAnalyze', 'completed');

    // Show Review
    setTimeout(() => {
        document.getElementById('processView').style.display = 'none';
        document.getElementById('reviewView').style.display = 'block';
        updateStep(3);
        renderExercises();
    }, 500);
}

function setupDragAndDrop() {
    const dropZone = document.getElementById('dropZone');
    if (!dropZone) return;

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
}

function handleFileSelect(event) {
    handleFiles(event.target.files);
}

function handleFiles(files) {
    if (files.length > 0) {
        const file = files[0];
        if (file.type !== 'application/pdf') {
            alert('Please upload a PDF file');
            return;
        }
        uploadedFile = file;

        // Auto-fill title if empty
        const titleInput = document.getElementById('chapterTitleInput');
        if (!titleInput.value) {
            titleInput.value = file.name.replace('.pdf', '');
        }

        startProcessing();
    }
}

async function startProcessing() {
    const title = document.getElementById('chapterTitleInput').value.trim();
    if (!title) {
        alert('Please enter a chapter title');
        return;
    }

    // Switch to process view
    document.getElementById('uploadView').style.display = 'none';
    document.getElementById('processView').style.display = 'block';
    updateStep(2);

    try {
        await processUpload(uploadedFile, title);
    } catch (error) {
        console.error("Upload processing error:", error);
        showProcessError(error.message);
    }
}

function showProcessError(message) {
    const processView = document.getElementById('processView');
    const errorDiv = document.createElement('div');
    errorDiv.style.marginTop = '2rem';
    errorDiv.style.padding = '1rem';
    errorDiv.style.background = 'var(--color-error-bg, rgba(239,68,68,0.15))';
    errorDiv.style.color = 'var(--color-error-text, #fca5a5)';
    errorDiv.style.borderRadius = '0.5rem';
    errorDiv.style.border = '1px solid var(--color-error-border, #ef4444)';
    errorDiv.innerHTML = `
        <strong>Error:</strong> ${message}<br>
        <button onclick="location.reload()" class="btn btn-secondary" style="margin-top: 1rem;">Try Again</button>
    `;
    processView.appendChild(errorDiv);

    // Mark current stage as failed
    const stages = ['stageUpload', 'stageExtract', 'stageAnalyze'];
    stages.forEach(id => {
        const el = document.getElementById(id);
        if (el && el.classList.contains('active')) {
            el.classList.remove('active');
            el.querySelector('.status-icon').innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f87171" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
            el.style.borderColor = '#dc2626';
        }
    });
}

function updateStep(step) {
    document.querySelectorAll('.step').forEach((el, idx) => {
        if (idx + 1 < step) {
            el.classList.remove('active');
            el.classList.add('completed');
            el.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg><span class="step-label">' + el.querySelector('.step-label').innerText + '</span>';
        } else if (idx + 1 === step) {
            el.classList.add('active');
            el.classList.remove('completed');
        } else {
            el.classList.remove('active', 'completed');
        }
    });
}

function updateStage(stageId, status) {
    const el = document.getElementById(stageId);
    if (!el) return;
    if (status === 'active') {
        el.classList.add('active');
        el.querySelector('.status-icon').innerHTML = '<div class="spinner"></div>';
    } else if (status === 'completed') {
        el.classList.remove('active');
        el.classList.add('completed');
        el.querySelector('.status-icon').innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-success,#10b981)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
    }
}

async function processUpload(file, title) {
    // 1. Upload & Create Chapter first (single upload, no duplicate)
    updateStage('stageUpload', 'active');

    const formData = new FormData();
    formData.append('pdf_file', file);
    formData.append('title', title);
    formData.append('exercise_mode', 'manual'); // Don't auto-generate yet
    formData.append('chapter_number', 999); // Auto-increment ideally

    // Create the chapter first
    const chapterResp = await authFetch(`${API_BASE_URL}/classes/${currentClassId}/chapters`, {
        method: 'POST',
        body: formData
    });

    if (!chapterResp.ok) {
        const errData = await chapterResp.json();
        throw new Error(errData.error || 'Failed to upload chapter');
    }

    const chapterData = await chapterResp.json();
    selectedChapterId = chapterData.chapter_id;

    updateStage('stageUpload', 'completed');

    // 2. Generate exercises from the uploaded chapter
    updateStage('stageExtract', 'active');
    updateStage('stageAnalyze', 'active');

    const response = await authFetch(`${API_BASE_URL}/chapters/${selectedChapterId}/generate-exercises`, {
        method: 'POST',
        body: JSON.stringify({})
    });

    if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to generate exercises');
    }

    const genData = await response.json();

    if (!genData.exercises_generated || genData.exercises_generated === 0) {
        throw new Error('No exercises were generated. Please check if the chapter has valid content.');
    }

    // Fetch the generated exercises from the database
    const exercisesResponse = await authFetch(`${API_BASE_URL}/chapters/${selectedChapterId}/exercises`);
    if (!exercisesResponse.ok) {
        throw new Error('Failed to fetch generated exercises');
    }

    const exercisesData = await exercisesResponse.json();
    generatedExercises = exercisesData.exercises || [];

    if (generatedExercises.length === 0) {
        throw new Error('Exercises were generated but could not be retrieved.');
    }

    updateStage('stageExtract', 'completed');
    updateStage('stageAnalyze', 'completed');

    // 3. Show Review
    setTimeout(() => {
        document.getElementById('processView').style.display = 'none';
        document.getElementById('reviewView').style.display = 'block';
        updateStep(3);
        renderExercises();
    }, 500);
}

function renderExercises() {
    const container = document.getElementById('exercisesContainer');

    if (!generatedExercises || generatedExercises.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 2rem; background: #fef3c7; border: 1px solid #f59e0b; border-radius: 0.5rem;">
                <p style="color: #92400e;">No exercises were generated. Try uploading a different chapter with more content.</p>
                <button class="btn btn-secondary" onclick="restartProcess()" style="margin-top: 1rem;">Start Over</button>
            </div>
        `;
        return;
    }

    container.innerHTML = generatedExercises.map((ex, idx) => `
        <div class="exercise-card">
            <div style="margin-bottom: 1rem;">
                <label style="display: block; font-size: 0.8rem; color: #64748b;">Title</label>
                <input type="text" class="ex-title" value="${escapeHtml(ex.title)}" style="width: 100%; border: 1px solid var(--border-color); padding: 0.5rem; border-radius: 0.25rem;">
            </div>
            <div style="margin-bottom: 1rem;">
                <label style="display: block; font-size: 0.8rem; color: #64748b;">Description</label>
                <textarea class="ex-desc" style="width: 100%; border: 1px solid var(--border-color); padding: 0.5rem; border-radius: 0.25rem; rows: 2;">${escapeHtml(ex.description)}</textarea>
            </div>
            <div style="margin-bottom: 1rem;">
                 <span style="background: ${getDifficultyColor(ex.difficulty)}; color: white; padding: 0.2rem 0.5rem; border-radius: 0.25rem; font-size: 0.8rem;">${ex.difficulty}</span>
            </div>
            <div class="code-preview">
                ${escapeHtml(ex.solution_code)}
            </div>
        </div>
    `).join('');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getDifficultyColor(diff) {
    if (diff === 'easy') return '#10b981';
    if (diff === 'medium') return '#f59e0b';
    return '#ef4444';
}

async function saveAll() {
    // Gather edited data
    const cards = document.querySelectorAll('.exercise-card');
    const finalExercises = Array.from(cards).map((card, idx) => ({
        ...generatedExercises[idx],
        title: card.querySelector('.ex-title').value,
        description: card.querySelector('.ex-desc').value
    }));

    if (!selectedChapterId) {
        alert('Error: No chapter selected');
        return;
    }

    const saveBtn = document.getElementById('saveBtn');
    const originalText = saveBtn.textContent;
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    try {
        // Save all exercises in parallel for speed
        // The exercises already exist (generated in previous step), so we update them using PUT
        const savePromises = finalExercises.map(ex =>
            authFetch(`${API_BASE_URL}/exercises/${ex.exercise_id}`, {
                method: 'PUT',
                body: JSON.stringify({
                    title: ex.title,
                    description: ex.description,
                    difficulty: ex.difficulty,
                    solution_code: ex.solution_code
                })
            }).then(response => {
                if (!response.ok) throw new Error('Failed to save exercise: ' + ex.title);
                return response.json();
            })
        );

        await Promise.all(savePromises);

        alert('Exercises saved successfully!');
        window.location.href = `professor-class.html?class_id=${currentClassId}`;

    } catch (error) {
        alert('Error saving: ' + error.message);
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
    }
}

function restartProcess() {
    location.reload();
}
