# Quick Deploy Guide - Backend API

## Easiest Option: Run on Your Server

### Step 1: Install Dependencies

SSH into your server:
```bash
ssh user@myanalytiq.org
cd /path/to/AnalytIQ
pip3 install -r requirements.txt
```

### Step 2: Set Up Environment

Make sure you have a `.env` file:
```bash
echo "DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.omjttmkczfpnwyzrdzqi.supabase.co:5432/postgres" > .env
```

### Step 3: Make Script Executable

```bash
chmod +x start_server.sh
```

### Step 4: Start the Server

**Option A: Run directly (for testing)**
```bash
./start_server.sh
```

**Option B: Run in background**
```bash
nohup ./start_server.sh > api.log 2>&1 &
```

**Option C: Use systemd (recommended for production)**

1. Copy the service file:
```bash
sudo cp analytiq-api.service /etc/systemd/system/
```

2. Update the paths in the service file:
```bash
sudo nano /etc/systemd/system/analytiq-api.service
```
Change `/var/www/AnalytIQ` to your actual project path.

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable analytiq-api
sudo systemctl start analytiq-api
```

4. Check status:
```bash
sudo systemctl status analytiq-api
```

### Step 5: Test the API

```bash
curl http://localhost:5001/api/health
```

You should see: `{"status":"ok"}`

### Step 6: Update Nginx (if needed)

Make sure nginx is configured to proxy to port 5001 (already fixed in nginx.conf):
```bash
sudo nginx -t
sudo nginx -s reload
```

## That's It!

Your API should now be accessible at:
- `http://www.myanalytiq.org/api/health`
- `http://www.myanalytiq.org/api/leaderboard/grand`
- `http://www.myanalytiq.org/api/exercises/progress`

## Troubleshooting

**If you get "Permission denied":**
```bash
chmod +x start_server.sh
```

**If gunicorn is not found:**
```bash
pip3 install gunicorn
```

**If port 5001 is in use:**
Change the port in `start_server.sh` or `analytiq-api.service`

**To check if the server is running:**
```bash
ps aux | grep gunicorn
# or
curl http://localhost:5001/api/health
```

**To view logs (if using systemd):**
```bash
sudo journalctl -u analytiq-api -f
```

**To restart the service:**
```bash
sudo systemctl restart analytiq-api
```
