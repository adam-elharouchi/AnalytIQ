# AnalytIQ Deployment Guide

This guide ensures the application works perfectly for all users across all platforms (macOS, Windows, Linux).

## 🎯 Architecture Overview

AnalytIQ uses a **client-server architecture**:

- **Frontend**: Static HTML/CSS/JavaScript files (served from `myanalytiq.org`)
- **Backend**: Flask API server (deployed on Render at `analytiq-qbfr.onrender.com`)
- **Database**: PostgreSQL (hosted on Supabase)

## 🔧 How It Works for Users

### For End Users (Students/Professors)
**No setup required!** Users simply:
1. Visit `https://www.myanalytiq.org`
2. Sign in with their credentials
3. The frontend automatically connects to the production backend

The application automatically detects whether it's running locally or in production and uses the appropriate backend URL.

### For Developers (Local Development)
Developers need to run the Flask backend locally:

```bash
# Start the local backend server
python3 app.py
# or
./start_server.sh
```

The server runs on `http://localhost:5001` and connects to the Supabase database.

## 📋 Production Deployment Checklist

### 1. Render Backend Deployment

The Flask backend is deployed on Render. **Critical environment variables** that must be set:

#### Required Environment Variables on Render:

```bash
# Database Connection (REQUIRED)
DATABASE_URL=postgresql://postgres.PROJECT_ID:PASSWORD@aws-0-us-west-2.pooler.supabase.com:5432/postgres

# Email Configuration (for password reset)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
MAIL_SENDER_NAME=AnalytIQ Services

# Frontend URL (for password reset links)
FRONTEND_URL=https://www.myanalytiq.org

# Flask Configuration
FLASK_ENV=production
PORT=10000  # Render assigns this automatically
```

#### How to Set Environment Variables on Render:

1. Go to your Render dashboard
2. Select the `analytiq-qbfr` service
3. Navigate to **Environment** tab
4. Add each variable listed above
5. Click **Save Changes**
6. Render will automatically redeploy

### 2. Database Connection Configuration

The application uses **Supabase Pooler** for database connections with the following settings:

- **Connection Timeout**: 10 seconds
- **Statement Timeout**: 30 seconds
- **Connection Pool**: 1-10 connections
- **Retry Logic**: 3 attempts with 1-second delays

#### Supabase Connection Modes:

- **Session Mode (Port 5432)**: Default, used for long-lived connections
- **Transaction Mode (Port 6543)**: Alternative for serverless environments

The application automatically handles both modes.

### 3. Frontend Deployment

The frontend is served from `myanalytiq.org` and automatically detects the environment:

```javascript
// Automatic backend URL detection
const isLocal = window.location.hostname === 'localhost' || 
                window.location.hostname === '127.0.0.1' ||
                window.location.protocol === 'file:';

window.API_BASE_URL = isLocal
    ? 'http://localhost:5001/api'
    : 'https://analytiq-qbfr.onrender.com/api';
```

## 🚨 Troubleshooting

### Issue: "Connection timed out" Error

**Symptoms**: Users see "could not send data to server: Connection timed out" when signing in.

**Causes**:
1. ❌ Backend server not running (local development)
2. ❌ DATABASE_URL not set on Render
3. ❌ Supabase database is down or unreachable
4. ❌ Firewall blocking connections

**Solutions**:

#### For Local Development:
```bash
# 1. Check if server is running
lsof -i :5001

# 2. If not running, start it
python3 app.py

# 3. Verify database connection
python3 test_db_connection.py

# 4. Check health endpoint
curl http://localhost:5001/api/health
```

#### For Production (Render):
1. Check Render logs for errors:
   - Go to Render dashboard → Your service → Logs
   - Look for database connection errors

2. Verify environment variables:
   - Ensure `DATABASE_URL` is set correctly
   - Format: `postgresql://USER:PASSWORD@HOST:PORT/DATABASE`

3. Test the health endpoint:
   ```bash
   curl https://analytiq-qbfr.onrender.com/api/health
   ```
   
   Expected response:
   ```json
   {
     "status": "ok",
     "database": "connected",
     "timestamp": "2026-02-04T22:27:13.222096"
   }
   ```

4. If database shows "disconnected":
   - Check Supabase dashboard for database status
   - Verify DATABASE_URL is correct
   - Check Supabase connection pooler settings

### Issue: Port 5000 Already in Use (macOS)

**Symptom**: Can't start Flask server on port 5000.

**Cause**: macOS uses port 5000 for AirPlay Receiver.

**Solution**: The app is already configured to use port 5001 by default.

```python
# app.py (line 4106)
port = int(os.getenv('PORT', 5001))  # Changed from 5000 to avoid macOS AirPlay conflict
```

### Issue: Database Connection Fails Locally

**Symptom**: Local server can't connect to Supabase.

**Solutions**:

1. Check `.env` file exists and has correct DATABASE_URL:
   ```bash
   cat .env
   ```

2. Test connection directly:
   ```bash
   python3 test_db_connection.py
   ```

3. Verify Supabase pooler is accessible:
   - Check Supabase dashboard
   - Ensure your IP isn't blocked
   - Try both port 5432 (session) and 6543 (transaction)

## 🔍 Health Monitoring

### Health Check Endpoint

**URL**: `/api/health`

**Response (Healthy)**:
```json
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2026-02-04T22:27:13.222096"
}
```

**Response (Unhealthy)**:
```json
{
  "status": "degraded",
  "database": "disconnected",
  "error": "connection timeout",
  "timestamp": "2026-02-04T22:27:13.222096"
}
```

### Monitoring Commands

```bash
# Check production backend health
curl https://analytiq-qbfr.onrender.com/api/health

# Check local backend health
curl http://localhost:5001/api/health

# Test signin endpoint (production)
curl -X POST https://analytiq-qbfr.onrender.com/api/users/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"test@student.hult.edu","password":"test"}'

# Test signin endpoint (local)
curl -X POST http://localhost:5001/api/users/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"test@student.hult.edu","password":"test"}'
```

## 🔐 Security Best Practices

1. **Never commit `.env` file** - It contains sensitive credentials
2. **Use environment variables** on Render for all secrets
3. **Enable SSL/TLS** - Already configured with `sslmode=require`
4. **Rotate passwords** regularly for database and email accounts
5. **Monitor logs** for suspicious activity

## 📊 Performance Optimization

### Connection Pooling
- **Min connections**: 1
- **Max connections**: 10
- **Automatic retry**: 3 attempts with 1s delay
- **Connection timeout**: 10 seconds
- **Query timeout**: 30 seconds

### Caching
- Frontend implements API response caching
- Cache TTL: 5 minutes
- Automatic cache invalidation on mutations

## 🚀 Deployment Workflow

### Deploying Backend Updates

1. **Commit changes** to GitHub:
   ```bash
   git add .
   git commit -m "Update backend"
   git push origin main
   ```

2. **Render auto-deploys** from GitHub
   - Deployment typically takes 2-3 minutes
   - Monitor deployment in Render dashboard

3. **Verify deployment**:
   ```bash
   curl https://analytiq-qbfr.onrender.com/api/health
   ```

### Deploying Frontend Updates

1. **Update files** on your hosting provider (GitHub Pages, Netlify, etc.)
2. **Clear browser cache** to see changes
3. **Test** on production URL

## 📞 Support

If issues persist after following this guide:

1. Check Render logs for detailed error messages
2. Verify all environment variables are set correctly
3. Test database connection using `test_db_connection.py`
4. Contact support with:
   - Error message from browser console
   - Response from `/api/health` endpoint
   - Render deployment logs

## ✅ Pre-Deployment Checklist

Before deploying to production, verify:

- [ ] DATABASE_URL is set on Render
- [ ] All email configuration variables are set
- [ ] FRONTEND_URL points to production domain
- [ ] Health endpoint returns "connected" status
- [ ] Test signin/signup flows work
- [ ] Password reset emails are being sent
- [ ] Frontend detects production environment correctly
- [ ] CORS headers allow frontend domain
- [ ] SSL/TLS is enabled (sslmode=require)
- [ ] Connection timeouts are configured

---

**Last Updated**: February 4, 2026
**Maintainer**: AnalytIQ Development Team
