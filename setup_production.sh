#!/bin/bash
# Master setup script for AnalytIQ production server
# This script sets up everything: Nginx, Flask service, dependencies
# Run this on your production server: sudo ./setup_production.sh

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 AnalytIQ Production Server Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use: sudo ./setup_production.sh)${NC}"
    exit 1
fi

# Get project directory
PROJECT_DIR=$(pwd)
echo -e "${BLUE}📁 Current directory: ${PROJECT_DIR}${NC}"
echo ""
read -p "Use this as project directory? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter full path to AnalytIQ project: " PROJECT_DIR
    if [ ! -d "$PROJECT_DIR" ]; then
        echo -e "${RED}❌ Directory not found: $PROJECT_DIR${NC}"
        exit 1
    fi
    cd "$PROJECT_DIR"
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
else
    echo -e "${RED}❌ Cannot detect OS${NC}"
    exit 1
fi

echo -e "${GREEN}✓ OS: $OS $OS_VERSION${NC}"
echo ""

# ============================================================================
# STEP 1: Install System Dependencies
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 1: Installing System Dependencies${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "📦 Updating package lists..."
if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    apt update -qq
    echo "📦 Installing Nginx, Python3, pip, and build tools..."
    apt install -y nginx python3 python3-pip python3-venv build-essential
elif [ "$OS" == "centos" ] || [ "$OS" == "rhel" ] || [ "$OS" == "fedora" ]; then
    yum update -y -q
    echo "📦 Installing Nginx, Python3, pip, and build tools..."
    yum install -y nginx python3 python3-pip gcc
else
    echo -e "${YELLOW}⚠️  Unsupported OS. Please install Nginx and Python3 manually.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ System dependencies installed${NC}"
echo ""

# ============================================================================
# STEP 2: Install Python Dependencies
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 2: Installing Python Dependencies${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt not found in $PROJECT_DIR${NC}"
    exit 1
fi

echo "📦 Installing Python packages..."
pip3 install --quiet --upgrade pip
pip3 install --quiet -r requirements.txt

echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

# ============================================================================
# STEP 3: Check .env File
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 3: Checking Environment Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Creating .env file template..."
    cat > .env <<EOF
# Database URL
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/postgres

# Flask Configuration (optional)
FLASK_ENV=production
FLASK_DEBUG=False
EOF
    echo -e "${YELLOW}⚠️  Please edit .env file and add your DATABASE_URL${NC}"
    echo "   File: $PROJECT_DIR/.env"
    read -p "Press Enter after you've updated .env file..."
else
    echo -e "${GREEN}✓ .env file found${NC}"
fi

# Set secure permissions
chmod 600 .env
echo -e "${GREEN}✓ .env file permissions set${NC}"
echo ""

# ============================================================================
# STEP 4: Set Up Nginx
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 4: Setting Up Nginx Reverse Proxy${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Determine Nginx config location
if [ -d "/etc/nginx/sites-available" ]; then
    CONFIG_FILE="/etc/nginx/sites-available/myanalytiq"
    ENABLED_DIR="/etc/nginx/sites-enabled"
elif [ -d "/etc/nginx/conf.d" ]; then
    CONFIG_FILE="/etc/nginx/conf.d/myanalytiq.conf"
    ENABLED_DIR=""
else
    CONFIG_FILE="/etc/nginx/myanalytiq.conf"
    ENABLED_DIR=""
fi

echo "📝 Creating Nginx configuration..."

# Create config
cat > "$CONFIG_FILE" <<EOF
# Nginx configuration for AnalytIQ
# Generated by setup_production.sh

server {
    listen 80;
    server_name www.myanalytiq.org myanalytiq.org;

    # Logging
    access_log /var/log/nginx/analytiq_access.log;
    error_log /var/log/nginx/analytiq_error.log;

    # Maximum upload size
    client_max_body_size 10M;

    # Serve static files (frontend)
    location / {
        root $PROJECT_DIR;
        index index.html;
        try_files \$uri \$uri/ /index.html;
        
        # Cache static assets
        location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Proxy API requests to Flask backend
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
        
        if (\$request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS';
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization';
            add_header 'Access-Control-Max-Age' 1728000;
            add_header 'Content-Type' 'text/plain; charset=utf-8';
            add_header 'Content-Length' 0;
            return 204;
        }
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

echo -e "${GREEN}✓ Configuration created: $CONFIG_FILE${NC}"

# Enable site (Debian/Ubuntu)
if [ -n "$ENABLED_DIR" ]; then
    if [ ! -f "$ENABLED_DIR/myanalytiq" ]; then
        ln -s "$CONFIG_FILE" "$ENABLED_DIR/myanalytiq"
        echo -e "${GREEN}✓ Site enabled${NC}"
    fi
fi

# Test and restart Nginx
echo ""
echo "🔍 Testing Nginx configuration..."
if nginx -t 2>/dev/null; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
    echo "🔄 Restarting Nginx..."
    if systemctl restart nginx 2>/dev/null || service nginx restart 2>/dev/null; then
        echo -e "${GREEN}✓ Nginx restarted successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  Nginx restart might have failed. Check manually.${NC}"
    fi
else
    echo -e "${RED}❌ Nginx configuration has errors${NC}"
    echo "Check the configuration file: $CONFIG_FILE"
    exit 1
fi

echo ""

# ============================================================================
# STEP 5: Set Up Flask Service
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Step 5: Setting Up Flask Backend Service${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Get Python path
PYTHON_PATH=$(which python3)
echo -e "${GREEN}✓ Python path: $PYTHON_PATH${NC}"

# Get service user
if [ -n "$SUDO_USER" ]; then
    SERVICE_USER=$SUDO_USER
else
    SERVICE_USER=$(stat -c '%U' "$PROJECT_DIR" 2>/dev/null || echo "www-data")
fi
echo -e "${GREEN}✓ Service user: $SERVICE_USER${NC}"
echo ""

# Create service file
SERVICE_FILE="/etc/systemd/system/analytiq-api.service"

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

# Reload systemd and enable service
echo ""
echo "🔄 Reloading systemd..."
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

echo "🔌 Enabling service..."
systemctl enable analytiq-api
echo -e "${GREEN}✓ Service enabled (will start on boot)${NC}"

echo "▶️  Starting service..."
if systemctl start analytiq-api; then
    sleep 3
    if systemctl is-active --quiet analytiq-api; then
        echo -e "${GREEN}✓ Service started and running${NC}"
    else
        echo -e "${YELLOW}⚠️  Service started but might not be running${NC}"
        echo "   Check with: systemctl status analytiq-api"
    fi
else
    echo -e "${RED}❌ Failed to start service${NC}"
    echo "   Check logs: journalctl -u analytiq-api -n 50"
fi

echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo -e "${GREEN}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${NC}"
echo ""
echo -e "${BLUE}📍 Your Services:${NC}"
echo "   Frontend: http://www.myanalytiq.org/"
echo "   API:      http://www.myanalytiq.org/api"
echo ""
echo -e "${BLUE}🧪 Test Commands:${NC}"
echo "   # Test Flask directly"
echo "   curl http://127.0.0.1:5000/api/health"
echo ""
echo "   # Test through Nginx"
echo "   curl http://localhost/api/health"
echo ""
echo "   # Check Flask service status"
echo "   systemctl status analytiq-api"
echo ""
echo "   # View Flask logs"
echo "   journalctl -u analytiq-api -f"
echo ""
echo -e "${YELLOW}⚠️  Next Steps:${NC}"
echo "   1. Configure SSL/HTTPS (recommended):"
echo "      sudo apt install certbot python3-certbot-nginx"
echo "      sudo certbot --nginx -d www.myanalytiq.org -d myanalytiq.org"
echo ""
echo "   2. Test your website:"
echo "      Visit https://www.myanalytiq.org"
echo ""
echo "   3. Check service logs if there are issues:"
echo "      journalctl -u analytiq-api -f"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

