#!/bin/bash
# Simple script to run Flask website

cd "$(dirname "$0")"

echo "🚀 Starting Flask website..."
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Make sure your DATABASE_URL is set in .env"
fi

# Run Flask
python3 app.py

