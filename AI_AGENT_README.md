# AI Agent Integration - Code Assistant

## Overview

The Code Assistant supports **three modes**:
1. **Local Intelligence (Default)** - Enhanced rule-based system, **NO API needed**
2. **Ollama** - Local LLM running on your machine, **NO API key needed**
3. **External APIs** - OpenAI (ChatGPT) or Google Gemini (requires API keys)

## Local Intelligence Mode (Recommended - No API Required)

The **Local Intelligence** mode is the default and works entirely in your browser with **no external APIs or API keys needed**. It features:

- **Advanced pattern matching** for code generation
- **Context-aware modifications** of previous code
- **Conversation memory** across messages
- **Intelligent code analysis** and suggestions
- **Comprehensive code templates** for common tasks
- **Follow-up request handling** (e.g., "I only want k 1-5")

### How It Works

The local intelligence engine:
1. Analyzes your message to detect intent
2. Extracts code, parameters, and requirements
3. Maintains conversation context
4. Generates appropriate code using advanced templates
5. Handles follow-up modifications intelligently

### Example

**You:** "Create KNN code to find optimal k"  
**Local AI:** [Generates code with optimization loop]

**You:** "I only want k 1-5"  
**Local AI:** [Modifies previous code to use range(1, 6)]

No API calls, no keys, works offline!

## Features

### 1. **AI Provider Selection**
- **Local (Rule-based)**: Default mode using pattern matching and templates
- **OpenAI (ChatGPT)**: Uses GPT-4o-mini for intelligent code assistance
- **Google Gemini**: Uses Gemini Pro for code generation

### 2. **Conversation Memory**
- **DIGEST System**: Maintains session memory with:
  - User Goal
  - Constraints
  - Decisions Made
  - Current State
  - Open Questions
- **Long-term Memory**: Stores durable preferences and project facts
- **Context Awareness**: Remembers previous code and modifications

### 3. **Response Format**
The AI agent follows a structured format:
1. **Goal** (one sentence)
2. **Plan** (2-7 bullets)
3. **Changes** (file-by-file with code blocks)
4. **How to run/verify** (commands)
5. **Notes** (tradeoffs, edge cases, next steps)

### 4. **Behavioral Patterns**
- Asks at most ONE clarifying question if blocked
- Proceeds with stated assumptions otherwise
- Prefers minimal, correct changes
- Maintains conversation context across messages
- Formats code ready for Google Colab

## Setup Instructions

### Option 1: Use Local Intelligence (No Setup Required!)

**This is the default mode** - just start using it! No API keys, no setup needed.

The local intelligence system handles:
- Code generation for common patterns
- Code modification and optimization
- Conversation context
- Follow-up requests
- Code analysis

### Option 2: Use Ollama (Local LLM - No API Key)

Ollama runs a language model locally on your machine - no API key needed!

1. **Install Ollama**: Visit https://ollama.ai and install
2. **Download a model**: Run `ollama pull llama2` (or another model)
3. **Configure in Code Assistant**:
   - Click ⚙️ API button
   - Select "Ollama (Local - No API Key)"
   - Enter Ollama URL (default: http://localhost:11434)
   - Click Save

### Option 3: Use External APIs

### Step 1: Get API Keys

**For OpenAI:**
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key

**For Google Gemini:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy the key

### Step 2: Configure in Code Assistant

1. Open the Code Assistant page
2. Click the **⚙️ API** button in the header
3. Enter your API key
4. Select your provider (OpenAI or Gemini)
5. Click **Save**

### Step 3: Select Provider

1. Use the **AI Provider** dropdown in the header
2. Select **OpenAI (ChatGPT)** or **Google Gemini**
3. The assistant will use the AI for all subsequent messages

## Usage Examples

### Example 1: Code Generation with Context

**You:** "Create a KNN regressor to find optimal k"

**AI Response:**
```
Goal: Generate code to find optimal k for KNN regressor

Plan:
- Load California housing dataset
- Split into train/test
- Test k values from 1-20
- Find k with highest R² score
- Train final model

Changes:
[Code block with full implementation]

How to run/verify:
python knn_optimization.py

Notes:
- Tests k values 1-20
- Uses distance weighting
- Returns best k and metrics
```

**You (follow-up):** "I only want k 1-5"

**AI Response:**
```
Goal: Modify previous code to test only k values 1-5

Plan:
- Update range from (1, 21) to (1, 6)
- Keep all other logic the same

Changes:
[Modified code with range(1, 6)]

How to run/verify:
python knn_optimization.py

Notes:
- Now tests only k=1 through k=5
- Faster execution
```

### Example 2: Code Modification

**You:** [Paste your KNN code] "Change n_neighbors to 5 and optimize for highest R2"

**AI Response:**
- Analyzes your code
- Modifies n_neighbors parameter
- Adds optimization loop
- Provides complete working code

## How It Works

### Conversation Flow

1. **User sends message** → Stored in conversation history
2. **AI processes** → Uses system prompt with DIGEST and memory
3. **Response generated** → Follows structured format
4. **DIGEST updated** → Extracts goals, constraints, decisions
5. **Memory stored** → Saves durable preferences
6. **Response displayed** → Formatted with code blocks

### Memory System

**Session Memory (DIGEST):**
- Updated every turn
- Stored in browser localStorage
- Cleared when chat is cleared

**Long-term Memory:**
- Stores preferences: "use Python", "avoid pandas"
- Stores decisions: "chose Postgres over SQLite"
- Retrieved via semantic search
- Persists across sessions

### Code Formatting

- All code blocks are formatted for Google Colab
- Ready to copy-paste directly
- Preserves newlines and formatting
- Includes proper syntax highlighting

## API Costs

**OpenAI:**
- GPT-4o-mini: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- Typical conversation: $0.01-0.05 per session

**Google Gemini:**
- Gemini Pro: Free tier available
- Check current pricing at https://ai.google.dev/pricing

## Security

- API keys are stored **locally** in your browser (localStorage)
- Keys are **never** sent to our servers
- All API calls are made **directly** from your browser to OpenAI/Gemini
- You can clear your API key anytime by clearing browser data

## Troubleshooting

### "Failed to initialize AI agent"
- Check that your API key is correct
- Verify you have API credits/quota
- Try the other provider

### "API Error"
- Check your internet connection
- Verify API key is valid
- Check API service status

### Code not working as expected
- The AI makes best-effort responses
- Review the generated code before using
- You can ask follow-up questions to refine

## Switching Back to Local Mode

1. Select **Local (Rule-based)** from the AI Provider dropdown
2. The assistant will use pattern matching instead of AI

## Advanced Features

### Conversation Context
- The AI remembers your previous messages
- Can modify previous code based on new requests
- Maintains understanding of your project

### Code Optimization
- Automatically optimizes code when requested
- Tests different parameters
- Finds best configurations

### Multi-step Tasks
- Can handle complex, multi-file changes
- Plans before executing
- Provides verification steps

## Future Enhancements

Potential additions:
- File system access (read/write files)
- Command execution
- Test running
- Git integration
- Project-wide refactoring

---

**Note**: This is a client-side integration. For production use with file system access and advanced features, consider implementing a backend service.

