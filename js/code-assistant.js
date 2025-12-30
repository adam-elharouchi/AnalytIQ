// ChatGPT-style Code Assistant
let currentLanguage = 'python';
let uploadedData = null;
let uploadedFileName = null;
let chatHistory = [];
let lastGeneratedCode = null;
let conversationContext = {
  lastCode: null,
  lastCodeType: null,
  modifications: []
};
let aiProvider = 'gemini'; // Only Gemini supported
let aiAgentInitialized = false;
let geminiModel = 'gemini-2.5-flash'; // Default: Best Balance
const GEMINI_API_KEY = 'AIzaSyAEj5b_MA3Y3oiyhkc1ZXaouRlHqk8C-fY'; // Pre-configured API key
let conversationHistoryList = []; // Store conversation history
let currentConversationId = null;

// Save conversation to history
function saveConversation() {
  const messages = document.querySelectorAll('.message');
  if (messages.length === 0) return;
  
  const firstUserMessage = Array.from(messages).find(msg => msg.classList.contains('user-message'));
  if (!firstUserMessage) return;
  
  const title = firstUserMessage.querySelector('.message-content')?.textContent?.substring(0, 50) || 'New Conversation';
  const conversation = {
    id: currentConversationId || Date.now().toString(),
    title: title,
    date: new Date().toLocaleString(),
    messages: Array.from(messages).map(msg => ({
      role: msg.classList.contains('user-message') ? 'user' : 'assistant',
      content: msg.querySelector('.message-content')?.innerHTML || ''
    }))
  };
  
  // Load existing conversations
  const existing = JSON.parse(localStorage.getItem('conversationHistory') || '[]');
  
  // Update or add conversation
  const index = existing.findIndex(c => c.id === conversation.id);
  if (index >= 0) {
    existing[index] = conversation;
  } else {
    existing.push(conversation);
  }
  
  // Keep only last 50 conversations
  const recent = existing.slice(-50);
  localStorage.setItem('conversationHistory', JSON.stringify(recent));
  conversationHistoryList = recent;
  
  renderConversationHistory();
}

// Load conversation history
function loadConversationHistory() {
  const saved = localStorage.getItem('conversationHistory');
  if (saved) {
    conversationHistoryList = JSON.parse(saved);
  }
  renderConversationHistory();
}

// Render conversation history
function renderConversationHistory() {
  const list = document.getElementById('conversationList');
  if (!list) return;
  
  // Filter out deleted conversations
  const activeConversations = conversationHistoryList.filter(conv => !conv.deleted);
  
  if (activeConversations.length === 0) {
    list.innerHTML = '<p class="no-conversations">No previous conversations</p>';
    return;
  }
  
  list.innerHTML = activeConversations.map(conv => `
    <div class="conversation-item ${conv.id === currentConversationId ? 'active' : ''} ${conv.archived ? 'archived' : ''}">
      <div class="conversation-item-content" onclick="loadConversation('${conv.id}')">
        <div class="conversation-item-title">
          ${conv.archived ? '📦 ' : ''}${escapeHtml(conv.title)}
        </div>
        <div class="conversation-item-date">${conv.date}</div>
      </div>
      <div class="conversation-item-actions">
        <button class="conversation-action-btn archive-btn" 
                onclick="event.stopPropagation(); archiveConversation('${conv.id}')" 
                title="${conv.archived ? 'Unarchive' : 'Archive'}">
          ${conv.archived ? '📤' : '📦'}
        </button>
        <button class="conversation-action-btn delete-btn" 
                onclick="event.stopPropagation(); deleteConversation('${conv.id}')" 
                title="Delete">
          🗑️
        </button>
      </div>
    </div>
  `).join('');
}

// Load a conversation
function loadConversation(conversationId) {
  const conversation = conversationHistoryList.find(c => c.id === conversationId);
  if (!conversation || conversation.deleted) return;
  
  currentConversationId = conversationId;
  
  // Clear current chat
  const messagesContainer = document.getElementById('chatMessages');
  messagesContainer.innerHTML = '';
  
  // Hide welcome section
  const welcomeSection = document.getElementById('conversationStarters');
  if (welcomeSection) {
    welcomeSection.style.display = 'none';
  }
  
  // Load messages
  conversation.messages.forEach(msg => {
    addMessage(msg.role, msg.content, false);
  });
  
  // Update history display
  renderConversationHistory();
  
  // Scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Archive/Unarchive a conversation
function archiveConversation(conversationId) {
  event.stopPropagation();
  const conversation = conversationHistoryList.find(c => c.id === conversationId);
  if (!conversation) return;
  
  conversation.archived = !conversation.archived;
  
  // Save to localStorage
  localStorage.setItem('conversationHistory', JSON.stringify(conversationHistoryList));
  
  // Update display
  renderConversationHistory();
}

// Delete a conversation
function deleteConversation(conversationId) {
  event.stopPropagation();
  
  // Confirm deletion
  if (!confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
    return;
  }
  
  const conversation = conversationHistoryList.find(c => c.id === conversationId);
  if (!conversation) return;
  
  // Mark as deleted instead of removing (for potential recovery)
  conversation.deleted = true;
  conversation.deletedAt = new Date().toISOString();
  
  // If this was the current conversation, start a new one
  if (conversationId === currentConversationId) {
    startNewConversation();
  }
  
  // Save to localStorage
  localStorage.setItem('conversationHistory', JSON.stringify(conversationHistoryList));
  
  // Update display
  renderConversationHistory();
}

// Start new conversation
function startNewConversation() {
  currentConversationId = Date.now().toString();
  chatHistory = [];
  lastGeneratedCode = null;
  conversationContext = {
    lastCode: null,
    lastCodeType: null,
    modifications: []
  };
  const messagesContainer = document.getElementById('chatMessages');
  if (messagesContainer) {
    // Check if welcome section already exists
    let welcomeSection = document.getElementById('conversationStarters');
    if (!welcomeSection) {
      // Recreate welcome section if it doesn't exist
      messagesContainer.innerHTML = `
        <div class="welcome-section" id="conversationStarters">
          <div class="welcome-message">
            <p>Hello! I'm your Code. Just type your request or paste your code below!</p>
          </div>
          <div class="conversation-starters">
            <div class="starter-grid">
              <button class="starter-btn" onclick="useStarter('Analyze sales data and create visualizations')">
                Analyze sales data and create visualizations
              </button>
              <button class="starter-btn" onclick="useStarter('Build a predictive model for customer churn')">
                Build a predictive model for customer churn
              </button>
              <button class="starter-btn" onclick="useStarter('Perform statistical analysis on revenue trends')">
                Perform statistical analysis on revenue trends
              </button>
              <button class="starter-btn" onclick="useStarter('Create a dashboard for business metrics')">
                Create a dashboard for business metrics
              </button>
            </div>
          </div>
        </div>
      `;
    } else {
      // Just clear messages and show welcome section
      messagesContainer.innerHTML = '';
      messagesContainer.appendChild(welcomeSection);
      welcomeSection.style.display = 'block';
    }
  }
  renderConversationHistory();
}

const languageConfig = {
  python: { name: 'Python', extensions: ['.py'] },
  javascript: { name: 'JavaScript', extensions: ['.js', '.jsx'] },
  sql: { name: 'SQL', extensions: ['.sql'] },
  java: { name: 'Java', extensions: ['.java'] },
  cpp: { name: 'C++', extensions: ['.cpp', '.hpp'] },
  r: { name: 'R', extensions: ['.r', '.R'] },
  go: { name: 'Go', extensions: ['.go'] },
  rust: { name: 'Rust', extensions: ['.rs'] },
  html: { name: 'HTML', extensions: ['.html', '.htm'] },
  css: { name: 'CSS', extensions: ['.css'] },
  typescript: { name: 'TypeScript', extensions: ['.ts', '.tsx'] },
  php: { name: 'PHP', extensions: ['.php'] },
  ruby: { name: 'Ruby', extensions: ['.rb'] },
  swift: { name: 'Swift', extensions: ['.swift'] },
  kotlin: { name: 'Kotlin', extensions: ['.kt'] }
};

// Update language
function updateLanguage() {
  const select = document.getElementById('languageSelect');
  currentLanguage = select.value;
  localStorage.setItem('currentLanguage', currentLanguage);
  
  // Update the display
  const display = document.getElementById('languageDisplay');
  if (display) {
    const languageNames = {
      'python': 'Python',
      'javascript': 'JavaScript',
      'sql': 'SQL',
      'java': 'Java',
      'cpp': 'C++',
      'r': 'R',
      'go': 'Go',
      'rust': 'Rust',
      'html': 'HTML',
      'css': 'CSS',
      'typescript': 'TypeScript',
      'php': 'PHP',
      'ruby': 'Ruby',
      'swift': 'Swift',
      'kotlin': 'Kotlin'
    };
    display.textContent = languageNames[currentLanguage] || currentLanguage;
  }
}

// Handle file upload
// Update file input accept attribute based on file type selection
function updateFileInputAccept() {
  const fileTypeSelect = document.getElementById('fileTypeSelect');
  const fileUpload = document.getElementById('fileUpload');
  if (!fileTypeSelect || !fileUpload) return;
  
  const fileType = fileTypeSelect.value;
  let accept = '';
  
  switch(fileType) {
    case 'image':
      accept = 'image/*';
      break;
    case 'text':
      accept = '.txt,.csv,.json,.xml';
      break;
    case 'excel':
      accept = '.xlsx,.xls';
      break;
    case 'ipynb':
      accept = '.ipynb';
      break;
    case 'code':
      accept = '.py,.js,.jsx,.ts,.tsx,.java,.cpp,.c,.h,.hpp,.r,.go,.rs,.html,.css,.php,.rb,.swift,.kt,.sql';
      break;
    default:
      accept = ''; // All files
  }
  
  fileUpload.setAttribute('accept', accept);
}

function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  uploadedFileName = file.name;
  const reader = new FileReader();
  
  // Detect file type
  const extension = '.' + file.name.split('.').pop().toLowerCase();
  
  // Binary file types that need special handling
  const binaryExtensions = ['.xlsx', '.xls', '.ipynb', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.pdf', '.zip', '.tar', '.gz'];
  const isBinary = binaryExtensions.includes(extension);
  
  // Image file types
  const imageExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp'];
  const isImage = imageExtensions.includes(extension);
  
  reader.onload = function(e) {
    let content = e.target.result;
    
    // Detect language from extension for code files
    for (const [lang, config] of Object.entries(languageConfig)) {
      if (config.extensions.includes(extension)) {
        document.getElementById('languageSelect').value = lang;
        updateLanguage();
        break;
      }
    }
    
    // Handle different file types
    if (isImage) {
      uploadedData = { type: 'image', dataUrl: content, fileName: file.name, extension: extension };
      addMessage('user', `📎 Uploaded image: ${file.name}`);
      addMessage('assistant', `Image uploaded successfully! I can help you:\n- Analyze the image\n- Generate code to work with image data\n- Create visualizations or image processing code\n\nWhat would you like to do with this image?`);
    } else if (['.xlsx', '.xls'].includes(extension)) {
      uploadedData = { type: 'excel', fileName: file.name, extension: extension, size: file.size };
      addMessage('user', `📎 Uploaded Excel file: ${file.name}`);
      addMessage('assistant', `Excel file uploaded successfully! I can help you:\n- Generate code to read and process Excel files (using pandas, openpyxl, etc.)\n- Analyze the data structure\n- Create data analysis code\n\nWhat would you like to do with this Excel file?`);
    } else if (extension === '.ipynb') {
      try {
        const notebook = typeof content === 'string' ? JSON.parse(content) : content;
        uploadedData = { type: 'notebook', content: notebook, fileName: file.name };
        addMessage('user', `📎 Uploaded Jupyter notebook: ${file.name}`);
        addMessage('assistant', `Jupyter notebook uploaded successfully! I can help you:\n- Analyze the notebook structure\n- Review and improve the code\n- Debug issues\n- Optimize the code\n\nWhat would you like to do with this notebook?`);
      } catch (error) {
        uploadedData = { type: 'notebook', fileName: file.name, extension: extension, size: file.size };
        addMessage('user', `📎 Uploaded file: ${file.name}`);
        addMessage('assistant', `File uploaded. I can help you work with this Jupyter notebook. What would you like to do with it?`);
      }
    } else if (['.csv', '.json', '.txt'].includes(extension)) {
      uploadedData = parseDataFile(content, extension);
      addMessage('user', `📎 Uploaded file: ${file.name}`);
      addMessage('assistant', `File uploaded successfully! I can help you:\n- Generate code to work with this data\n- Visualize the data (boxplots, histograms, etc.)\n- Analyze the data\n\nWhat would you like to do with this data?`);
    } else if (isBinary && !['.ipynb'].includes(extension)) {
      uploadedData = { type: 'binary', fileName: file.name, extension: extension, size: file.size };
      addMessage('user', `📎 Uploaded file: ${file.name}`);
      addMessage('assistant', `File uploaded successfully! I can help you:\n- Generate code to work with this file type\n- Analyze the file structure\n- Create processing scripts\n\nWhat would you like to do with this file?`);
    } else {
      if (content instanceof ArrayBuffer) {
        uploadedData = { type: 'binary', fileName: file.name, extension: extension, size: file.size };
        addMessage('user', `📎 Uploaded file: ${file.name}`);
        addMessage('assistant', `File uploaded successfully! I can help you generate code to work with this file. What would you like to do?`);
      } else {
        addMessage('user', `📎 Uploaded file: ${file.name}`);
        addMessage('assistant', processCodeFile(content, extension));
      }
    }
  };
  
  // Use appropriate reading method based on file type
  if (isImage) {
    reader.readAsDataURL(file);
  } else if (extension === '.ipynb') {
    reader.readAsText(file);
  } else if (['.xlsx', '.xls', '.pdf', '.zip', '.tar', '.gz'].includes(extension)) {
    uploadedData = { type: 'binary', fileName: file.name, extension: extension, size: file.size };
    addMessage('user', `📎 Uploaded file: ${file.name}`);
    addMessage('assistant', `File uploaded successfully! I can help you:\n- Generate code to read and process this file\n- Analyze the file structure\n- Create data processing scripts\n\nWhat would you like to do with this file?`);
    return;
  } else {
    reader.readAsText(file);
  }
}

// Parse data file
function parseDataFile(content, extension) {
  try {
    if (extension === '.json') {
      return JSON.parse(content);
    } else if (extension === '.csv') {
      return parseCSV(content);
    } else {
      return { type: 'text', content: content };
    }
  } catch (error) {
    return { error: error.message };
  }
}

// Parse CSV
function parseCSV(csv) {
  const lines = csv.trim().split('\n');
  if (lines.length === 0) return [];
  
  const headers = lines[0].split(',').map(h => h.trim());
  const data = [];
  
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(v => v.trim());
    const obj = {};
    headers.forEach((header, index) => {
      const value = values[index] || '';
      obj[header] = isNaN(value) ? value : parseFloat(value);
    });
    data.push(obj);
  }
  
  return { headers, data, type: 'csv' };
}

// Process code file
function processCodeFile(content, extension) {
  const analysis = analyzeCode(content, currentLanguage);
  let response = `I've analyzed your code. Here's what I found:\n\n`;
  
  if (analysis.errors.length > 0) {
    response += `**Errors Found:**\n`;
    analysis.errors.forEach(err => {
      response += `- ${err}\n`;
    });
    response += `\n`;
  }
  
  if (analysis.warnings.length > 0) {
    response += `**Warnings:**\n`;
    analysis.warnings.forEach(warn => {
      response += `- ${warn}\n`;
    });
    response += `\n`;
  }
  
  if (analysis.suggestions.length > 0) {
    response += `**Suggestions:**\n`;
    analysis.suggestions.forEach(sugg => {
      response += `- ${sugg}\n`;
    });
  }
  
  if (analysis.errors.length === 0 && analysis.warnings.length === 0 && analysis.suggestions.length === 0) {
    response += `✅ Your code looks good! No errors or warnings detected.`;
  }
  
  return response;
}

// Update Gemini Model
function updateGeminiModel() {
  const select = document.getElementById('geminiModelSelect');
  geminiModel = select.value;
  localStorage.setItem('geminiModel', geminiModel);
  
  // Update the display
  const display = document.getElementById('geminiModelDisplay');
  if (display) {
    // Show shortened model name
    const modelNames = {
      'gemini-2.5-flash': 'Gemini 2.5',
      'gemini-3-pro-preview': 'Gemini 3 Pro',
      'gemini-3-flash': 'Gemini 3',
      'gemini-1.5-pro': 'Gemini 1.5 Pro'
    };
    display.textContent = modelNames[geminiModel] || 'Gemini';
  }
  
  // Update the AI agent with new model
  if (aiAgentInitialized) {
    codeWriterAgent.setGeminiModel(geminiModel);
  }
}

// Initialize Gemini on page load
function initializeGemini() {
  // Set Gemini as provider
  aiProvider = 'gemini';
  
  // Load saved model preference or use default
  const savedModel = localStorage.getItem('geminiModel') || 'gemini-2.5-flash';
  geminiModel = savedModel;
  
  // Update UI to reflect saved model
  const modelSelect = document.getElementById('geminiModelSelect');
  if (modelSelect) {
    modelSelect.value = geminiModel;
  }
  
  // Set API key in localStorage
  localStorage.setItem('aiApiKey', GEMINI_API_KEY);
  localStorage.setItem('aiProvider', 'gemini');
  
  // Initialize AI agent
  initializeAIAgent();
}

// Test Ollama connection
async function testOllamaConnection() {
  const ollamaUrl = localStorage.getItem('ollamaUrl') || 'http://localhost:11434';
  
  try {
    const response = await fetch(`${ollamaUrl}/api/tags`);
    if (response.ok) {
      const data = await response.json();
      const models = data.models?.map(m => m.name).join(', ') || 'None';
      addMessage('assistant', `✅ Connected to Ollama at ${ollamaUrl}!\n\nAvailable models: ${models}\n\n**Note:** Ollama runs locally on your machine - no API key needed!`);
    } else {
      throw new Error('Ollama not responding');
    }
  } catch (error) {
    addMessage('assistant', `⚠️ Cannot connect to Ollama at ${ollamaUrl}.\n\n**To use Ollama:**\n1. Install Ollama from https://ollama.ai\n2. Run: \`ollama pull llama2\` (or another model)\n3. Make sure Ollama is running\n4. Try again\n\n**Or use Local Intelligence mode** - it works without any setup!`);
  }
}

// Initialize AI Agent
async function initializeAIAgent() {
  const apiKey = localStorage.getItem('aiApiKey') || GEMINI_API_KEY;
  
  if (!apiKey) {
    console.error('Gemini API key not found');
    aiAgentInitialized = false;
    return;
  }
  
  try {
    await codeWriterAgent.initialize(apiKey, 'gemini', geminiModel);
    aiAgentInitialized = true;
    console.log(`Gemini AI agent initialized successfully with model: ${geminiModel}`);
  } catch (error) {
    console.error(`Failed to initialize Gemini AI agent: ${error.message}`);
    aiAgentInitialized = false;
  }
}

// Show API Settings Modal
function showAPISettings() {
  const modal = document.getElementById('apiSettingsModal');
  const apiKey = localStorage.getItem('aiApiKey') || '';
  const provider = localStorage.getItem('aiProvider') || 'ollama';
  const ollamaUrl = localStorage.getItem('ollamaUrl') || 'http://localhost:11434';
  
  document.getElementById('apiKeyInput').value = apiKey;
  document.getElementById('apiProviderSelect').value = provider;
  document.getElementById('ollamaUrlInput').value = ollamaUrl;
  
  // Show/hide Ollama URL field
  const ollamaGroup = document.getElementById('ollamaUrlGroup');
  const apiKeyGroup = document.querySelector('.form-group:has(#apiKeyInput)');
  if (provider === 'ollama') {
    ollamaGroup.style.display = 'block';
    apiKeyGroup.style.display = 'none';
  } else {
    ollamaGroup.style.display = 'none';
    apiKeyGroup.style.display = 'block';
  }
  
  modal.style.display = 'block';
}

// Update form when provider changes
document.addEventListener('DOMContentLoaded', function() {
  const providerSelect = document.getElementById('apiProviderSelect');
  if (providerSelect) {
    providerSelect.addEventListener('change', function() {
      const provider = this.value;
      const ollamaGroup = document.getElementById('ollamaUrlGroup');
      const apiKeyGroup = document.querySelector('.form-group:has(#apiKeyInput)');
      
      if (provider === 'ollama') {
        ollamaGroup.style.display = 'block';
        apiKeyGroup.style.display = 'none';
      } else {
        ollamaGroup.style.display = 'none';
        apiKeyGroup.style.display = 'block';
      }
    });
  }
});

// Close API Settings Modal
function closeAPISettings() {
  document.getElementById('apiSettingsModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
  const modal = document.getElementById('apiSettingsModal');
  if (event.target === modal) {
    closeAPISettings();
  }
}

// Save API Settings
async function saveAPISettings() {
  const provider = document.getElementById('apiProviderSelect').value;
  
  if (provider === 'ollama') {
    const ollamaUrl = document.getElementById('ollamaUrlInput').value.trim() || 'http://localhost:11434';
    localStorage.setItem('ollamaUrl', ollamaUrl);
    localStorage.setItem('aiProvider', provider);
    
    // Update provider selector
    document.getElementById('aiProvider').value = provider;
    aiProvider = provider;
    
    closeAPISettings();
    // Test connection
    await testOllamaConnection();
    return;
  } else {
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    
    if (!apiKey) {
      alert('Please enter an API key');
      return;
    }
    
    localStorage.setItem('aiApiKey', apiKey);
    localStorage.setItem('aiProvider', provider);
    
    // Update provider selector
    document.getElementById('aiProvider').value = provider;
    aiProvider = provider;
    
    // Initialize agent
    await initializeAIAgent();
  }
  
  closeAPISettings();
}

// Send message
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  
  if (!message) return;
  
  // Initialize conversation ID if needed
  if (!currentConversationId) {
    currentConversationId = Date.now().toString();
  }
  
  // Hide welcome section
  const welcomeSection = document.getElementById('conversationStarters');
  if (welcomeSection) {
    welcomeSection.style.display = 'none';
  }
  
  // Add user message
  addMessage('user', message);
  input.value = '';
  
  // Add to conversation history
  chatHistory.push({ role: 'user', content: message });
  
  // Show loading
  const loadingId = addLoadingMessage();
  
  try {
    let response;
    
    // Use Gemini AI
    if (aiAgentInitialized) {
      response = await codeWriterAgent.processMessage(message);
    } else {
      // Fallback to enhanced local processing if Gemini not initialized
      response = localIntelligence.processMessage(message, chatHistory, uploadedData, currentLanguage);
    }
    
    removeLoadingMessage(loadingId);
    addMessage('assistant', response);
    chatHistory.push({ role: 'assistant', content: response });
    
    // Auto-save conversation after a short delay
    setTimeout(() => {
      saveConversation();
    }, 1000);
  } catch (error) {
    removeLoadingMessage(loadingId);
    const errorMessage = `❌ Error: ${error.message}\n\nFalling back to local intelligence...`;
    addMessage('assistant', errorMessage);
    
    // Add error message to chat history
    chatHistory.push({ role: 'assistant', content: errorMessage });
    
    // Fallback to enhanced local processing
    const localResponse = localIntelligence.processMessage(message, chatHistory, uploadedData, currentLanguage);
    addMessage('assistant', localResponse);
    
    // Add fallback response to chat history
    chatHistory.push({ role: 'assistant', content: localResponse });
    
    // Auto-save conversation after a short delay
    setTimeout(() => {
      saveConversation();
    }, 1000);
  }
}


// Handle Enter key
function handleKeyDown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// Process message with conversation context
function processMessageWithContext(message) {
  const lowerMessage = message.toLowerCase();
  
  // Check if this is a follow-up request (modification of previous code)
  if (conversationContext.lastCode && (
      lowerMessage.includes('only') || lowerMessage.includes('just') || 
      lowerMessage.includes('change') || lowerMessage.includes('modify') ||
      lowerMessage.includes('update') || lowerMessage.includes('instead') ||
      lowerMessage.includes('different') || lowerMessage.includes('k ') ||
      lowerMessage.includes('neighbors') || lowerMessage.includes('range') ||
      lowerMessage.includes('1') || lowerMessage.includes('2') || 
      lowerMessage.includes('3') || lowerMessage.includes('4') || 
      lowerMessage.includes('5') || lowerMessage.includes('6') ||
      lowerMessage.includes('7') || lowerMessage.includes('8') ||
      lowerMessage.includes('9') || lowerMessage.includes('10')
  )) {
    return processFollowUpModification(message);
  }
  
  // Check if message contains code (imports, functions, classes, etc.)
  const hasCode = message.includes('import ') || message.includes('from ') || 
                  message.includes('def ') || message.includes('function ') || 
                  message.includes('class ') || message.includes('const ') || 
                  message.includes('let ') || message.includes('var ') ||
                  message.includes('sklearn') || message.includes('numpy') || 
                  message.includes('pandas') || message.includes('matplotlib');
  
  // Check for modification/optimization requests with code context
  if (hasCode && (lowerMessage.includes('modify') || lowerMessage.includes('change') || 
      lowerMessage.includes('optimize') || lowerMessage.includes('improve') || 
      lowerMessage.includes('get') || lowerMessage.includes('highest') || 
      lowerMessage.includes('best') || lowerMessage.includes('tune') ||
      lowerMessage.includes('different') || lowerMessage.includes('update'))) {
    const result = processCodeModification(message);
    // Store the generated code in context
    extractAndStoreCode(result);
    return result;
  }
  
  // Check for code in message (if it looks like code)
  if (hasCode) {
    return processCodeMessage(message);
  }
  
  // Check for visualization requests
  if (lowerMessage.includes('visualize') || lowerMessage.includes('plot') || lowerMessage.includes('chart') ||
      lowerMessage.includes('boxplot') || lowerMessage.includes('histogram') || lowerMessage.includes('confusion matrix')) {
    return processVisualizationRequest(message);
  }
  
  // Check for analysis requests
  if (lowerMessage.includes('analyze') || lowerMessage.includes('explain') || lowerMessage.includes('what does')) {
    if (uploadedData) {
      return processDataAnalysis(message);
    } else {
      return 'Please upload a data file first, or paste code you want me to analyze.';
    }
  }
  
  // Check for code generation
  if (lowerMessage.includes('generate') || lowerMessage.includes('create') || lowerMessage.includes('write') ||
      lowerMessage.includes('make') || lowerMessage.includes('build')) {
    const result = processCodeGeneration(message);
    extractAndStoreCode(result);
    return result;
  }
  
  // Check for data-based code generation
  if (uploadedData && (lowerMessage.includes('code') || lowerMessage.includes('script'))) {
    const result = generateCodeFromData(message);
    extractAndStoreCode(result);
    return result;
  }
  
  // Default: try to generate code
  const result = processCodeGeneration(message);
  extractAndStoreCode(result);
  return result;
}

// Process follow-up modification request
function processFollowUpModification(message) {
  const lowerMessage = message.toLowerCase();
  let modifiedCode = conversationContext.lastCode;
  let explanation = 'I\'ve updated the previous code based on your request:\n\n';
  
  // Handle k range modifications
  if (lowerMessage.includes('k ') || lowerMessage.includes('neighbors') || lowerMessage.includes('only')) {
    // Extract range (e.g., "k 1-5", "only 1 to 5", "k from 1 to 5")
    const rangeMatch = message.match(/(?:k|neighbors?)\s*(?:from|to|is|are|only)?\s*(\d+)\s*(?:to|-|through|and)?\s*(\d+)/i) ||
                       message.match(/(\d+)\s*(?:to|-|through|and)\s*(\d+)/);
    
    if (rangeMatch) {
      const startK = parseInt(rangeMatch[1]);
      const endK = parseInt(rangeMatch[2]);
      
      // Modify the range in the code
      modifiedCode = modifiedCode.replace(/for k in range\(\d+, \d+\)/g, `for k in range(${startK}, ${endK + 1})`);
      modifiedCode = modifiedCode.replace(/range\(1, 21\)/g, `range(${startK}, ${endK + 1})`);
      modifiedCode = modifiedCode.replace(/range\(1, 20\)/g, `range(${startK}, ${endK + 1})`);
      
      explanation += `Changed the k range to test values from ${startK} to ${endK}.\n\n`;
    } else {
      // Single k value
      const singleKMatch = message.match(/(?:k|neighbors?)\s*(?:is|are|only|=\s*)?\s*(\d+)/i) ||
                           message.match(/\b(\d+)\b/);
      if (singleKMatch && conversationContext.lastCode) {
        const kValue = parseInt(singleKMatch[1]);
        modifiedCode = modifiedCode.replace(/n_neighbors\s*=\s*\d+/g, `n_neighbors=${kValue}`);
        explanation += `Changed n_neighbors to ${kValue}.\n\n`;
      }
    }
  }
  
  // Handle other parameter changes
  if (lowerMessage.includes('change') || lowerMessage.includes('modify')) {
    const paramMatches = lowerMessage.match(/(\w+)\s*(?:to|=\s*|=)\s*(\d+|\w+)/g);
    if (paramMatches) {
      paramMatches.forEach(match => {
        const parts = match.match(/(\w+)\s*(?:to|=\s*|=)\s*(\d+|\w+)/);
        if (parts) {
          const param = parts[1];
          const value = parts[2];
          const regex = new RegExp(`(${param}\\s*=\\s*)[^,\\n)]+`, 'gi');
          modifiedCode = modifiedCode.replace(regex, `$1${value}`);
          explanation += `Changed ${param} to ${value}. `;
        }
      });
    }
  }
  
  // Update context
  conversationContext.lastCode = modifiedCode;
  conversationContext.modifications.push(message);
  
  let response = explanation;
  response += formatCodeBlock(modifiedCode, 'python');
  
  return response;
}

// Extract and store code from response
function extractAndStoreCode(response) {
  // Extract code from markdown code blocks
  const codeMatch = response.match(/```[\w]*\n([\s\S]*?)```/);
  if (codeMatch) {
    conversationContext.lastCode = codeMatch[1].trim();
    conversationContext.lastCodeType = 'python';
  }
}

// Process code modification/optimization request
function processCodeModification(message) {
  const lowerMessage = message.toLowerCase();
  
  // Extract the original code
  const codeMatch = message.match(/(?:starter code|code|following code)[\s\S]*?(?=\n\n|$|write|get|create|modify)/i);
  let originalCode = '';
  
  if (codeMatch) {
    originalCode = codeMatch[0].replace(/(?:starter code|code|following code):?\s*/i, '').trim();
  } else {
    // Try to extract code blocks
    const codeBlockMatch = message.match(/```[\s\S]*?```/);
    if (codeBlockMatch) {
      originalCode = codeBlockMatch[0].replace(/```\w*\n?/g, '').replace(/```/g, '').trim();
    } else {
      // Extract code after "The following is" or similar
      const afterFollowing = message.split(/following is|starter code|code:/i);
      if (afterFollowing.length > 1) {
        originalCode = afterFollowing[1].split(/write|get|create|modify/i)[0].trim();
      }
    }
  }
  
  // If no code found, try the whole message
  if (!originalCode || originalCode.length < 50) {
    originalCode = message;
  }
  
  // Analyze the request
  let modifiedCode = originalCode;
  let explanation = '';
  
  // Handle KNN optimization requests
  if (lowerMessage.includes('knn') || lowerMessage.includes('k-neighbors') || lowerMessage.includes('neighbors')) {
    if (lowerMessage.includes('5') || lowerMessage.includes('five')) {
      // Change n_neighbors to 5
      modifiedCode = originalCode.replace(/n_neighbors\s*=\s*\d+/g, 'n_neighbors=5');
      explanation = 'Changed n_neighbors to 5 as requested.';
    }
    
    if (lowerMessage.includes('highest') || lowerMessage.includes('best') || lowerMessage.includes('optimize') || lowerMessage.includes('r2')) {
      // Generate code to find optimal k
      modifiedCode = generateOptimalKNNCode(originalCode);
      explanation = 'Generated code to find the optimal number of neighbors (k) that gives the highest R² score. The code will test different k values and select the best one.';
    }
  }
  
  // Handle general parameter changes
  if (lowerMessage.includes('change') || lowerMessage.includes('modify') || lowerMessage.includes('update')) {
    // Extract parameter changes from the request
    const paramMatches = lowerMessage.match(/(\w+)\s*(?:to|=\s*|=)\s*(\d+|\w+)/g);
    if (paramMatches) {
      paramMatches.forEach(match => {
        const parts = match.match(/(\w+)\s*(?:to|=\s*|=)\s*(\d+|\w+)/);
        if (parts) {
          const param = parts[1];
          const value = parts[2];
          const regex = new RegExp(`(${param}\\s*=\\s*)[^,\\n)]+`, 'gi');
          modifiedCode = modifiedCode.replace(regex, `$1${value}`);
          explanation += `Changed ${param} to ${value}. `;
        }
      });
    }
  }
  
  let response = `**Modified Code:**\n\n`;
  if (explanation) {
    response += `${explanation}\n\n`;
  }
  response += formatCodeBlock(modifiedCode, 'python');
  
  // Store the generated code in context
  conversationContext.lastCode = modifiedCode;
  conversationContext.lastCodeType = 'python';
  
  return response;
}

// Generate optimal KNN code
function generateOptimalKNNCode(originalCode) {
  // Extract key parts from original code
  const hasScaler = originalCode.includes('StandardScaler') || originalCode.includes('scaler');
  const hasTrainTest = originalCode.includes('train_test_split');
  
  let code = `from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import r2_score, mean_squared_error
import numpy as np

# Load dataset
california = fetch_california_housing(as_frame=True)
X = california.data
y = california.target

# Split train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Find optimal k value (testing k from 1 to 20)
best_k = 1
best_r2 = -np.inf
best_mse = np.inf
results = []

print("Testing different k values to find optimal R² score...")
print("-" * 50)

for k in range(1, 21):
    knn_reg = KNeighborsRegressor(
        n_neighbors=k,
        weights='distance',
        p=2,
        n_jobs=-1
    )
    
    knn_reg.fit(X_train_scaled, y_train)
    y_pred = knn_reg.predict(X_test_scaled)
    
    r2 = r2_score(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    
    results.append({'k': k, 'r2': r2, 'mse': mse})
    
    if r2 > best_r2:
        best_r2 = r2
        best_k = k
        best_mse = mse
    
    print(f"k={k:2d} | R² Score: {r2:.6f} | MSE: {mse:.6f}")

print("-" * 50)
print(f"\\nBest k value: {best_k}")
print(f"Best R² Score: {best_r2:.6f}")
print(f"Best MSE: {best_mse:.6f}")

# Train final model with optimal k
print(f"\\nTraining final model with k={best_k}...")
final_knn = KNeighborsRegressor(
    n_neighbors=best_k,
    weights='distance',
    p=2,
    n_jobs=-1
)

final_knn.fit(X_train_scaled, y_train)
y_pred_final = final_knn.predict(X_test_scaled)

final_r2 = r2_score(y_test, y_pred_final)
final_mse = mean_squared_error(y_test, y_pred_final)

print(f"\\nFinal Model Results:")
print(f"R² Score: {final_r2:.6f}")
print(f"MSE: {final_mse:.6f}")`;

  return code;
}

// Process code message (debug/analyze)
function processCodeMessage(message) {
  const analysis = analyzeCode(message, currentLanguage);
  let response = `**Code Analysis:**\n\n`;
  
  if (analysis.errors.length > 0) {
    response += `**❌ Errors:**\n`;
    analysis.errors.forEach(err => {
      response += `- ${err}\n`;
    });
    response += `\n`;
  }
  
  if (analysis.warnings.length > 0) {
    response += `**⚠️ Warnings:**\n`;
    analysis.warnings.forEach(warn => {
      response += `- ${warn}\n`;
    });
    response += `\n`;
  }
  
  if (analysis.suggestions.length > 0) {
    response += `**💡 Suggestions:**\n`;
    analysis.suggestions.forEach(sugg => {
      response += `- ${sugg}\n`;
    });
    response += `\n`;
  }
  
  if (analysis.fixedCode) {
    response += `**✅ Fixed Code:**\n\n`;
    response += formatCodeBlock(analysis.fixedCode, currentLanguage);
  }
  
  if (analysis.errors.length === 0 && analysis.warnings.length === 0) {
    response += `✅ Your code looks good!`;
  }
  
  return response;
}

// Analyze code
function analyzeCode(code, language) {
  const analysis = {
    errors: [],
    warnings: [],
    suggestions: [],
    fixedCode: null
  };
  
  // Syntax checks
  const openBrackets = (code.match(/[\(\[\{]/g) || []).length;
  const closeBrackets = (code.match(/[\)\]\}]/g) || []).length;
  if (openBrackets !== closeBrackets) {
    analysis.errors.push('Mismatched brackets - check for unclosed parentheses, brackets, or braces');
  }
  
  // Language-specific checks
  if (language === 'python') {
    if (code.includes('print ') && !code.includes('print(')) {
      analysis.warnings.push('Python 3 requires print() function, not print statement');
      analysis.fixedCode = code.replace(/print\s+/g, 'print(').replace(/\n/g, ')\n');
    }
    if (code.includes('import *')) {
      analysis.warnings.push('Avoid "import *" - it pollutes the namespace');
    }
  }
  
  if (language === 'javascript') {
    if (code.includes('var ')) {
      analysis.warnings.push('Prefer "let" or "const" over "var"');
      analysis.fixedCode = code.replace(/\bvar\s+/g, 'let ');
    }
    if (code.includes('==') && !code.includes('===')) {
      analysis.warnings.push('Use strict equality (===) instead of loose equality (==)');
    }
  }
  
  // General suggestions
  if (!code.includes('def ') && !code.includes('function ') && code.split('\n').length > 10) {
    analysis.suggestions.push('Consider breaking code into functions for better organization');
  }
  
  return analysis;
}

// Process visualization request
function processVisualizationRequest(message) {
  if (!uploadedData || !uploadedData.data) {
    return 'Please upload a data file first to create visualizations.';
  }
  
  const lowerMessage = message.toLowerCase();
  const visualizationId = 'viz-' + Date.now();
  
  let response = `Creating visualization...\n\n`;
  
  // Determine visualization type
  let vizType = 'histogram';
  if (lowerMessage.includes('boxplot') || lowerMessage.includes('box plot')) {
    vizType = 'boxplot';
  } else if (lowerMessage.includes('histogram')) {
    vizType = 'histogram';
  } else if (lowerMessage.includes('confusion matrix') || lowerMessage.includes('confusion')) {
    vizType = 'confusion';
  } else if (lowerMessage.includes('scatter')) {
    vizType = 'scatter';
  } else if (lowerMessage.includes('bar')) {
    vizType = 'bar';
  } else if (lowerMessage.includes('line')) {
    vizType = 'line';
  }
  
  response += formatCodeBlock(generateVisualizationCode(vizType, uploadedData), currentLanguage);
  response += `\n\n**Visualization:**\n<div id="${visualizationId}" class="visualization-container"></div>`;
  
  // Render visualization after message is added
  setTimeout(() => {
    renderVisualization(visualizationId, vizType, uploadedData);
  }, 100);
  
  return response;
}

// Generate visualization code
function generateVisualizationCode(type, data) {
  if (currentLanguage === 'python') {
    return generatePythonVisualizationCode(type, data);
  } else if (currentLanguage === 'r') {
    return generateRVisualizationCode(type, data);
  } else {
    return generatePythonVisualizationCode(type, data);
  }
}

function generatePythonVisualizationCode(type, data) {
  const numericCols = data.headers ? data.headers.filter((h, i) => {
    const sample = data.data[0];
    return typeof sample[h] === 'number';
  }) : [];
  
  if (type === 'boxplot') {
    return `import matplotlib.pyplot as plt
import pandas as pd

# Load your data
df = pd.read_csv('${uploadedFileName}')

# Create boxplot
plt.figure(figsize=(10, 6))
df.boxplot(column=${numericCols.length > 0 ? `'${numericCols[0]}'` : 'numeric_columns'})
plt.title('Boxplot')
plt.ylabel('Values')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()`;
  } else if (type === 'histogram') {
    return `import matplotlib.pyplot as plt
import pandas as pd

# Load your data
df = pd.read_csv('${uploadedFileName}')

# Create histogram
plt.figure(figsize=(10, 6))
df['${numericCols[0] || 'column_name'}'].hist(bins=30, edgecolor='black')
plt.title('Histogram')
plt.xlabel('${numericCols[0] || 'Values'}')
plt.ylabel('Frequency')
plt.tight_layout()
plt.show()`;
  } else if (type === 'confusion') {
    return `import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix
import numpy as np

# Example confusion matrix (replace with your actual predictions and labels)
y_true = [0, 1, 0, 1, 0, 1, 0, 1]
y_pred = [0, 1, 0, 0, 0, 1, 1, 1]

cm = confusion_matrix(y_true, y_pred)

plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
plt.title('Confusion Matrix')
plt.ylabel('True Label')
plt.xlabel('Predicted Label')
plt.tight_layout()
plt.show()`;
  } else if (type === 'scatter') {
    return `import matplotlib.pyplot as plt
import pandas as pd

# Load your data
df = pd.read_csv('${uploadedFileName}')

# Create scatter plot
plt.figure(figsize=(10, 6))
plt.scatter(df['${numericCols[0] || 'x'}'], df['${numericCols[1] || 'y'}'])
plt.title('Scatter Plot')
plt.xlabel('${numericCols[0] || 'X'}')
plt.ylabel('${numericCols[1] || 'Y'}')
plt.tight_layout()
plt.show()`;
  }
  
  return `# Visualization code for ${type}`;
}

function generateRVisualizationCode(type, data) {
  if (type === 'boxplot') {
    return `# Boxplot in R
data <- read.csv('${uploadedFileName}')
boxplot(data$column_name, main='Boxplot', ylab='Values')`;
  } else if (type === 'histogram') {
    return `# Histogram in R
data <- read.csv('${uploadedFileName}')
hist(data$column_name, main='Histogram', xlab='Values', ylab='Frequency')`;
  }
  return `# R visualization code`;
}

// Render visualization
function renderVisualization(containerId, type, data) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  const canvas = document.createElement('canvas');
  container.appendChild(canvas);
  
  if (!data.data || data.data.length === 0) {
    container.innerHTML = '<p>No data available for visualization</p>';
    return;
  }
  
  const numericCols = data.headers ? data.headers.filter((h, i) => {
    const sample = data.data[0];
    return typeof sample[h] === 'number';
  }) : [];
  
  if (numericCols.length === 0) {
    container.innerHTML = '<p>No numeric columns found for visualization</p>';
    return;
  }
  
  const values = data.data.map(row => parseFloat(row[numericCols[0]])).filter(v => !isNaN(v));
  
  if (type === 'histogram') {
    renderHistogram(canvas, values, numericCols[0]);
  } else if (type === 'boxplot') {
    renderBoxplot(canvas, values, numericCols[0]);
  } else if (type === 'bar') {
    renderBarChart(canvas, data, numericCols[0]);
  } else if (type === 'scatter' && numericCols.length >= 2) {
    renderScatterPlot(canvas, data, numericCols[0], numericCols[1]);
  }
}

// Render histogram
function renderHistogram(canvas, values, label) {
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: Array.from({length: 20}, (_, i) => i),
      datasets: [{
        label: label,
        data: createHistogramData(values, 20),
        backgroundColor: 'rgba(37, 99, 235, 0.8)'
      }]
    },
    options: {
      responsive: true,
      plugins: {
        title: { display: true, text: 'Histogram' },
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

// Render boxplot (using bar chart as approximation)
function renderBoxplot(canvas, values, label) {
  const sorted = [...values].sort((a, b) => a - b);
  const q1 = sorted[Math.floor(sorted.length * 0.25)];
  const q2 = sorted[Math.floor(sorted.length * 0.5)];
  const q3 = sorted[Math.floor(sorted.length * 0.75)];
  const min = Math.min(...sorted);
  const max = Math.max(...sorted);
  
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: ['Min', 'Q1', 'Median', 'Q3', 'Max'],
      datasets: [{
        label: label,
        data: [min, q1, q2, q3, max],
        backgroundColor: 'rgba(16, 185, 129, 0.8)'
      }]
    },
    options: {
      responsive: true,
      plugins: {
        title: { display: true, text: 'Boxplot Statistics' },
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

// Render bar chart
function renderBarChart(canvas, data, column) {
  const grouped = {};
  data.data.forEach(row => {
    const key = String(row[column] || 'Unknown');
    grouped[key] = (grouped[key] || 0) + 1;
  });
  
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: Object.keys(grouped),
      datasets: [{
        label: column,
        data: Object.values(grouped),
        backgroundColor: 'rgba(37, 99, 235, 0.8)'
      }]
    },
    options: {
      responsive: true,
      plugins: {
        title: { display: true, text: 'Bar Chart' }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

// Render scatter plot
function renderScatterPlot(canvas, data, xCol, yCol) {
  const points = data.data.map(row => ({
    x: parseFloat(row[xCol]) || 0,
    y: parseFloat(row[yCol]) || 0
  }));
  
  new Chart(canvas, {
    type: 'scatter',
    data: {
      datasets: [{
        label: `${xCol} vs ${yCol}`,
        data: points,
        backgroundColor: 'rgba(37, 99, 235, 0.6)'
      }]
    },
    options: {
      responsive: true,
      plugins: {
        title: { display: true, text: 'Scatter Plot' }
      },
      scales: {
        x: { title: { display: true, text: xCol } },
        y: { title: { display: true, text: yCol } }
      }
    }
  });
}

// Create histogram data
function createHistogramData(values, bins) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const binWidth = (max - min) / bins;
  const histogram = Array(bins).fill(0);
  
  values.forEach(v => {
    const binIndex = Math.min(Math.floor((v - min) / binWidth), bins - 1);
    histogram[binIndex]++;
  });
  
  return histogram;
}

// Process code generation
function processCodeGeneration(message) {
  const generatedCode = generateCodeFromDescription(message, currentLanguage);
  return `Here's the code I generated for you:\n\n${formatCodeBlock(generatedCode, currentLanguage)}`;
}

// Generate code from description
function generateCodeFromDescription(description, language) {
  const lowerDesc = description.toLowerCase();
  
  // Use existing code generation functions
  if (lowerDesc.includes('factorial') || lowerDesc.includes('fact')) {
    return generateFactorialCode(language);
  } else if (lowerDesc.includes('fibonacci') || lowerDesc.includes('fib')) {
    return generateFibonacciCode(language);
  } else if (lowerDesc.includes('sort')) {
    return generateSortingCode(language);
  } else if (lowerDesc.includes('api') || lowerDesc.includes('endpoint')) {
    return generateAPICode(language);
  } else {
    return generateGenericCode(description, language);
  }
}

// Generate code from data
function generateCodeFromData(message) {
  if (!uploadedData || !uploadedData.data) {
    return 'Please upload a data file first.';
  }
  
  const code = generateDataProcessingCode(uploadedData, currentLanguage);
  return `Here's code to work with your uploaded data:\n\n${formatCodeBlock(code, currentLanguage)}`;
}

// Generate data processing code
function generateDataProcessingCode(data, language) {
  if (language === 'python') {
    return `import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('${uploadedFileName}')

# Basic statistics
print(df.describe())

# Data info
print(df.info())

# First few rows
print(df.head())

# Check for missing values
print(df.isnull().sum())

# Example: Clean data
df_clean = df.dropna()

# Example: Filter data
# df_filtered = df[df['column'] > value]

print(f"Original rows: {len(df)}")
print(f"Cleaned rows: {len(df_clean)}")`;
  }
  return `# Data processing code for ${language}`;
}

// Process data analysis
function processDataAnalysis(message) {
  if (!uploadedData || !uploadedData.data) {
    return 'Please upload a data file first.';
  }
  
  const analysis = analyzeData(uploadedData);
  return formatDataAnalysis(analysis);
}

// Analyze data
function analyzeData(data) {
  if (!data.data || data.data.length === 0) {
    return { error: 'No data to analyze' };
  }
  
  const numericCols = data.headers ? data.headers.filter((h, i) => {
    const sample = data.data[0];
    return typeof sample[h] === 'number';
  }) : [];
  
  const analysis = {
    totalRows: data.data.length,
    columns: data.headers || [],
    numericColumns: numericCols,
    statistics: {}
  };
  
  numericCols.forEach(col => {
    const values = data.data.map(row => parseFloat(row[col])).filter(v => !isNaN(v));
    if (values.length > 0) {
      const sorted = [...values].sort((a, b) => a - b);
      analysis.statistics[col] = {
        mean: values.reduce((a, b) => a + b, 0) / values.length,
        median: sorted[Math.floor(sorted.length / 2)],
        min: Math.min(...values),
        max: Math.max(...values),
        count: values.length
      };
    }
  });
  
  return analysis;
}

// Format data analysis
function formatDataAnalysis(analysis) {
  let response = `**Data Analysis Results:**\n\n`;
  response += `- Total Rows: ${analysis.totalRows}\n`;
  response += `- Columns: ${analysis.columns.join(', ')}\n`;
  response += `- Numeric Columns: ${analysis.numericColumns.join(', ')}\n\n`;
  
  if (Object.keys(analysis.statistics).length > 0) {
    response += `**Statistics:**\n\n`;
    for (const [col, stats] of Object.entries(analysis.statistics)) {
      response += `**${col}:**\n`;
      response += `- Mean: ${stats.mean.toFixed(2)}\n`;
      response += `- Median: ${stats.median.toFixed(2)}\n`;
      response += `- Min: ${stats.min}\n`;
      response += `- Max: ${stats.max}\n`;
      response += `- Count: ${stats.count}\n\n`;
    }
  }
  
  return response;
}

// Add message to chat
function addMessage(role, content, updateVisualizeBtn = true) {
  const messagesContainer = document.getElementById('chatMessages');
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}-message`;
  
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  
  // Format content (handle code blocks, lists, etc.)
  contentDiv.innerHTML = formatMessageContent(content);
  
  messageDiv.appendChild(contentDiv);
  messagesContainer.appendChild(messageDiv);
  
  // Scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  // Copy code buttons
  setTimeout(() => {
    attachCopyButtons();
  }, 100);
}

// Toggle sidebar
function toggleSidebar() {
  const sidebar = document.getElementById('conversationSidebar');
  const fullPage = document.getElementById('codeAssistantPage');
  if (sidebar && fullPage) {
    sidebar.classList.toggle('hidden');
    // Update full page class to reflect sidebar state
    if (sidebar.classList.contains('hidden')) {
      fullPage.classList.add('sidebar-hidden');
      fullPage.classList.remove('sidebar-visible');
    } else {
      fullPage.classList.add('sidebar-visible');
      fullPage.classList.remove('sidebar-hidden');
    }
  }
}


// Format message content
function formatMessageContent(content) {
  // Remove # from text explanations (markdown headers) - but keep them in code blocks
  // First, protect code blocks
  const codeBlockPlaceholders = [];
  let placeholderIndex = 0;
  
  content = content.replace(/```(\w+)?\n([\s\S]*?)```/g, (match) => {
    const placeholder = `__CODE_BLOCK_${placeholderIndex}__`;
    codeBlockPlaceholders[placeholderIndex] = match;
    placeholderIndex++;
    return placeholder;
  });
  
  // Now remove # from text (outside code blocks)
  content = content.replace(/^#+\s+/gm, '');
  
  // Restore code blocks
  codeBlockPlaceholders.forEach((codeBlock, index) => {
    content = content.replace(`__CODE_BLOCK_${index}__`, codeBlock);
  });
  
  // Handle code blocks - make them Colab-ready
  content = content.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    // Clean the code for Colab
    let cleanCode = code.trim();
    cleanCode = cleanCode.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    
    // Remove any nested code fences
    cleanCode = cleanCode.replace(/^```[\w]*\n?/gm, '').replace(/```$/gm, '');
    
    // Preserve newlines by using <pre> or proper formatting
    const language = lang || 'python';
    const escapedCode = escapeHtml(cleanCode);
    
    // Use pre tag to preserve whitespace and newlines
    return `<div class="code-block-container">
      <pre class="code-block" data-language="${language}"><code>${escapedCode}</code></pre>
      <div class="code-block-footer">
        <small>Highlight and copy the code above, then paste it</small>
        <button class="btn-copy-code-footer" onclick="copyCodeFromFooter(this)" title="Copy code">
          <span class="copy-icon">📋</span>
        </button>
      </div>
    </div>`;
  });
  
  // Handle inline code
  content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Handle bold
  content = content.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  
  // Handle line breaks
  content = content.replace(/\n/g, '<br>');
  
  // Handle lists
  content = content.replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>');
  content = content.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
  
  return content;
}

// Format code block for Google Colab compatibility
function formatCodeBlock(code, language) {
  // Clean the code - remove any existing markdown code fences
  let cleanCode = code.replace(/^```[\w]*\n?/gm, '').replace(/```$/gm, '').trim();
  
  // Ensure proper line breaks
  cleanCode = cleanCode.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  
  return `\`\`\`${language}\n${cleanCode}\n\`\`\``;
}

// Escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Add loading message
function addLoadingMessage() {
  const messagesContainer = document.getElementById('chatMessages');
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message assistant-message';
  messageDiv.id = 'loading-message';
  
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  contentDiv.innerHTML = '<div class="loading-indicator"><div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div></div>';
  
  messageDiv.appendChild(contentDiv);
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  return 'loading-message';
}

// Remove loading message
function removeLoadingMessage(id) {
  const loadingMsg = document.getElementById(id);
  if (loadingMsg) {
    loadingMsg.remove();
  }
}

// Attach copy buttons
function attachCopyButtons() {
  document.querySelectorAll('.btn-copy-code').forEach(btn => {
    if (!btn.onclick) {
      btn.onclick = function() {
        const codeBlock = this.closest('.code-block-container').querySelector('.code-block');
        const code = codeBlock.textContent;
        navigator.clipboard.writeText(code).then(() => {
          const originalText = this.textContent;
          this.textContent = 'Copied!';
          setTimeout(() => {
            this.textContent = originalText;
          }, 2000);
        });
      };
    }
  });
}

// Copy code from footer button
function copyCodeFromFooter(button) {
  const codeBlock = button.closest('.code-block-container').querySelector('.code-block');
  
  // Get the raw HTML content first to preserve formatting
  let code = '';
  
  // Try to get text while preserving newlines
  if (codeBlock.textContent) {
    code = codeBlock.textContent;
  } else if (codeBlock.innerText) {
    code = codeBlock.innerText;
  } else {
    // Fallback: get from innerHTML and convert <br> to newlines
    code = codeBlock.innerHTML
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/&nbsp;/g, ' ')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&amp;/g, '&');
    // Remove HTML tags
    const div = document.createElement('div');
    div.innerHTML = code;
    code = div.textContent || div.innerText || '';
  }
  
  // Clean the code - preserve newlines
  let cleanCode = code.trim();
  
  // Ensure proper Unix-style line endings for Colab
  cleanCode = cleanCode.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  
  // Remove any trailing whitespace from lines but keep the newlines
  cleanCode = cleanCode.split('\n').map(line => line.trimEnd()).join('\n');
  
  // Copy to clipboard
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(cleanCode).then(() => {
      const originalText = button.textContent;
      button.textContent = '✅ Copied!';
      button.style.background = '#10b981';
      setTimeout(() => {
        button.textContent = originalText;
        button.style.background = '';
      }, 2000);
    }).catch(err => {
      // Fallback for older browsers
      copyToClipboardFallback(cleanCode, button);
    });
  } else {
    // Fallback for older browsers
    copyToClipboardFallback(cleanCode, button);
  }
}

// Fallback copy function
function copyToClipboardFallback(text, button) {
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
  textArea.style.opacity = '0';
  textArea.style.zIndex = '-1';
  
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  
  try {
    const successful = document.execCommand('copy');
    if (successful) {
      button.textContent = '✅ Copied!';
      button.style.background = '#10b981';
      setTimeout(() => {
        button.textContent = '📋 Copy Code';
        button.style.background = '';
      }, 2000);
    } else {
      button.textContent = '❌ Failed';
      setTimeout(() => {
        button.textContent = '📋 Copy Code';
      }, 2000);
    }
  } catch (err) {
    button.textContent = '❌ Failed';
    setTimeout(() => {
      button.textContent = '📋 Copy Code';
    }, 2000);
  }
  
  document.body.removeChild(textArea);
}

// Clear chat
function clearChat() {
  if (confirm('Clear all chat messages?')) {
    document.getElementById('chatMessages').innerHTML = `
      <div class="welcome-section" id="conversationStarters">
        <div class="welcome-message">
          <p>Hello! I'm your Code Assistant. Just type your request or paste your code below!</p>
        </div>
        <div class="conversation-starters">
          <div class="starter-grid">
            <button class="starter-btn" onclick="useStarter('Create a function to calculate factorial')">
              Create a function to calculate factorial
            </button>
            <button class="starter-btn" onclick="useStarter('Write a REST API endpoint')">
              Write a REST API endpoint
            </button>
            <button class="starter-btn" onclick="useStarter('Debug and fix errors in my code')">
              Debug and fix errors
            </button>
            <button class="starter-btn" onclick="useStarter('Create a histogram visualization')">
              Create a histogram visualization
            </button>
          </div>
        </div>
      </div>
    `;
    chatHistory = [];
    uploadedData = null;
    uploadedFileName = null;
    conversationContext = {
      lastCode: null,
      lastCodeType: null,
      modifications: []
    };
  }
}

// Simple code generation functions (abbreviated versions)
function generateFactorialCode(lang) {
  if (lang === 'python') {
    return `def factorial(n):
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result`;
  }
  return `// Factorial function for ${lang}`;
}

function generateFibonacciCode(lang) {
  if (lang === 'python') {
    return `def fibonacci(n):
    if n <= 0:
        return []
    if n == 1:
        return [0]
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib`;
  }
  return `// Fibonacci function for ${lang}`;
}

function generateSortingCode(lang) {
  if (lang === 'python') {
    return `def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)`;
  }
  return `// Sorting function for ${lang}`;
}

function generateAPICode(lang) {
  if (lang === 'python') {
    return `from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/items', methods=['GET'])
def get_items():
    return jsonify([]), 200

if __name__ == '__main__':
    app.run(debug=True)`;
  }
  return `// API code for ${lang}`;
}

function generateGenericCode(description, lang) {
  if (lang === 'python') {
    return `def process_data(input_data):
    """
    ${description}
    """
    # TODO: Implement functionality
    result = input_data
    return result`;
  }
  return `// Code for: ${description}`;
}

// Use conversation starter
function useStarter(prompt) {
  const input = document.getElementById('chatInput');
  input.value = prompt;
  input.focus();
  
  // Hide conversation starters after selection
  const starters = document.getElementById('conversationStarters');
  if (starters) {
    starters.style.display = 'none';
  }
  
  // Optionally auto-send (you can remove this if you want user to click send)
  // sendMessage();
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
  updateLanguage();
  
  // Load saved AI provider
  const savedProvider = localStorage.getItem('aiProvider') || 'local';
  document.getElementById('aiProvider').value = savedProvider;
  aiProvider = savedProvider;
  
  // Initialize AI agent if configured
  if (savedProvider !== 'local') {
    initializeAIAgent();
  }
  
  // Hide conversation starters after first message
  const chatMessages = document.getElementById('chatMessages');
  const observer = new MutationObserver(function(mutations) {
    const messages = chatMessages.querySelectorAll('.message');
    if (messages.length > 0) { // Any message sent
      const starters = document.getElementById('conversationStarters');
      if (starters && starters.style.display !== 'none') {
        starters.style.display = 'none';
      }
    }
  });
  
  observer.observe(chatMessages, { childList: true });
});
