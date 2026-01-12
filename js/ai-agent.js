// AI Agent Integration - Code Writer Agent
// Uses Google Gemini

class CodeWriterAgent {
  constructor() {
    this.apiKey = null;
    this.apiProvider = 'gemini';
    this.geminiModel = 'gemini-2.5-flash';
    this.digest = {
      userGoal: '',
      constraints: [],
      decisionsMade: [],
      currentState: [],
      openQuestions: []
    };
    this.conversationHistory = [];
    this.memory = [];
    this.repoContext = null;
  }
  
  // Set Gemini model
  setGeminiModel(model) {
    this.geminiModel = model;
  }

  // Initialize with API key
  async initialize(apiKey, provider = 'gemini', geminiModel = 'gemini-2.5-flash') {
    this.apiKey = apiKey;
    this.apiProvider = 'gemini';
    this.geminiModel = geminiModel;
    await this.loadDigest();
    await this.loadMemory();
    await this.detectRepoContext();
  }

  // Detect repository context
  async detectRepoContext() {
    // Try to detect project type from common files
    const context = {
      stack: 'unknown',
      commands: {},
      entryPoints: []
    };

    // This would ideally check for package.json, requirements.txt, etc.
    // For now, we'll infer from conversation
    this.repoContext = context;
  }

  // Load digest from API
  async loadDigest() {
    try {
      const digest = await aiAgentAPI.getDigest();
      // Transform API response to match internal format
      // API returns: goal, constraints, decisions, current_state, open_questions (as strings or arrays)
      // Internal format expects: userGoal, constraints, decisionsMade, currentState, openQuestions (as arrays)
      
      // Helper function to ensure value is an array
      const ensureArray = (value) => {
        if (Array.isArray(value)) return value;
        if (typeof value === 'string') {
          // If it's a JSON string, try to parse it
          try {
            const parsed = JSON.parse(value);
            return Array.isArray(parsed) ? parsed : (parsed ? [parsed] : []);
          } catch (e) {
            // If parsing fails, treat as empty or single value
            return value.trim() ? [value.trim()] : [];
          }
        }
        return [];
      };
      
      this.digest = {
        userGoal: digest.goal || digest.userGoal || '',
        constraints: ensureArray(digest.constraints || []),
        decisionsMade: ensureArray(digest.decisions || digest.decisionsMade || []),
        currentState: ensureArray(digest.current_state || digest.currentState || []),
        openQuestions: ensureArray(digest.open_questions || digest.openQuestions || [])
      };
    } catch (error) {
      console.error('Error loading digest:', error);
      // Fallback to localStorage
      const saved = localStorage.getItem('codeWriterDigest');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          // Ensure arrays are arrays
          this.digest = {
            userGoal: parsed.userGoal || '',
            constraints: Array.isArray(parsed.constraints) ? parsed.constraints : [],
            decisionsMade: Array.isArray(parsed.decisionsMade) ? parsed.decisionsMade : [],
            currentState: Array.isArray(parsed.currentState) ? parsed.currentState : [],
            openQuestions: Array.isArray(parsed.openQuestions) ? parsed.openQuestions : []
          };
        } catch (e) {
          // If parsing fails, initialize with defaults
          this.digest = {
            userGoal: '',
            constraints: [],
            decisionsMade: [],
            currentState: [],
            openQuestions: []
          };
        }
      }
    }
  }

  // Save digest to API
  async saveDigest() {
    try {
      // Ensure digest has correct format before saving
      const digestToSave = {
        goal: this.digest.userGoal || '',
        constraints: Array.isArray(this.digest.constraints) ? this.digest.constraints : [],
        decisions: Array.isArray(this.digest.decisionsMade) ? this.digest.decisionsMade : [],
        current_state: Array.isArray(this.digest.currentState) ? this.digest.currentState : [],
        open_questions: Array.isArray(this.digest.openQuestions) ? this.digest.openQuestions : []
      };
      await aiAgentAPI.saveDigest(digestToSave);
    } catch (error) {
      console.error('Error saving digest:', error);
      // Fallback to localStorage - ensure arrays are arrays
      const digestToSave = {
        userGoal: this.digest.userGoal || '',
        constraints: Array.isArray(this.digest.constraints) ? this.digest.constraints : [],
        decisionsMade: Array.isArray(this.digest.decisionsMade) ? this.digest.decisionsMade : [],
        currentState: Array.isArray(this.digest.currentState) ? this.digest.currentState : [],
        openQuestions: Array.isArray(this.digest.openQuestions) ? this.digest.openQuestions : []
      };
      localStorage.setItem('codeWriterDigest', JSON.stringify(digestToSave));
    }
  }

  // Load memory from API
  async loadMemory() {
    try {
      const memory = await aiAgentAPI.getMemory();
      this.memory = Array.isArray(memory) ? memory : [];
    } catch (error) {
      console.error('Error loading memory:', error);
      // Fallback to localStorage
      const saved = localStorage.getItem('codeWriterMemory');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          this.memory = Array.isArray(parsed) ? parsed : [];
        } catch (e) {
          this.memory = [];
        }
      } else {
        this.memory = [];
      }
    }
  }

  // Save memory to API
  async saveMemory() {
    try {
      await aiAgentAPI.saveMemory(this.memory);
    } catch (error) {
      console.error('Error saving memory:', error);
      // Fallback to localStorage
      localStorage.setItem('codeWriterMemory', JSON.stringify(this.memory));
    }
  }

  // Update digest from conversation
  updateDigest(userMessage, assistantResponse) {
    // Ensure all digest arrays exist and are arrays
    if (!Array.isArray(this.digest.constraints)) {
      this.digest.constraints = [];
    }
    if (!Array.isArray(this.digest.decisionsMade)) {
      this.digest.decisionsMade = [];
    }
    if (!Array.isArray(this.digest.currentState)) {
      this.digest.currentState = [];
    }
    if (!Array.isArray(this.digest.openQuestions)) {
      this.digest.openQuestions = [];
    }
    
    // Extract goal
    const goalMatch = userMessage.match(/goal:\s*(.+)/i) || 
                     userMessage.match(/I want to (.+)/i) ||
                     userMessage.match(/create (.+)/i) ||
                     userMessage.match(/build (.+)/i);
    if (goalMatch) {
      this.digest.userGoal = goalMatch[1].trim();
    }

    // Extract constraints
    const constraintPatterns = [
      /must\s+(.+?)(?:\.|$)/gi,
      /cannot\s+(.+?)(?:\.|$)/gi,
      /avoid\s+(.+?)(?:\.|$)/gi,
      /only\s+(.+?)(?:\.|$)/gi,
      /don't\s+(.+?)(?:\.|$)/gi
    ];
    constraintPatterns.forEach(pattern => {
      const matches = userMessage.matchAll(pattern);
      for (const match of matches) {
        const constraint = match[1].trim();
        if (constraint && !this.digest.constraints.includes(constraint)) {
          this.digest.constraints.push(constraint);
        }
      }
    });

    // Extract decisions from assistant response
    const decisionPatterns = [
      /Assumption:\s*(.+?)(?:\.|$)/gi,
      /Decision:\s*(.+?)(?:\.|$)/gi,
      /I'm assuming\s+(.+?)(?:\.|$)/gi
    ];
    decisionPatterns.forEach(pattern => {
      const matches = assistantResponse.matchAll(pattern);
      for (const match of matches) {
        const decision = match[1].trim();
        if (decision && !this.digest.decisionsMade.includes(decision)) {
          this.digest.decisionsMade.push(decision);
        }
      }
    });

    // Keep arrays manageable
    this.digest.constraints = this.digest.constraints.slice(0, 20);
    this.digest.decisionsMade = this.digest.decisionsMade.slice(0, 20);
  }

  // Build system prompt
  buildSystemPrompt() {
    // Ensure all digest fields are arrays before calling .map()
    const constraints = Array.isArray(this.digest.constraints) ? this.digest.constraints : [];
    const decisionsMade = Array.isArray(this.digest.decisionsMade) ? this.digest.decisionsMade : [];
    const currentState = Array.isArray(this.digest.currentState) ? this.digest.currentState : [];
    const openQuestions = Array.isArray(this.digest.openQuestions) ? this.digest.openQuestions : [];
    
    const digestText = `
DIGEST:
<UserGoal>${this.digest.userGoal || 'Not set'}</UserGoal>
<Constraints>
${constraints.length > 0 ? constraints.map(c => `- ${c}`).join('\n') : '- None'}
</Constraints>
<DecisionsMade>
${decisionsMade.length > 0 ? decisionsMade.map(d => `- ${d}`).join('\n') : '- None'}
</DecisionsMade>
<CurrentState>
${currentState.length > 0 ? currentState.map(s => `- ${s}`).join('\n') : '- Not detected'}
</CurrentState>
<OpenQuestions>
${openQuestions.length > 0 ? openQuestions.map(q => `- ${q}`).join('\n') : '- None'}
</OpenQuestions>
`;

    const memoryText = this.memory.length > 0 ? `
RelevantMemory:
${this.memory.slice(0, 5).map(m => `- ${m}`).join('\n')}
` : '';

    return `You are a senior-level AI code assistant whose goal is to deliver correct, maintainable, production-ready solutions while communicating clearly and efficiently.

For every request, first identify the user's end goal, constraints (such as language, framework, performance, style, or platform), inputs and outputs, and any ambiguity. If missing information would materially affect correctness, ask concise clarifying questions; otherwise, make reasonable assumptions and state them explicitly.

Structure responses by briefly restating the goal, explaining the chosen approach and reasoning, providing the implementation (code or steps), validating the result with examples, tests, or edge cases, and noting pitfalls and best practices.

When writing code:
- Use modern idiomatic syntax
- Prioritize readability and correctness
- Handle errors and edge cases
- Avoid premature optimization
- Comment on why rather than what
- Include usage examples or tests when appropriate
- Do not output pseudocode unless explicitly requested
- ALL code must be in markdown code blocks (triple backticks with language). Never write code as plain text.
- Code blocks should be ready to copy-paste into Google Colab or any IDE.

Use computation tools when accuracy matters, browsing tools for time-sensitive or factual information, cite external sources when used, and never guess on critical facts.

Communicate in a professional, calm, and supportive tone, use structured formatting when helpful, adapt depth to the user's expertise, and avoid unnecessary filler. Use minimal spacing between sentences and paragraphs. Keep spacing between code blocks and following text to a minimum (no extra blank lines).

When debugging, identify the root cause, explain why it occurs, propose one or more fixes, and explain tradeoffs rather than patching symptoms.

Clearly label assumptions and constraints when they exist, and do not end responses with open loops unless follow-up questions are required for correctness.

${digestText}
${memoryText}`;
  }

  // Call Google Gemini API
  async callGemini(messages) {
    // Convert messages to Gemini format
    const contents = messages
      .filter(m => m.role !== 'system')
      .map(m => ({
        role: m.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: m.content }]
      }));

    // Use selected Gemini model
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${this.geminiModel}:generateContent?key=${this.apiKey}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          contents: contents,
          generationConfig: {
            temperature: 0.7,
            maxOutputTokens: 4000
          }
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      const errorMessage = error.error?.message || 'Gemini API error';
      
      // Check for specific API not enabled error
      if (errorMessage.includes('has not been used') || errorMessage.includes('it is disabled') || errorMessage.includes('Enable it by visiting')) {
        throw new Error(`Generative Language API is not enabled for this API key's project. Please enable the API in Google Cloud Console: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com`);
      }
      
      throw new Error(errorMessage);
    }

    const data = await response.json();
    return data.candidates[0].content.parts[0].text;
  }

  // Process message with AI
  async processMessage(userMessage) {
    // Build messages array
    const messages = [
      {
        role: 'system',
        content: this.buildSystemPrompt()
      },
      ...this.conversationHistory.slice(-10), // Last 10 messages for context
      {
        role: 'user',
        content: userMessage
      }
    ];

    try {
      const response = await this.callGemini(messages);

      // Update digest
      this.updateDigest(userMessage, response);

      // Add to conversation history
      this.conversationHistory.push(
        { role: 'user', content: userMessage },
        { role: 'assistant', content: response }
      );

      // Save digest
      await this.saveDigest();

      // Extract and store durable memories
      this.extractMemories(userMessage, response);

      return response;
    } catch (error) {
      throw new Error(`AI API Error: ${error.message}`);
    }
  }

  // Extract durable memories from conversation
  extractMemories(userMessage, assistantResponse) {
    // Look for durable preferences and decisions
    const memoryPatterns = [
      /(?:prefer|use|always|never)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/gi,
      /(?:stack|framework|library)\s+is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/gi,
      /(?:don't|avoid|never)\s+use\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/gi
    ];

    memoryPatterns.forEach(pattern => {
      const matches = [...userMessage.matchAll(pattern), ...assistantResponse.matchAll(pattern)];
      matches.forEach(match => {
        const memory = match[1] || match[0];
        if (memory && !this.memory.includes(memory)) {
          this.memory.push(memory);
        }
      });
    });

    // Keep memory manageable
    this.memory = this.memory.slice(0, 50);
    this.saveMemory();
  }

  // Clear conversation
  clearConversation() {
    this.conversationHistory = [];
    this.digest = {
      userGoal: '',
      constraints: [],
      decisionsMade: [],
      currentState: [],
      openQuestions: []
    };
    this.saveDigest();
  }
}

// Export singleton instance
const codeWriterAgent = new CodeWriterAgent();

