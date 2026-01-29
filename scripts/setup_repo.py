#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script to copy AnalytIQ to a new GitHub repository
Run with: python3 setup_repo.py
"""

import os
import shutil
import subprocess
from pathlib import Path

def main():
    print("🚀 Setting up new AnalytIQ repository...")
    
    # Define paths
    source_dir = Path("/Users/aelharouchi/Documents/GitHub/AnalytIQ")
    target_dir = Path("/Users/aelharouchi/Documents/GitHub/AnalytIQ-Test")
    
    # Remove old directory if exists
    if target_dir.exists():
        print("⚠️  Removing old AnalytIQ-Test directory...")
        shutil.rmtree(target_dir)
    
    # Create new directory
    print("📁 Creating new directory...")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Files/directories to exclude
    excludes = {
        '.git', 'node_modules', '__pycache__', '.DS_Store',
        '*.pyc', '*.log', '*.pid', 'flask_server.log',
        'flask_server.pid', 'flask_final.log', 'flask_server_new.log',
        'test_*.py', 'test_*.html', 'migrate_*.py', 'check_*.py',
        'create_tables.py', 'export_*.html', 'export_*.js', 'mock_data.json'
    }
    
    # Copy files
    print("📋 Copying files...")
    copied = 0
    skipped = 0
    
    for root, dirs, files in os.walk(source_dir):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in excludes and not d.startswith('.')]
        
        # Calculate relative path
        rel_path = os.path.relpath(root, source_dir)
        if rel_path == '.':
            target_root = target_dir
        else:
            target_root = target_dir / rel_path
        
        # Create target directory
        target_root.mkdir(parents=True, exist_ok=True)
        
        # Copy files
        for file in files:
            # Skip excluded files
            skip = False
            for exclude in excludes:
                if exclude.startswith('*') and file.endswith(exclude[1:]):
                    skip = True
                    break
                elif file == exclude or file.startswith(exclude.replace('*', '')):
                    skip = True
                    break
            
            if skip or file.endswith('.pyc') or file.endswith('.log') or file.endswith('.pid'):
                skipped += 1
                continue
            
            source_file = Path(root) / file
            target_file = target_root / file
            
            try:
                shutil.copy2(source_file, target_file)
                copied += 1
            except Exception as e:
                print(f"⚠️  Could not copy {source_file}: {e}")
                skipped += 1
    
    print(f"✅ Copied {copied} files, skipped {skipped} files")
    
    # Create .gitignore
    print("📝 Creating .gitignore...")
    gitignore_content = """# Environment variables
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
env/
venv/
ENV/
.venv
pip-log.txt
pip-delete-this-directory.txt

# Flask
*.log
*.pid
instance/
.webassets-cache
.flaskenv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.project
.classpath
.settings/

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Node modules (if any)
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Database
*.db
*.sqlite
*.sqlite3

# Temporary files
*.tmp
*.temp
*.bak
*.swp

# Test files
test_*.py
test_*.html

# Migration scripts (not needed in production)
migrate_*.py
check_*.py
create_tables.py
"""
    
    with open(target_dir / '.gitignore', 'w') as f:
        f.write(gitignore_content)
    
    # Create README
    print("📝 Creating README.md...")
    readme_content = """# AnalytIQ - Data Analytics Learning Platform

A comprehensive platform for mastering data analytics with AI-powered features for both students and professors.

## 🎯 Features

### For Professors
- **Dashboard**: Create and manage multiple classes
- **Class Management**: Custom class codes, descriptions, and settings
- **PDF Upload**: Upload course chapters with automatic text extraction
- **Exercise Generation**: AI-powered automatic exercise generation from PDFs
- **Progress Tracking**: Monitor student progress and performance
- **Resource Management**: Add and organize course resources
- **Exercise Editor**: View and edit generated exercises

### For Students
- **Class Enrollment**: Join classes using class codes
- **Course Materials**: Access PDF chapters and resources
- **Practice Exercises**: Interactive exercises with leaderboards
- **Progress Tracking**: Monitor your learning progress
- **AI Code Assistant**: Get help with coding and analytics

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- PostgreSQL database (Supabase recommended)
- Google Gemini API key (for exercise generation)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd AnalytIQ-Test
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
Create a `.env` file in the root directory:
```env
DATABASE_URL=your_postgresql_connection_string
GEMINI_API_KEY=your_gemini_api_key
PORT=5001
```

4. **Start the Flask server**
```bash
python3 app.py
```

5. **Open the application**
Navigate to `http://localhost:8000` in your browser

## 📁 Project Structure

- `app.py` - Flask backend API server
- `db_connection.py` - Database connection utilities
- `python/` - Backend utilities (PDF processing, exercise generation)
- `js/` - Frontend JavaScript modules
- `css/` - Stylesheets
- HTML files for each page/feature

## 🔌 API Endpoints

- `POST /api/users/signup` - Register new user
- `POST /api/users/signin` - Sign in user
- `GET /api/classes` - Get user's classes
- `POST /api/classes` - Create new class
- `POST /api/classes/<id>/chapters` - Upload PDF chapter
- `POST /api/contact` - Submit contact form

## 📄 License

Copyright (c) 2026 AnalytIQ. All rights reserved. Adam El Harouchi.
"""
    
    with open(target_dir / 'README.md', 'w') as f:
        f.write(readme_content)
    
    # Initialize git
    print("🔧 Initializing git repository...")
    os.chdir(target_dir)
    subprocess.run(['git', 'init'], check=True)
    subprocess.run(['git', 'branch', '-M', 'main'], check=True)
    
    # Stage all files
    print("📦 Staging files for commit...")
    subprocess.run(['git', 'add', '-A'], check=True)
    
    # Make initial commit
    print("💾 Creating initial commit...")
    subprocess.run([
        'git', 'commit', '-m',
        'Initial commit: Complete AnalytIQ platform\n\n'
        '- Professor dashboard with class management\n'
        '- PDF chapter upload with text extraction\n'
        '- AI-powered exercise generation\n'
        '- Student enrollment and progress tracking\n'
        '- Practice exercises with leaderboards\n'
        '- AI code assistant\n'
        '- Contact form integration\n'
        '- Resources management\n'
        '- Full UI with responsive design'
    ], check=True)
    
    print("")
    print("✅ Repository setup complete!")
    print("")
    print(f"📁 Location: {target_dir}")
    print("")
    print("📋 Next steps:")
    print("1. Create a new repository on GitHub: https://github.com/new")
    print("2. Copy the repository URL")
    print("3. Run these commands:")
    print("")
    print(f"   cd {target_dir}")
    print("   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git")
    print("   git push -u origin main")
    print("")
    print("🎉 Ready to push to GitHub!")

if __name__ == '__main__':
    main()
