# Quick Setup Instructions

## For Local Development

### Option 1: Use the All-in-One Script (Easiest)

```bash
./start_all.sh
```

This will:
- Start Flask backend on port 5000
- Start frontend proxy on port 8080
- Open your site at http://localhost:8080

### Option 2: Start Manually

**Terminal 1 - Start Flask backend:**
```bash
./start_backend.sh
# or
python3 app.py
```

**Terminal 2 - Start frontend proxy:**
```bash
python3 start_server.py
```

Then visit: http://localhost:8080

---

## For Production (www.myanalytiq.org)

### Step 1: Install Nginx (if not installed)

**On macOS:**
```bash
brew install nginx
```

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install nginx
```

### Step 2: Copy Nginx Configuration

**On macOS:**
```bash
# Copy config file
sudo cp nginx.conf /usr/local/etc/nginx/servers/myanalytiq.conf

# Edit the path in the config file
sudo nano /usr/local/etc/nginx/servers/myanalytiq.conf
# Update the 'root' path to your actual project directory
```

**On Linux:**
```bash
# Copy config file
sudo cp nginx.conf /etc/nginx/sites-available/myanalytiq.conf

# Edit the path in the config file
sudo nano /etc/nginx/sites-available/myanalytiq.conf
# Update the 'root' path to your actual project directory

# Create symlink
sudo ln -s /etc/nginx/sites-available/myanalytiq.conf /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default
```

### Step 3: Update Configuration Path

Edit the nginx config file and update this line:
```nginx
root /Users/aelharouchi/Documents/GitHub/AnalytIQ;  # Change to your actual path
```

### Step 4: Test and Reload Nginx

```bash
# Test configuration
sudo nginx -t

# If test passes, reload nginx
sudo nginx -s reload
# or on Linux
sudo systemctl reload nginx
```

### Step 5: Set Up Flask Backend as a Service

**On macOS (using launchd):**

Create `/Library/LaunchDaemons/com.analytiq.api.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.analytiq.api</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/aelharouchi/Documents/GitHub/AnalytIQ/app.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/aelharouchi/Documents/GitHub/AnalytIQ</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/bin:/usr/local/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Then:
```bash
sudo launchctl load /Library/LaunchDaemons/com.analytiq.api.plist
```

**On Linux (using systemd):**

Create `/etc/systemd/system/analytiq-api.service`:
```ini
[Unit]
Description=AnalytIQ Flask API
After=network.target

[Service]
User=your-username
WorkingDirectory=/path/to/AnalytIQ
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /path/to/AnalytIQ/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable analytiq-api
sudo systemctl start analytiq-api
```

### Step 6: Set Up SSL (HTTPS)

**Using Let's Encrypt (Free):**

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx  # Ubuntu/Debian
brew install certbot  # macOS

# Get certificate
sudo certbot --nginx -d www.myanalytiq.org -d myanalytiq.org

# Auto-renewal is set up automatically
```

### Step 7: Test

1. Visit: https://www.myanalytiq.org
2. Check API: https://www.myanalytiq.org/api/health
3. Check browser console for any errors

---

## Troubleshooting

### Flask backend not starting
- Check if port 5000 is already in use: `lsof -i :5000`
- Make sure `.env` file exists with `DATABASE_URL`
- Check Flask logs for errors

### Nginx not working
- Test config: `sudo nginx -t`
- Check nginx error logs: `tail -f /var/log/nginx/error.log`
- Make sure Flask is running: `curl http://127.0.0.1:5000/api/health`

### CORS errors
- Check that `app.py` has your domain in `ALLOWED_ORIGINS`
- Make sure Nginx is proxying correctly

### 502 Bad Gateway
- Flask backend is not running or not accessible
- Check Flask is running on `127.0.0.1:5000`
- Check firewall settings

---

## Quick Test Commands

```bash
# Test Flask backend directly
curl http://127.0.0.1:5000/api/health

# Test through Nginx (local)
curl http://localhost/api/health

# Test production API
curl https://www.myanalytiq.org/api/health
```

