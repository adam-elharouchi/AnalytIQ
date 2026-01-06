# 🚀 Quick Start: Production Server Setup

## One-Command Setup

Everything is automated! Just run this on your production server:

```bash
sudo ./setup_production.sh
```

That's it! The script will:
- ✅ Install Nginx
- ✅ Install Python dependencies
- ✅ Set up reverse proxy
- ✅ Create Flask service
- ✅ Start everything

---

## Prerequisites

Before running the script, make sure:

1. **You have SSH access** to your production server
2. **Your project files are on the server** (upload via Git, SCP, etc.)
3. **You have sudo/root access** on the server
4. **Your domain points to the server** (`www.myanalytiq.org` → your server IP)

---

## Step-by-Step Instructions

### 1. Upload Your Project to Server

**Option A: Using Git (Recommended)**
```bash
ssh user@your-server-ip
cd /var/www  # or wherever you want it
git clone https://github.com/adamelharouchi5-blip/AnalytIQ.git
cd AnalytIQ
```

**Option B: Using SCP**
```bash
# From your local machine
scp -r /Users/aelharouchi/Documents/GitHub/AnalytIQ user@your-server-ip:/path/to/destination/
```

### 2. Set Up .env File

```bash
cd /path/to/AnalytIQ
nano .env
```

Add your database URL:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/postgres
```

### 3. Run the Setup Script

```bash
chmod +x setup_production.sh
sudo ./setup_production.sh
```

The script will guide you through everything!

### 4. Test It

```bash
# Test Flask backend
curl http://127.0.0.1:5000/api/health

# Test through Nginx
curl http://localhost/api/health

# Test from your computer
curl http://www.myanalytiq.org/api/health
```

### 5. Set Up SSL (Optional but Recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d www.myanalytiq.org -d myanalytiq.org
```

---

## Troubleshooting

### Script Fails to Run

**Make it executable:**
```bash
chmod +x setup_production.sh
```

**Check if you're in the right directory:**
```bash
ls -la setup_production.sh
```

### Flask Service Won't Start

**Check status:**
```bash
sudo systemctl status analytiq-api
```

**Check logs:**
```bash
sudo journalctl -u analytiq-api -f
```

**Common issues:**
- `.env` file missing or wrong `DATABASE_URL`
- Python dependencies not installed
- Port 5000 already in use

### Nginx Won't Start

**Check status:**
```bash
sudo systemctl status nginx
```

**Test configuration:**
```bash
sudo nginx -t
```

**Check error logs:**
```bash
sudo tail -f /var/log/nginx/error.log
```

### Can't Access Website

**Check firewall:**
```bash
# Allow HTTP
sudo ufw allow 80/tcp
# Allow HTTPS
sudo ufw allow 443/tcp
```

**Check DNS:**
```bash
# Make sure your domain points to server
nslookup www.myanalytiq.org
```

---

## After Setup

### Update Your Application

When you push changes to GitHub:

```bash
cd /path/to/AnalytIQ
git pull origin main
sudo systemctl restart analytiq-api
```

### View Logs

```bash
# Flask logs
sudo journalctl -u analytiq-api -f

# Nginx logs
sudo tail -f /var/log/nginx/analytiq_access.log
sudo tail -f /var/log/nginx/analytiq_error.log
```

### Manage Services

```bash
# Flask service
sudo systemctl restart analytiq-api
sudo systemctl stop analytiq-api
sudo systemctl start analytiq-api

# Nginx
sudo systemctl restart nginx
sudo systemctl reload nginx
```

---

## What the Script Does

1. **Installs Nginx** - Web server for reverse proxy
2. **Installs Python dependencies** - From requirements.txt
3. **Creates Nginx config** - Sets up reverse proxy
4. **Sets up Flask service** - Creates systemd service
5. **Starts everything** - Enables and starts services

---

## Files Created

- `/etc/nginx/sites-available/myanalytiq` - Nginx configuration
- `/etc/systemd/system/analytiq-api.service` - Flask service file

---

## Need Help?

See `PRODUCTION_SETUP.md` for detailed manual instructions and troubleshooting.

