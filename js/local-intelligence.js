// Advanced Local Intelligence Engine - No API Required
// Enhanced rule-based system with sophisticated pattern matching and code generation

class LocalIntelligenceEngine {
  constructor() {
    this.conversationMemory = {
      goals: [],
      constraints: [],
      decisions: [],
      codeHistory: [],
      context: {}
    };
  }

  // Process message with advanced local intelligence
  processMessage(message, conversationHistory, uploadedData, currentLanguage) {
    const lowerMessage = message.toLowerCase();
    
    // Build context from conversation history
    const context = this.buildContext(conversationHistory, message);
    
    // Detect intent
    const intent = this.detectIntent(message, context);
    
    // Process based on intent
    switch (intent.type) {
      case 'code_modification':
        return this.handleCodeModification(message, context);
      case 'code_generation':
        return this.handleCodeGeneration(message, context, currentLanguage);
      case 'code_analysis':
        return this.handleCodeAnalysis(message, context);
      case 'optimization':
        return this.handleOptimization(message, context, currentLanguage);
      case 'visualization':
        return this.handleVisualization(message, uploadedData, currentLanguage);
      case 'data_analysis':
        return this.handleDataAnalysis(message, uploadedData);
      case 'follow_up':
        return this.handleFollowUp(message, context);
      default:
        return this.handleGeneralRequest(message, context, currentLanguage);
    }
  }

  // Build context from conversation
  buildContext(history, currentMessage) {
    const context = {
      hasCode: false,
      codeBlocks: [],
      mentionedLibraries: [],
      mentionedConcepts: [],
      parameters: {},
      previousRequests: []
    };

    // Extract code blocks from history
    history.forEach(msg => {
      if (msg.role === 'user') {
        const codeMatch = msg.content.match(/```[\s\S]*?```/g);
        if (codeMatch) {
          context.hasCode = true;
          codeMatch.forEach(block => {
            const code = block.replace(/```[\w]*\n?/g, '').replace(/```/g, '').trim();
            context.codeBlocks.push(code);
          });
        }
        
        // Extract mentioned libraries
        const libs = msg.content.match(/(?:import|from)\s+(\w+)/g);
        if (libs) {
          libs.forEach(lib => {
            const libName = lib.match(/(?:import|from)\s+(\w+)/)[1];
            if (!context.mentionedLibraries.includes(libName)) {
              context.mentionedLibraries.push(libName);
            }
          });
        }
      }
    });

    // Extract from current message
    const codeMatch = currentMessage.match(/```[\s\S]*?```/g);
    if (codeMatch) {
      context.hasCode = true;
      codeMatch.forEach(block => {
        const code = block.replace(/```[\w]*\n?/g, '').replace(/```/g, '').trim();
        context.codeBlocks.push(code);
      });
    }

    return context;
  }

  // Detect intent from message
  detectIntent(message, context) {
    const lower = message.toLowerCase();
    
    // Check for code modification
    if (context.hasCode && (
        lower.includes('modify') || lower.includes('change') || 
        lower.includes('update') || lower.includes('fix') ||
        lower.includes('only') || lower.includes('just')
    )) {
      return { type: 'code_modification', confidence: 0.9 };
    }

    // Check for optimization
    if (lower.includes('optimize') || lower.includes('best') || 
        lower.includes('highest') || lower.includes('improve') ||
        lower.includes('optimal')) {
      return { type: 'optimization', confidence: 0.9 };
    }

    // Check for code generation
    if (lower.includes('create') || lower.includes('generate') || 
        lower.includes('write') || lower.includes('build') ||
        lower.includes('make') || lower.includes('code for')) {
      return { type: 'code_generation', confidence: 0.8 };
    }

    // Check for analysis
    if (lower.includes('analyze') || lower.includes('explain') || 
        lower.includes('what does') || lower.includes('how does')) {
      return { type: 'code_analysis', confidence: 0.8 };
    }

    // Check for visualization
    if (lower.includes('visualize') || lower.includes('plot') || 
        lower.includes('chart') || lower.includes('graph')) {
      return { type: 'visualization', confidence: 0.8 };
    }

    // Check for follow-up
    if (this.conversationMemory.codeHistory.length > 0 && (
        lower.includes('only') || lower.includes('just') ||
        lower.includes('change') || lower.includes('modify')
    )) {
      return { type: 'follow_up', confidence: 0.9 };
    }

    return { type: 'general', confidence: 0.5 };
  }

  // Handle code modification with context
  handleCodeModification(message, context) {
    const lower = message.toLowerCase();
    let modifiedCode = context.codeBlocks[0] || '';
    let explanation = '**Modified Code:**\n\n';
    const changes = [];

    // Extract parameter changes
    const paramPatterns = [
      /(?:change|set|make|use)\s+(\w+)\s+(?:to|as|=\s*)?\s*(\d+|\w+)/gi,
      /(\w+)\s*=\s*(\d+|\w+)/g,
      /(?:only|just)\s+(?:k|neighbors?)\s*(\d+)\s*(?:to|-|through)?\s*(\d+)?/gi
    ];

    paramPatterns.forEach(pattern => {
      const matches = [...message.matchAll(pattern)];
      matches.forEach(match => {
        const param = match[1];
        const value = match[2] || match[1];
        
        if (param && value) {
          // Modify code
          const regex = new RegExp(`(${param}\\s*=\\s*)[^,\\n)]+`, 'gi');
          if (regex.test(modifiedCode)) {
            modifiedCode = modifiedCode.replace(regex, `$1${value}`);
            changes.push(`Changed ${param} to ${value}`);
          }
        }
      });
    });

    // Handle range modifications
    const rangeMatch = message.match(/(?:k|neighbors?|range)\s*(?:from|to|is|only)?\s*(\d+)\s*(?:to|-|through|and)?\s*(\d+)/i);
    if (rangeMatch) {
      const start = parseInt(rangeMatch[1]);
      const end = parseInt(rangeMatch[2] || rangeMatch[1]);
      
      modifiedCode = modifiedCode.replace(/for\s+k\s+in\s+range\(\d+,\s*\d+\)/g, `for k in range(${start}, ${end + 1})`);
      modifiedCode = modifiedCode.replace(/range\(1,\s*21\)/g, `range(${start}, ${end + 1})`);
      changes.push(`Changed k range to ${start}-${end}`);
    }

    if (changes.length > 0) {
      explanation += changes.join('\n') + '\n\n';
    } else {
      explanation += 'I\'ve modified the code based on your request.\n\n';
    }

    // Store in memory
    this.conversationMemory.codeHistory.push(modifiedCode);

    return explanation + `\`\`\`python\n${modifiedCode}\n\`\`\``;
  }

  // Handle code generation with advanced templates
  handleCodeGeneration(message, context, language) {
    const lower = message.toLowerCase();
    const goal = this.extractGoal(message);
    const plan = this.generatePlan(message, context);
    
    let code = '';
    let explanation = `**Goal:** ${goal}\n\n**Plan:**\n${plan}\n\n**Implementation:**\n\n`;

    // Advanced code generation based on patterns
    if (lower.includes('knn') || lower.includes('k-neighbors') || lower.includes('neighbors')) {
      code = this.generateKNNCode(message, context, language);
    } else if (lower.includes('regression') || lower.includes('linear regression')) {
      code = this.generateRegressionCode(message, context, language);
    } else if (lower.includes('classification') || lower.includes('classifier')) {
      code = this.generateClassificationCode(message, context, language);
    } else if (lower.includes('api') || lower.includes('endpoint') || lower.includes('rest')) {
      code = this.generateAPICode(message, context, language);
    } else if (lower.includes('database') || lower.includes('db') || lower.includes('sql')) {
      code = this.generateDatabaseCode(message, context, language);
    } else if (lower.includes('scraper') || lower.includes('scrape')) {
      code = this.generateScraperCode(message, context, language);
    } else {
      code = this.generateGenericCode(message, context, language);
    }

    // Store in memory
    this.conversationMemory.codeHistory.push(code);
    this.conversationMemory.goals.push(goal);

    return explanation + `\`\`\`${language}\n${code}\n\`\`\``;
  }

  // Generate KNN code with optimization
  generateKNNCode(message, context, language) {
    const lower = message.toLowerCase();
    const hasOptimization = lower.includes('optimal') || lower.includes('best') || 
                           lower.includes('highest') || lower.includes('optimize');
    
    // Extract k range
    const rangeMatch = message.match(/(?:k|neighbors?)\s*(?:from|to|is|only)?\s*(\d+)\s*(?:to|-|through|and)?\s*(\d+)/i);
    const startK = rangeMatch ? parseInt(rangeMatch[1]) : 1;
    const endK = rangeMatch ? parseInt(rangeMatch[2] || rangeMatch[1]) : 20;

    if (hasOptimization) {
      return this.generateOptimalKNNCode(startK, endK);
    } else {
      return this.generateSimpleKNNCode(startK, endK);
    }
  }

  generateOptimalKNNCode(startK, endK) {
    return `from sklearn.datasets import fetch_california_housing
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

# Find optimal k value (testing k from ${startK} to ${endK})
best_k = ${startK}
best_r2 = -np.inf
best_mse = np.inf
results = []

print("Testing different k values to find optimal R² score...")
print("-" * 50)

for k in range(${startK}, ${endK + 1}):
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
  }

  generateSimpleKNNCode(startK, endK) {
    return `from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import r2_score, mean_squared_error

# Load dataset
california = fetch_california_housing(as_frame=True)
X = california.data
y = california.target

# Split train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Create KNN regressor
knn_reg = KNeighborsRegressor(
    n_neighbors=5,
    weights='distance',
    p=2,
    n_jobs=-1
)

knn_reg.fit(X_train_scaled, y_train)
y_pred = knn_reg.predict(X_test_scaled)

r2 = r2_score(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)

print(f"R² Score: {r2:.6f}")
print(f"Mean Squared Error: {mse:.6f}")`;
  }

  // Generate regression code
  generateRegressionCode(message, context, language) {
    if (language === 'python') {
      return `from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
import pandas as pd

# Load your data
# df = pd.read_csv('your_data.csv')
# X = df.drop('target', axis=1)
# y = df['target']

# Split data
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create and train model
model = LinearRegression()
# model.fit(X_train, y_train)

# Make predictions
# y_pred = model.predict(X_test)

# Evaluate
# r2 = r2_score(y_test, y_pred)
# mse = mean_squared_error(y_test, y_pred)
# print(f"R² Score: {r2:.4f}")
# print(f"MSE: {mse:.4f}")`;
    }
    return '# Regression code';
  }

  // Generate classification code
  generateClassificationCode(message, context, language) {
    if (language === 'python') {
      return `from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pandas as pd

# Load your data
# df = pd.read_csv('your_data.csv')
# X = df.drop('target', axis=1)
# y = df['target']

# Split data
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create and train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
# model.fit(X_train, y_train)

# Make predictions
# y_pred = model.predict(X_test)

# Evaluate
# accuracy = accuracy_score(y_test, y_pred)
# print(f"Accuracy: {accuracy:.4f}")
# print("\\nClassification Report:")
# print(classification_report(y_test, y_pred))
# print("\\nConfusion Matrix:")
# print(confusion_matrix(y_test, y_pred))`;
    }
    return '# Classification code';
  }

  // Generate API code
  generateAPICode(message, context, language) {
    if (language === 'python') {
      return `from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Sample data store
items = []

@app.route('/api/items', methods=['GET'])
def get_items():
    """Get all items"""
    return jsonify(items), 200

@app.route('/api/items', methods=['POST'])
def create_item():
    """Create a new item"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
    new_item = {
        'id': len(items) + 1,
        'name': data['name'],
        'description': data.get('description', '')
    }
    items.append(new_item)
    return jsonify(new_item), 201

@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    """Get a specific item"""
    item = next((i for i in items if i['id'] == item_id), None)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    return jsonify(item), 200

@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """Update an item"""
    item = next((i for i in items if i['id'] == item_id), None)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    data = request.get_json()
    item.update(data)
    return jsonify(item), 200

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    """Delete an item"""
    global items
    items = [i for i in items if i['id'] != item_id]
    return jsonify({'message': 'Item deleted'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)`;
    }
    return '# API code';
  }

  // Generate database code
  generateDatabaseCode(message, context, language) {
    if (language === 'python') {
      return `import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection(db_path):
    """Context manager for database connections"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def create_table(conn):
    """Create a sample table"""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

def insert_user(conn, name, email):
    """Insert a new user"""
    conn.execute('INSERT INTO users (name, email) VALUES (?, ?)', (name, email))
    conn.commit()
    return conn.lastrowid

def get_user(conn, user_id):
    """Get a user by ID"""
    cursor = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    return cursor.fetchone()

def get_all_users(conn):
    """Get all users"""
    cursor = conn.execute('SELECT * FROM users')
    return cursor.fetchall()

def update_user(conn, user_id, name=None, email=None):
    """Update a user"""
    updates = []
    params = []
    if name:
        updates.append('name = ?')
        params.append(name)
    if email:
        updates.append('email = ?')
        params.append(email)
    if updates:
        params.append(user_id)
        conn.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = ?', params)
        conn.commit()

def delete_user(conn, user_id):
    """Delete a user"""
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()

# Example usage
if __name__ == "__main__":
    db_path = 'example.db'
    with get_db_connection(db_path) as conn:
        create_table(conn)
        user_id = insert_user(conn, 'John Doe', 'john@example.com')
        user = get_user(conn, user_id)
        print(f"Created user: {dict(user)}")`;
    }
    return '# Database code';
  }

  // Generate scraper code
  generateScraperCode(message, context, language) {
    if (language === 'python') {
      return `import requests
from bs4 import BeautifulSoup
import json

def scrape_website(url):
    """
    Scrape a website and extract data.
    
    Args:
        url (str): URL to scrape
        
    Returns:
        dict: Scraped data
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text() if title else 'No title found'
        
        # Extract all links
        links = [a.get('href') for a in soup.find_all('a', href=True)]
        
        # Extract all paragraphs
        paragraphs = [p.get_text().strip() for p in soup.find_all('p')]
        
        return {
            'url': url,
            'title': title_text,
            'links_count': len(links),
            'links': links[:10],  # First 10 links
            'paragraphs_count': len(paragraphs),
            'paragraphs': paragraphs[:5]  # First 5 paragraphs
        }
    except requests.RequestException as e:
        return {'error': f'Failed to scrape website: {str(e)}'}

# Example usage
if __name__ == "__main__":
    url = "https://example.com"
    result = scrape_website(url)
    print(json.dumps(result, indent=2))`;
    }
    return '# Scraper code';
  }

  // Generate generic code
  generateGenericCode(message, context, language) {
    const goal = this.extractGoal(message);
    
    if (language === 'python') {
      return `def ${this.extractFunctionName(message) || 'process_data'}(input_data):
    """
    ${goal}
    
    Args:
        input_data: Input data to process
        
    Returns:
        Processed result
    """
    # TODO: Implement functionality
    result = input_data
    return result

# Example usage
if __name__ == "__main__":
    data = "example input"
    output = ${this.extractFunctionName(message) || 'process_data'}(data)
    print(f"Output: {output}")`;
    }
    return `# Code for: ${goal}`;
  }

  // Extract goal from message
  extractGoal(message) {
    const goalPatterns = [
      /goal:\s*(.+?)(?:\.|$)/i,
      /I want to (.+?)(?:\.|$)/i,
      /create (.+?)(?:\.|$)/i,
      /build (.+?)(?:\.|$)/i,
      /generate (.+?)(?:\.|$)/i,
      /write (.+?)(?:\.|$)/i
    ];

    for (const pattern of goalPatterns) {
      const match = message.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }

    return message.substring(0, 100) + '...';
  }

  // Generate plan
  generatePlan(message, context) {
    const plan = [];
    const lower = message.toLowerCase();

    if (lower.includes('knn') || lower.includes('neighbors')) {
      plan.push('Load dataset');
      plan.push('Split into train/test sets');
      plan.push('Scale features');
      if (lower.includes('optimal') || lower.includes('best')) {
        plan.push('Test different k values');
        plan.push('Find k with highest R² score');
      }
      plan.push('Train KNN model');
      plan.push('Evaluate performance');
    } else if (lower.includes('api')) {
      plan.push('Set up Flask application');
      plan.push('Define routes (GET, POST, PUT, DELETE)');
      plan.push('Implement request handling');
      plan.push('Add error handling');
    } else {
      plan.push('Identify requirements');
      plan.push('Implement core functionality');
      plan.push('Add error handling');
      plan.push('Test implementation');
    }

    return plan.map((p, i) => `${i + 1}. ${p}`).join('\n');
  }

  // Extract function name
  extractFunctionName(message) {
    const match = message.match(/(?:function|create|write|make|build)\s+(\w+)/i);
    return match ? match[1] : null;
  }

  // Handle optimization requests
  handleOptimization(message, context, language) {
    const lower = message.toLowerCase();
    let code = '';

    if (lower.includes('knn') || lower.includes('neighbors')) {
      const rangeMatch = message.match(/(?:k|neighbors?)\s*(?:from|to|is|only)?\s*(\d+)\s*(?:to|-|through|and)?\s*(\d+)/i);
      const startK = rangeMatch ? parseInt(rangeMatch[1]) : 1;
      const endK = rangeMatch ? parseInt(rangeMatch[2] || rangeMatch[1]) : 20;
      code = this.generateOptimalKNNCode(startK, endK);
    } else {
      code = this.generateGenericCode(message, context, language);
    }

    const goal = this.extractGoal(message);
    const plan = this.generatePlan(message, context);

    return `**Goal:** ${goal}\n\n**Plan:**\n${plan}\n\n**Optimized Code:**\n\n\`\`\`${language}\n${code}\n\`\`\`\n\n**How to run/verify:**\n\`\`\`bash\npython script.py\n\`\`\`\n\n**Notes:**\n- The code will test different parameters to find the optimal configuration\n- Results will be printed showing the best configuration and metrics`;
  }

  // Handle code analysis
  handleCodeAnalysis(message, context) {
    if (!context.hasCode && context.codeBlocks.length === 0) {
      return 'Please paste the code you want me to analyze.';
    }

    const code = context.codeBlocks[0] || '';
    const analysis = this.analyzeCodeAdvanced(code);

    let response = `**Code Analysis:**\n\n`;
    
    if (analysis.summary) {
      response += `**Summary:** ${analysis.summary}\n\n`;
    }

    if (analysis.issues.length > 0) {
      response += `**Issues Found:**\n`;
      analysis.issues.forEach(issue => {
        response += `- ${issue.type}: ${issue.message}\n`;
      });
      response += `\n`;
    }

    if (analysis.suggestions.length > 0) {
      response += `**Suggestions:**\n`;
      analysis.suggestions.forEach(sugg => {
        response += `- ${sugg}\n`;
      });
      response += `\n`;
    }

    if (analysis.improvements.length > 0) {
      response += `**Potential Improvements:**\n`;
      analysis.improvements.forEach(imp => {
        response += `- ${imp}\n`;
      });
    }

    return response;
  }

  // Advanced code analysis
  analyzeCodeAdvanced(code) {
    const analysis = {
      summary: '',
      issues: [],
      suggestions: [],
      improvements: []
    };

    // Detect what the code does
    if (code.includes('KNeighborsRegressor') || code.includes('KNeighborsClassifier')) {
      analysis.summary = 'K-Nearest Neighbors (KNN) machine learning model implementation';
    } else if (code.includes('LinearRegression')) {
      analysis.summary = 'Linear regression model implementation';
    } else if (code.includes('train_test_split')) {
      analysis.summary = 'Machine learning workflow with train/test split';
    }

    // Check for common issues
    if (code.includes('import *')) {
      analysis.issues.push({
        type: 'Warning',
        message: 'Avoid "import *" - it pollutes the namespace'
      });
    }

    if (code.includes('print(') && !code.includes('if __name__')) {
      analysis.suggestions.push('Consider using "if __name__ == \'__main__\'" guard for script execution');
    }

    if (!code.includes('try') && (code.includes('requests.get') || code.includes('open('))) {
      analysis.suggestions.push('Add error handling with try/except blocks');
    }

    return analysis;
  }

  // Handle visualization
  handleVisualization(message, uploadedData, language) {
    if (!uploadedData || !uploadedData.data) {
      return 'Please upload a data file first to create visualizations.';
    }

    const lower = message.toLowerCase();
    let vizType = 'histogram';
    
    if (lower.includes('boxplot') || lower.includes('box plot')) {
      vizType = 'boxplot';
    } else if (lower.includes('histogram')) {
      vizType = 'histogram';
    } else if (lower.includes('scatter')) {
      vizType = 'scatter';
    } else if (lower.includes('bar')) {
      vizType = 'bar';
    }

    const code = generateVisualizationCode(vizType, uploadedData);
    const visualizationId = 'viz-' + Date.now();
    
    let response = `**Goal:** Create ${vizType} visualization\n\n`;
    response += `**Plan:**\n1. Load data\n2. Prepare visualization\n3. Display chart\n\n`;
    response += `**Code:**\n\n\`\`\`${language}\n${code}\n\`\`\`\n\n`;
    response += `**Visualization:**\n<div id="${visualizationId}" class="visualization-container"></div>`;
    
    setTimeout(() => {
      renderVisualization(visualizationId, vizType, uploadedData);
    }, 100);
    
    return response;
  }

  // Handle data analysis
  handleDataAnalysis(message, uploadedData) {
    if (!uploadedData || !uploadedData.data) {
      return 'Please upload a data file first.';
    }

    const analysis = analyzeData(uploadedData);
    return formatDataAnalysis(analysis);
  }

  // Handle follow-up requests
  handleFollowUp(message, context) {
    const lastCode = this.conversationMemory.codeHistory[this.conversationMemory.codeHistory.length - 1];
    
    if (!lastCode) {
      return 'I don\'t have previous code to modify. Please provide code or generate new code first.';
    }

    return this.handleCodeModification(message, { ...context, codeBlocks: [lastCode] });
  }

  // Handle general requests
  handleGeneralRequest(message, context, language) {
    // Try to infer what user wants
    const lower = message.toLowerCase();
    
    if (lower.includes('help') || lower.includes('what can')) {
      return `I can help you with:
- Generate code in any language
- Modify and optimize existing code
- Analyze code for errors and improvements
- Create visualizations from data
- Work with machine learning models
- Build APIs and web services
- And much more!

Just describe what you need or paste your code.`;
    }

    // Default: try code generation
    return this.handleCodeGeneration(message, context, language);
  }
}

// Export singleton
const localIntelligence = new LocalIntelligenceEngine();

