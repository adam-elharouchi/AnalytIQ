#!/bin/bash
# Script to start the Flask backend server

cd "$(dirname "$0")"

echo "🚀 Starting Flask backend server..."
echo "📍 Directory: $(pwd)"
echo "🔌 Port: 5000"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Make sure your DATABASE_URL is set in .env"
fi

# Start Flask server
python3 app.py

