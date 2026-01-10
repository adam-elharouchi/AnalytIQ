# Backend Deployment Instructions

## Problem
The frontend is deployed but the backend API is returning 404 errors because the Flask app isn't running on the production server.

## Solution: Deploy Flask Backend

### Option 1: Run Flask on Your Server (Recommended if you have server access)

1. **SSH into your server** (www.myanalytiq.org):
   ```bash
   ssh user@myanalytiq.org
   ```

2. **Navigate to your project directory**:
   ```bash
   cd /path/to/AnalytIQ
   ```

3. **Install Python dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file with:
   ```
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.omjttmkczfpnwyzrdzqi.supabase.co:5432/postgres
   ```

5. **Start Flask with a process manager** (using systemd or supervisor):
   
   **Create a systemd service** (`/etc/systemd/system/analytiq-api.service`):
   ```ini
   [Unit]
   Description=AnalytIQ Flask API
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/path/to/AnalytIQ
   Environment="PATH=/usr/bin:/usr/local/bin"
   EnvironmentFile=/path/to/AnalytIQ/.env
   ExecStart=/usr/bin/python3 /path/to/AnalytIQ/app.py 5001
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   **Enable and start the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable analytiq-api
   sudo systemctl start analytiq-api
   ```

6. **Verify Flask is running**:
   ```bash
   curl http://localhost:5001/api/health
   ```

7. **Update nginx configuration** (if needed):
   - Make sure nginx.conf proxies to port 5001 (already fixed)
   - Reload nginx: `sudo nginx -t && sudo nginx -s reload`

### Option 2: Deploy to Cloud Platform (Heroku, Railway, Render, etc.)

#### Using Railway:

1. **Install Railway CLI**:
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Initialize Railway project**:
   ```bash
   railway init
   railway link
   ```

3. **Set environment variables**:
   ```bash
   railway variables set DATABASE_URL=postgresql://...
   ```

4. **Deploy**:
   ```bash
   railway up
   ```

5. **Update frontend API_BASE_URL** in `js/api-helper.js`:
   ```javascript
   return 'https://your-app.railway.app/api';
   ```

#### Using Render:

1. Create new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Add environment variable: `DATABASE_URL`
6. Deploy

### Option 3: Use Gunicorn for Production

For production, use Gunicorn instead of Flask's development server:

1. **Install Gunicorn**:
   ```bash
   pip install gunicorn
   ```

2. **Create a Procfile**:
   ```
   web: gunicorn app:app --bind 0.0.0.0:5001 --workers 4
   ```

3. **Start with Gunicorn**:
   ```bash
   gunicorn app:app --bind 0.0.0.0:5001 --workers 4
   ```

## Verify Deployment

After deploying, test these endpoints:

1. **Health check**: `curl http://your-domain.com/api/health`
2. **Grand leaderboard**: `curl http://your-domain.com/api/leaderboard/grand?limit=10`
3. **Progress endpoint**: `curl http://your-domain.com/api/exercises/progress?user_id=TEST`

All should return JSON responses, not 404 errors.

## Important Notes

- **Port mismatch fixed**: nginx.conf now proxies to port 5001 (matches Flask default)
- **CORS is configured**: Flask already has CORS headers set up
- **Database connection**: Make sure DATABASE_URL is set correctly
- **Firewall**: Ensure port 5001 is accessible locally (nginx will handle external access)

## Quick Fix for Testing

If you just want to test quickly, you can run Flask directly on your server:

```bash
cd /path/to/AnalytIQ
python3 app.py 5001
```

Then test: `curl http://localhost:5001/api/health`

If this works but `http://www.myanalytiq.org/api/health` doesn't, the issue is with nginx configuration or nginx isn't running.
