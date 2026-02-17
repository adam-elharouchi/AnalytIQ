// AI Agent Integration - Code Writer Agent
// Uses Google Gemini

class CodeWriterAgent {
  constructor() {
    this.apiKey = null;
    this.apiProvider = 'gemini';
    this.geminiModel = 'gemini-3-pro-preview';
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
  async initialize(apiKey, provider = 'gemini', geminiModel = 'gemini-3-pro-preview') {
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

    // Extract current section progress
    const sectionMatch = userMessage.match(/section\s+(\d+)/i) ||
      assistantResponse.match(/section\s+(\d+)/i) ||
      userMessage.match(/step\s+(\d+)/i);

    if (sectionMatch) {
      const sectionNum = sectionMatch[1];
      // Only update if it's a new section or explicit reference
      const sectionText = `Section ${sectionNum}`;
      if (!this.digest.currentState.includes(sectionText) && !this.digest.currentState.some(s => s.startsWith('Completed Section'))) {
        // Clear previous section statuse to keep state clean
        this.digest.currentState = this.digest.currentState.filter(s => !s.startsWith('Section'));
        this.digest.currentState.push(sectionText);
      }
    }

    // Keep arrays manageable
    this.digest.constraints = this.digest.constraints.slice(0, 20);
    this.digest.decisionsMade = this.digest.decisionsMade.slice(0, 20);
    this.digest.currentState = this.digest.currentState.slice(0, 5); // Keep concise state
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

    return `You are a helpful coding assistant for beginners in data science and business analytics. Respond naturally — like a knowledgeable friend, not a documentation generator.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TONE & RESPONSE STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Talk like a normal AI chatbot (ChatGPT / Claude style): one short sentence of context, then the code, then a brief note if it genuinely helps.
- No walls of bullet points. No formal headers. Just natural, friendly text.
- Never start with "Certainly!", "Great question!", "Of course!", or "Sure!".
- If the user pastes code and asks you to extend it, add only what they asked for — don't recap what they already have.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CODE BLOCKS — STRICT RULES (every rule applies every time)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALLOWED inside the code block:
  ✅ Brief label comments where they aid readability (e.g., \`# load dataset\`, \`# fit model\`)
  ✅ One clean solution using the most standard library approach

NEVER put any of these inside the code block — not even once:

1. Attribution / license / author comments
   ❌  # Code source: Gaël Varoquaux
   ❌  # Modified for documentation by Jaques Grobler
   ❌  # License: BSD 3 clause
   → If the user's pasted code contains these, silently remove them.

2. Numbered step comments
   ❌  # 1. Create a DataFrame from the 'data'
   ❌  # 2. Add the 'target' as a new column

3. Section divider comments
   ❌  # --- Create the digits_df DataFrame ---
   ❌  # =====================================

4. Multi-line prose block comments above code sections
   ❌  # Combine the feature data (pixel values) and the target labels
   ❌  # into a single DataFrame.

5. Commented-out optional code
   ❌  # (Your original visualization code, kept here for completeness)
   ❌  # plt.figure(1, figsize=(3, 3))
   ❌  # plt.show()
   → Delete it entirely. The user did not ask for it.

6. "Optional:" sections of any kind

7. Multiple alternative methods (Method 1 / Method 2)

8. try/except blocks unless explicitly requested

9. Exploration calls (.head(), .info(), .describe(), .head(5)) unless the user explicitly asked

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXACT EXAMPLE — what to do when user pastes starter code
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User pastes:
\`\`\`python
# Code source: Gaël Varoquaux
# License: BSD 3 clause

import matplotlib.pyplot as plt
import pandas as pd

from sklearn import datasets

# Load the digits dataset
digits = datasets.load_digits()

# --- Create the digits_df DataFrame ---
# Combine the feature data and labels into a single DataFrame.

# 1. Create a DataFrame from the 'data'
digits_df = pd.DataFrame(data=digits.data)

# 2. Add the 'target' as a new column
digits_df['label'] = digits.target

# Optional: rename columns
pixel_column_names = [f'pixel_{i}' for i in range(digits.data.shape[1])]
digits_df.columns = pixel_column_names + ['label']

print("Shape:", digits_df.shape)
print("\\nFirst 5 rows:")
print(digits_df.head())

# (Original visualization, kept for completeness)
# plt.figure(1, figsize=(3, 3))
# plt.imshow(digits.images[-1])
# plt.show()
\`\`\`
User says: "create a dataframe called digits_df and print the shape"

✅ CORRECT response:
Here you go:

\`\`\`python
from sklearn import datasets
import pandas as pd

digits = datasets.load_digits()

digits_df = pd.DataFrame(digits.data)
digits_df['label'] = digits.target

print(digits_df.shape)
\`\`\`

That gives you a DataFrame with 1797 rows and 65 columns (64 pixel features + the label).

❌ WRONG response: repeating the attribution header, numbered steps, optional renaming block, commented-out plt code, or extra print statements the user didn't ask for.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYNTAX — ALWAYS CORRECT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Always include * for multiplication: \`df['A'] * df['B']\` not \`df['A'] df['B']\`
- Always include commas between arguments and list items
- Code must execute without SyntaxError

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT AWARENESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- If a dataset or library was already imported in this conversation, don't repeat it
- Only output new or changed code — not the entire history
- Reference earlier work naturally: "Using the DataFrame from earlier…"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AFTER THE CODE (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- A 1–3 sentence plain-English note is fine if it adds real value
- No formal "Explanation:" headers, no bullet lists unless the user asked

${digestText}
${memoryText}`;
  }

  // Call Google Gemini API (supports text and images)
  async callGemini(messages, imageData = null) {
    // Convert messages to Gemini format
    const contents = messages
      .filter(m => m.role !== 'system')
      .map((m, index) => {
        const parts = [{ text: m.content }];

        // Add image to the last user message if provided
        if (imageData && index === messages.length - 1 && m.role === 'user') {
          // Extract base64 data from data URL
          const base64Match = imageData.match(/^data:([^;]+);base64,(.+)$/);
          if (base64Match) {
            parts.unshift({
              inlineData: {
                mimeType: base64Match[1],
                data: base64Match[2]
              }
            });
          }
        }

        return {
          role: m.role === 'assistant' ? 'model' : 'user',
          parts: parts
        };
      });

    // Use selected Gemini model
    // Use secure backend proxy instead of direct call
    const response = await authFetch(`${window.API_BASE_URL || '/api'}/ai/chat`,
      {
        method: 'POST',
        body: JSON.stringify({
          model: this.geminiModel,
          contents: contents,
          generationConfig: {
            temperature: 0.7,
            maxOutputTokens: 8192
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

  // Process message with AI (supports optional image data)
  async processMessage(userMessage, context = null, imageData = null) {
    // Build messages array
    // For playground mode (when context is provided), don't include conversation history
    // Each exercise should be treated independently
    // For playground mode, prepend system prompt directly to user message
    // This ensures Gemini receives the full context since system prompts are filtered
    const systemPrompt = context ? this.buildPlaygroundSystemPrompt(context) : this.buildSystemPrompt();

    // Add image context to message if image is provided
    // Always prepend system prompt for main code assistant to ensure Gemini follows instructions
    let finalUserMessage = userMessage;

    if (context) {
      // Playground mode: prepend playground system prompt
      finalUserMessage = `${systemPrompt}\n\nStudent's question: ${userMessage}`;
    } else if (this.conversationHistory.length === 0) {
      // First message in main code assistant: prepend system prompt
      finalUserMessage = `${systemPrompt}\n\nUser request: ${userMessage}`;
    }

    if (imageData && !context) {
      finalUserMessage = `[User has uploaded an image for analysis]\n\n${finalUserMessage}`;
    }

    const messages = [
      // Only include conversation history for main code assistant (not playground mode)
      ...(context ? [] : this.conversationHistory.slice(-10)), // Last 10 messages for context
      {
        role: 'user',
        content: finalUserMessage
      }
    ];

    try {
      const response = await this.callGemini(messages, imageData);

      // Only update digest and conversation history for main code assistant (not playground mode)
      if (!context) {
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
      }

      return response;
    } catch (error) {
      throw new Error(`AI API Error: ${error.message}`);
    }
  }

  // Build system prompt for playground mode (solution-aware hints)
  buildPlaygroundSystemPrompt(context) {
    const { exerciseId, exerciseTitle, exerciseDescription, solutionCode, difficulty, hintLevel = 1, allExercises = [] } = context;

    const hintInstructions = hintLevel === 1
      ? `Provide direct, specific hints with exact module/library names (e.g., "sklearn.datasets" instead of "popular machine learning libraries"). Be concise and actionable. Mention specific modules and functions when relevant, but don't show complete code.`
      : hintLevel === 2
        ? `Provide more direct hints that point toward specific methods or libraries needed. Mention specific function names and modules (e.g., "fetch_california_housing from sklearn.datasets"), but still avoid showing the complete solution code.`
        : `Provide stronger hints with more specific guidance. You can show partial code examples or explain the specific steps needed, but still encourage the student to write their own implementation.`;

    // Build all exercises reference text for context
    let allExercisesText = '';
    if (allExercises && allExercises.length > 0) {
      allExercisesText = `\n\nALL AVAILABLE EXERCISES (for context - you have access to these solutions):
${allExercises.map(ex => `- [${ex.id}] ${ex.title} (${ex.difficulty}, ${ex.chapter})`).join('\n')}

IMPORTANT: You have access to ALL exercise solutions for context and understanding curriculum progression. However, you MUST focus your hints ONLY on the CURRENT EXERCISE below (Exercise ID: ${exerciseId}). Use other exercises' solutions only for understanding progression and concepts, NOT for giving hints about them.`;
    }

    return `You are a solution-aware AI teaching assistant helping a student learn through guided hints in a practice exercise.

🚨 CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. You MUST ALWAYS respond ONLY in the context of the CURRENT EXERCISE below.
2. NEVER give generic life advice, general productivity tips, or answer as if the question is about life in general.
3. ALL questions are about THIS SPECIFIC EXERCISE - interpret them accordingly.
4. If asked "how do I start" - this means "how do I start THIS EXERCISE" - provide a hint about the first step.
5. NEVER ask clarifying questions about what they want to start - they want to start THIS EXERCISE.
6. You have access to ALL exercises' solutions for context, but ALWAYS focus hints on the CURRENT EXERCISE.

CURRENT EXERCISE (you are helping with THIS exercise - focus all hints here):
- Exercise ID: ${exerciseId}
- Title: ${exerciseTitle}
- Description: ${exerciseDescription}
- Difficulty: ${difficulty || 'easy'}
- Hint Level: ${hintLevel} (1=subtle, 2=moderate, 3=strong)

CURRENT EXERCISE SOLUTION (for your understanding only - DO NOT reveal):
\`\`\`python
${solutionCode}
\`\`\`${allExercisesText}

YOUR ROLE:
- Understand the intended solution approach for THIS CURRENT EXERCISE
- Provide targeted hints that nudge the student in the right direction FOR THIS EXERCISE ONLY
- NEVER directly provide the complete solution code
- NEVER give generic advice about life, productivity, habits, or general topics
- ALWAYS interpret questions in the context of THIS CURRENT EXERCISE
- Help students discover the solution through guided learning
- Answer questions about concepts, libraries, or approaches relevant to THIS EXERCISE
- Explain what specific code does if asked
- Use knowledge of other exercises' solutions ONLY for understanding curriculum progression, NOT for hints

HINT STRATEGY (Level ${hintLevel}):
${hintInstructions}

RESPONSE GUIDELINES - ALL QUESTIONS ARE ABOUT THE CURRENT EXERCISE:
- "how do I start" → Mention the exact module/library and function needed (e.g., "import fetch_california_housing from sklearn.datasets" or "import the function from sklearn.datasets"). Be direct and specific, not vague.
- "what do I do" / "what's next" → Hint about the next step in THIS exercise based on the solution, mentioning specific modules/functions when relevant
- "where do I find X" → Provide the exact module/library path (e.g., "sklearn.datasets" not "popular machine learning libraries like scikit-learn")
- "what is the first line of code" → Mention the exact import statement or first action needed (e.g., "import fetch_california_housing from sklearn.datasets" or "import the function from sklearn.datasets")
- "how do I approach this" → Explain the strategy for THIS exercise without showing code
- "what does this code do" / "explain this" → Explain what the code does in the context of THIS exercise
- "stronger hint" / "more help" → Gradually increase specificity
- Always be direct and specific - mention exact modules, libraries, and functions when relevant
- Use a supportive, educational tone
- Keep responses concise and focused (1-3 sentences for subtle hints)
- ALWAYS relate your answer to THIS CURRENT EXERCISE - never generic advice
- Prefer exact module names (e.g., "sklearn.datasets") over vague descriptions (e.g., "well-known machine learning library")

Remember: Your goal is to help students learn THIS CURRENT EXERCISE by guiding them, not by giving them the answer. ALL questions are about THIS EXERCISE. NEVER give generic life or productivity advice. Focus hints on the CURRENT EXERCISE (ID: ${exerciseId}).`;
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

