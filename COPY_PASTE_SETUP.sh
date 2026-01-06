#!/bin/bash
# One-command setup - Copy and paste this entire block on your server
# Run: curl -sSL https://raw.githubusercontent.com/adamelharouchi5-blip/AnalytIQ/main/setup_production.sh | sudo bash
# OR: Download and run: sudo bash setup_production.sh

# But first, make sure you're in the project directory and have .env set up

echo "🚀 Starting setup..."

# This is the same as setup_production.sh - run that instead
if [ -f "setup_production.sh" ]; then
    chmod +x setup_production.sh
    exec sudo ./setup_production.sh
else
    echo "❌ setup_production.sh not found!"
    echo "Please run this from your AnalytIQ project directory"
    exit 1
fi

