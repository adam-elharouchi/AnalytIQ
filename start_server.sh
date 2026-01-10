#!/bin/bash
# Simple startup script for AnalytIQ Flask API
# Usage: ./start_server.sh

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set production environment
export FLASK_ENV=production
export PORT=${PORT:-5001}

# Check if gunicorn is installed
if command -v gunicorn &> /dev/null; then
    echo "Starting AnalytIQ API with Gunicorn on port $PORT..."
    gunicorn app:app --bind 127.0.0.1:$PORT --workers 4 --timeout 120 --access-logfile - --error-logfile -
else
    echo "Gunicorn not found. Install it with: pip install gunicorn"
    echo "Starting with Flask development server instead..."
    echo "WARNING: This is not recommended for production!"
    python3 app.py $PORT
fi
