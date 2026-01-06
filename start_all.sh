#!/bin/bash
# Script to start both Flask backend and frontend proxy server

cd "$(dirname "$0")"

echo "🚀 Starting AnalytIQ servers..."
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $FLASK_PID $PROXY_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start Flask backend
echo "📡 Starting Flask backend on port 5000..."
bash start_backend.sh &
FLASK_PID=$!

# Wait a moment for Flask to start
sleep 3

# Check if Flask started successfully
if ! kill -0 $FLASK_PID 2>/dev/null; then
    echo "❌ Flask backend failed to start!"
    exit 1
fi

echo "✅ Flask backend is running (PID: $FLASK_PID)"
echo ""

# Start frontend proxy server
echo "🌐 Starting frontend proxy server on port 8080..."
python3 start_server.py &
PROXY_PID=$!

echo "✅ Frontend proxy is running (PID: $PROXY_PID)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 All servers are running!"
echo ""
echo "📍 Frontend: http://localhost:8080"
echo "📍 API: http://localhost:5000/api"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Wait for both processes
wait

