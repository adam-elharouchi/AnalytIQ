// AI Agent Integration - Code Writer Agent
// Supports OpenAI (ChatGPT) and Google Gemini

class CodeWriterAgent {
  constructor() {
    this.apiKey = null;
    this.apiProvider = 'openai'; // 'openai' or 'gemini'
    this.geminiModel = 'gemini-2.5-flash'; // Default Gemini model
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
  async initialize(apiKey, provider = 'openai', geminiModel = 'gemini-2.5-flash') {
    this.apiKey = apiKey;
    this.apiProvider = provider;
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

  // Load digest from localStorage
  async loadDigest() {
    const saved = localStorage.getItem('codeWriterDigest');
    if (saved) {
      this.digest = JSON.parse(saved);
    }
  }

  // Save digest to localStorage
  async saveDigest() {
    localStorage.setItem('codeWriterDigest', JSON.stringify(this.digest));
  }

  // Load memory from localStorage
  async loadMemory() {
    const saved = localStorage.getItem('codeWriterMemory');
    if (saved) {
      this.memory = JSON.parse(saved);
    }
  }

  // Save memory to localStorage
  async saveMemory() {
    localStorage.setItem('codeWriterMemory', JSON.stringify(this.memory));
  }

  // Update digest from conversation
  updateDigest(userMessage, assistantResponse) {
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
        if (!this.digest.constraints.includes(match[1].trim())) {
          this.digest.constraints.push(match[1].trim());
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
        if (!this.digest.decisionsMade.includes(match[1].trim())) {
          this.digest.decisionsMade.push(match[1].trim());
        }
      }
    });

    // Keep arrays manageable
    this.digest.constraints = this.digest.constraints.slice(0, 20);
    this.digest.decisionsMade = this.digest.decisionsMade.slice(0, 20);
  }

  // Build system prompt
  buildSystemPrompt() {
    const digestText = `
DIGEST:
<UserGoal>${this.digest.userGoal || 'Not set'}</UserGoal>
<Constraints>
${this.digest.constraints.map(c => `- ${c}`).join('\n') || '- None'}
</Constraints>
<DecisionsMade>
${this.digest.decisionsMade.map(d => `- ${d}`).join('\n') || '- None'}
</DecisionsMade>
<CurrentState>
${this.digest.currentState.map(s => `- ${s}`).join('\n') || '- Not detected'}
</CurrentState>
<OpenQuestions>
${this.digest.openQuestions.map(q => `- ${q}`).join('\n') || '- None'}
</OpenQuestions>
`;

    const memoryText = this.memory.length > 0 ? `
RelevantMemory:
${this.memory.slice(0, 5).map(m => `- ${m}`).join('\n')}
` : '';

    return `You are Code Writer, a pragmatic coding agent inside Cursor.
Your job: implement the user's request in their repository with minimal, correct changes.

Always follow this response format unless user asks otherwise:
1) Goal (one sentence)
2) Plan (2-7 bullets)
3) Changes (file-by-file, with code patches or full file blocks)
4) How to run/verify (commands)
5) Notes (tradeoffs, edge cases, next steps)

Rules:
- Prefer smallest correct diff.
- Read existing code before writing new code.
- Do not assume libraries/APIs; verify in repo files or implement behind an interface.
- If blocked, ask at most ONE clarifying question; otherwise proceed with stated assumptions.
- Write idiomatic code, matching existing project style.
- Update or add tests when practical.
- Never fabricate results of commands; if you can run commands, run them. If not, say what would be run.
- Maintain a running DIGEST of the conversation and project facts. Use it to stay consistent.
- Code blocks should be ready to copy-paste into Google Colab or any IDE.

${digestText}
${memoryText}

Before making changes:
- Identify the relevant files.
- Summarize what you found.
- Then patch.

When patching:
- Use apply_patch style diffs when possible.
- Keep changes tight; avoid drive-by refactors.

After patching:
- Provide commands to run.
- Mention any config/env vars needed.`;
  }

  // Call OpenAI API
  async callOpenAI(messages) {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: messages,
        temperature: 0.7,
        max_tokens: 4000
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'OpenAI API error');
    }

    const data = await response.json();
    return data.choices[0].message.content;
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
      throw new Error(error.error?.message || 'Gemini API error');
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
      let response;
      if (this.apiProvider === 'openai') {
        response = await this.callOpenAI(messages);
      } else if (this.apiProvider === 'gemini') {
        response = await this.callGemini(messages);
      } else {
        throw new Error('Unknown API provider');
      }

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

