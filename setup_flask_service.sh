#!/bin/bash
# Script to set up Flask backend as a systemd service
# Run this on your production server

set -e  # Exit on error

echo "🚀 Setting up Flask Backend Service"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Get project directory
PROJECT_DIR=$(pwd)
echo "📁 Project directory: $PROJECT_DIR"
echo ""
read -p "Is this correct? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter the full path to your AnalytIQ project: " PROJECT_DIR
fi

# Get Python path
PYTHON_PATH=$(which python3)
echo ""
echo "🐍 Python path: $PYTHON_PATH"
read -p "Is this correct? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter Python3 path: " PYTHON_PATH
fi

# Get username (non-root user who owns the project)
if [ -n "$SUDO_USER" ]; then
    SERVICE_USER=$SUDO_USER
else
    SERVICE_USER=$(stat -c '%U' "$PROJECT_DIR" 2>/dev/null || echo "www-data")
fi

echo ""
echo "👤 Service user: $SERVICE_USER"
read -p "Is this correct? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter service user: " SERVICE_USER
fi

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/analytiq-api.service"

echo ""
echo "📝 Creating systemd service file..."

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=AnalytIQ Flask API
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PYTHON_PATH:/usr/bin:/usr/local/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$PYTHON_PATH $PROJECT_DIR/app.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Service file created: $SERVICE_FILE${NC}"

# Reload systemd
echo ""
echo "🔄 Reloading systemd..."
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

# Enable service
echo ""
echo "🔌 Enabling service..."
systemctl enable analytiq-api
echo -e "${GREEN}✓ Service enabled (will start on boot)${NC}"

# Start service
echo ""
echo "▶️  Starting service..."
if systemctl start analytiq-api; then
    echo -e "${GREEN}✓ Service started successfully${NC}"
else
    echo -e "${RED}❌ Failed to start service${NC}"
    echo ""
    echo "Check status with: systemctl status analytiq-api"
    echo "Check logs with: journalctl -u analytiq-api -f"
    exit 1
fi

# Wait a moment
sleep 2

# Check status
if systemctl is-active --quiet analytiq-api; then
    echo -e "${GREEN}✓ Service is running${NC}"
else
    echo -e "${YELLOW}⚠️  Service might not be running. Check status.${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Flask Service Setup Complete!${NC}"
echo ""
echo "📋 Useful commands:"
echo "   Status:  systemctl status analytiq-api"
echo "   Start:   systemctl start analytiq-api"
echo "   Stop:    systemctl stop analytiq-api"
echo "   Restart: systemctl restart analytiq-api"
echo "   Logs:    journalctl -u analytiq-api -f"
echo ""
echo "🧪 Test it:"
echo "   curl http://127.0.0.1:5000/api/health"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

