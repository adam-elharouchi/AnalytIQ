#!/bin/bash

# Start the Flask server on port 5001
# This script ensures the server runs on the correct port

echo "Starting AnalytIQ Flask Server..."
echo "Server will be available at: http://localhost:5001"
echo "Press CTRL+C to stop the server"
echo ""

# Check if port 5001 is already in use
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 5001 is already in use!"
    echo "Stopping existing process..."
    lsof -ti:5001 | xargs kill -9
    sleep 1
fi

# Start the Flask server
python3 app.py
