# Production Server Setup Guide

Complete guide to set up reverse proxy and Flask backend on your production server.

## Prerequisites

1. **Server Access**: SSH access to your server where `www.myanalytiq.org` is hosted
2. **Domain**: `www.myanalytiq.org` should point to your server's IP address
3. **Python 3**: Installed on the server
4. **Project Files**: Your AnalytIQ project files should be on the server

---

## Step 1: Upload Project Files to Server

If not already on the server, upload your project:

```bash
# From your local machine
scp -r /Users/aelharouchi/Documents/GitHub/AnalytIQ user@your-server-ip:/path/to/destination/

# Or use Git to clone on server
ssh user@your-server-ip
git clone https://github.com/adamelharouchi5-blip/AnalytIQ.git
cd AnalytIQ
```

---

## Step 2: Install Dependencies on Server

```bash
# SSH into your server
ssh user@your-server-ip

# Navigate to project directory
cd /path/to/AnalytIQ

# Install Python dependencies
pip3 install -r requirements.txt

# Make sure .env file exists with DATABASE_URL
nano .env
# Add: DATABASE_URL=postgresql://postgres:password@host:5432/database
```

---

## Step 3: Set Up Reverse Proxy (Nginx)

### Option A: Use the Automated Script (Easiest)

```bash
# On your server
cd /path/to/AnalytIQ
chmod +x setup_reverse_proxy.sh
sudo ./setup_reverse_proxy.sh
```

The script will:
- ✅ Install Nginx
- ✅ Create configuration file
- ✅ Enable the site
- ✅ Test and restart Nginx

### Option B: Manual Setup

#### 3.1 Install Nginx

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install nginx
```

**CentOS/RHEL:**
```bash
sudo yum install nginx
```

#### 3.2 Create Nginx Configuration

**For Ubuntu/Debian:**
```bash
sudo cp nginx.conf /etc/nginx/sites-available/myanalytiq.conf
sudo nano /etc/nginx/sites-available/myanalytiq.conf
# Update the 'root' path to your actual project directory
sudo ln -s /etc/nginx/sites-available/myanalytiq.conf /etc/nginx/sites-enabled/
```

**For CentOS/RHEL:**
```bash
sudo cp nginx.conf /etc/nginx/conf.d/myanalytiq.conf
sudo nano /etc/nginx/conf.d/myanalytiq.conf
# Update the 'root' path to your actual project directory
```

#### 3.3 Update Configuration Path

Edit the config file and update this line:
```nginx
root /path/to/your/AnalytIQ;  # Change to your actual path
```

#### 3.4 Test and Restart Nginx

```bash
# Test configuration
sudo nginx -t

# If test passes, restart nginx
sudo systemctl restart nginx
```

---

## Step 4: Set Up Flask Backend as a Service

### Option A: Use the Automated Script (Easiest)

```bash
# On your server
cd /path/to/AnalytIQ
chmod +x setup_flask_service.sh
sudo ./setup_flask_service.sh
```

The script will:
- ✅ Create systemd service file
- ✅ Enable service (auto-start on boot)
- ✅ Start the service
- ✅ Verify it's running

### Option B: Manual Setup

#### 4.1 Create Service File

```bash
sudo nano /etc/systemd/system/analytiq-api.service
```

Paste this (update paths):
```ini
[Unit]
Description=AnalytIQ Flask API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/AnalytIQ
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /path/to/AnalytIQ/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4.2 Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable analytiq-api

# Start service
sudo systemctl start analytiq-api

# Check status
sudo systemctl status analytiq-api
```

---

## Step 5: Configure SSL/HTTPS (Recommended)

### Using Let's Encrypt (Free SSL)

```bash
# Install Certbot
# Ubuntu/Debian:
sudo apt install certbot python3-certbot-nginx

# CentOS/RHEL:
sudo yum install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d www.myanalytiq.org -d myanalytiq.org

# Auto-renewal is set up automatically
```

---

## Step 6: Verify Everything Works

### Test Backend Directly
```bash
curl http://127.0.0.1:5000/api/health
# Should return: {"status":"ok"}
```

### Test Through Nginx
```bash
curl http://localhost/api/health
# Should return: {"status":"ok"}
```

### Test Production
```bash
curl https://www.myanalytiq.org/api/health
# Should return: {"status":"ok"}
```

### Test Frontend
- Visit: https://www.myanalytiq.org
- Try to sign up / sign in
- Check browser console for errors

---

## Troubleshooting

### Flask Service Not Starting

**Check service status:**
```bash
sudo systemctl status analytiq-api
```

**Check logs:**
```bash
sudo journalctl -u analytiq-api -f
```

**Common issues:**
- `.env` file missing or incorrect `DATABASE_URL`
- Python dependencies not installed
- Port 5000 already in use
- Permission issues

### Nginx Not Working

**Check Nginx status:**
```bash
sudo systemctl status nginx
```

**Check error logs:**
```bash
sudo tail -f /var/log/nginx/error.log
```

**Test configuration:**
```bash
sudo nginx -t
```

**Common issues:**
- Configuration syntax error
- Wrong path in `root` directive
- Flask backend not running

### 502 Bad Gateway

This means Nginx can't reach Flask backend:
1. Check Flask is running: `sudo systemctl status analytiq-api`
2. Check Flask is listening on 127.0.0.1:5000
3. Check firewall isn't blocking
4. Check Nginx error logs

### CORS Errors

1. Make sure Flask backend is accessible
2. Check `app.py` has your domain in `ALLOWED_ORIGINS`
3. Verify Nginx proxy is working

---

## Service Management Commands

### Flask Service

```bash
# Status
sudo systemctl status analytiq-api

# Start
sudo systemctl start analytiq-api

# Stop
sudo systemctl stop analytiq-api

# Restart
sudo systemctl restart analytiq-api

# View logs
sudo journalctl -u analytiq-api -f
```

### Nginx

```bash
# Status
sudo systemctl status nginx

# Restart
sudo systemctl restart nginx

# Reload (without downtime)
sudo systemctl reload nginx

# Test config
sudo nginx -t
```

---

## Security Checklist

- [ ] Flask only listens on 127.0.0.1 (not 0.0.0.0)
- [ ] SSL/HTTPS configured
- [ ] Firewall configured (allow 80, 443, deny 5000 from outside)
- [ ] `.env` file has secure permissions (chmod 600)
- [ ] Database credentials are secure
- [ ] Regular backups configured
- [ ] Updates applied regularly

---

## Updating Your Application

When you push changes to GitHub:

```bash
# On your server
cd /path/to/AnalytIQ
git pull origin main

# Restart Flask service to apply changes
sudo systemctl restart analytiq-api
```

---

## Next Steps

1. ✅ Set up monitoring (optional but recommended)
2. ✅ Set up automated backups
3. ✅ Configure email notifications for errors
4. ✅ Set up log rotation

---

## Quick Reference

**Project directory:** `/path/to/AnalytIQ`  
**Nginx config:** `/etc/nginx/sites-available/myanalytiq.conf`  
**Service file:** `/etc/systemd/system/analytiq-api.service`  
**Flask logs:** `journalctl -u analytiq-api -f`  
**Nginx logs:** `/var/log/nginx/`

