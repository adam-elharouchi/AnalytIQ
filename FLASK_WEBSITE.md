# 🚀 Flask Website - Complete Setup

Your Flask app now serves **both frontend and API**! No Nginx needed.

## Quick Start

```bash
# Simple way
./run_flask.sh

# Or directly
python3 app.py
```

Then visit: **http://localhost:5000**

---

## What Changed

✅ **app.py now serves static files** (HTML, CSS, JS)  
✅ **All API routes work** (from your existing app.py)  
✅ **No reverse proxy needed** - Flask handles everything  
✅ **Works locally and in production**

---

## How It Works

- **Frontend files**: Served by Flask at `http://localhost:5000/`
- **API endpoints**: Available at `http://localhost:5000/api/*`
- **Everything on same domain**: No CORS issues!

---

## Deploying to Production

### Option 1: Run Directly (Simple)

```bash
python3 app.py
```

Access at: `http://your-server-ip:5000`

### Option 2: Use a Process Manager

**With systemd:**
```bash
sudo systemctl start analytiq-api  # (from earlier setup)
```

**With PM2:**
```bash
pm2 start app.py --interpreter python3 --name analytiq
```

### Option 3: Behind a Reverse Proxy (Optional)

If you want to use port 80/443, you can still use Nginx:
- Nginx on port 80 → proxies to Flask on port 5000
- But Flask can serve everything directly too!

---

## Configuration

Set environment variables:

```bash
# Port (default: 5000)
export PORT=5000

# Host (default: 0.0.0.0 for production, 127.0.0.1 for local)
export HOST=0.0.0.0

# Debug mode
export FLASK_DEBUG=False

# Database
export DATABASE_URL=postgresql://user:pass@host:5432/db
```

Or use `.env` file:
```
PORT=5000
HOST=0.0.0.0
FLASK_DEBUG=False
DATABASE_URL=postgresql://...
```

---

## Testing

```bash
# Test frontend
curl http://localhost:5000/

# Test API
curl http://localhost:5000/api/health
```

---

## That's It!

Your Flask app is now a complete website. Just run it and everything works! 🎉

