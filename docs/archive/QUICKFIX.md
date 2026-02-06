# 🚨 CRITICAL: Fix "Connection Timed Out" Error

## The Problem
Users see: **"could not send data to server: Connection timed out"** when signing in.

## The Root Cause
The **DATABASE_URL environment variable is not set** (or is incorrect) on Render.

## The Solution (5 Minutes)

### Step 1: Get Your Supabase Connection String

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Click **Settings** → **Database**
4. Scroll to **Connection Pooling**
5. Copy the **Connection string** (Session mode)
   - Format: `postgresql://postgres.PROJECT_ID:PASSWORD@aws-0-us-west-2.pooler.supabase.com:5432/postgres`

### Step 2: Set Environment Variable on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Select your **analytiq-qbfr** service
3. Click **Environment** tab
4. Click **Add Environment Variable**
5. Set:
   - **Key**: `DATABASE_URL`
   - **Value**: Paste the connection string from Step 1
6. Click **Save Changes**

### Step 3: Wait for Automatic Redeploy

Render will automatically redeploy your service (takes ~2-3 minutes).

### Step 4: Verify the Fix

Test the health endpoint:

```bash
curl https://analytiq-qbfr.onrender.com/api/health
```

**Expected Response** (Success):
```json
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2026-02-04T22:27:13.222096"
}
```

**If Still Failing**:
```json
{
  "status": "degraded",
  "database": "disconnected",
  "error": "..."
}
```

Check:
- DATABASE_URL format is correct
- Password doesn't contain special characters that need URL encoding
- Supabase database is running (check Supabase dashboard)

## Additional Required Environment Variables

While you're in the Render Environment tab, also set these:

```bash
# Email Configuration (for password reset)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Frontend URL
FRONTEND_URL=https://www.myanalytiq.org

# Flask Environment
FLASK_ENV=production
```

## Testing After Deployment

1. **Health Check**:
   ```bash
   curl https://analytiq-qbfr.onrender.com/api/health
   ```

2. **Test Signin**:
   ```bash
   curl -X POST https://analytiq-qbfr.onrender.com/api/users/signin \
     -H "Content-Type: application/json" \
     -d '{"email":"test@student.hult.edu","password":"test"}'
   ```

3. **Test in Browser**:
   - Go to https://www.myanalytiq.org
   - Try signing in
   - Should work without "Connection timed out" error

## Why This Happens

The application needs to connect to the PostgreSQL database to:
- Authenticate users
- Store/retrieve user data
- Manage classes and exercises

Without the DATABASE_URL:
- The backend can't connect to the database
- All API requests fail with "Connection timed out"
- Users can't sign in or use any features

## Prevention

To prevent this issue in the future:

1. **Always set DATABASE_URL** when deploying to a new environment
2. **Use the health endpoint** to verify database connectivity
3. **Monitor Render logs** for connection errors
4. **Keep a backup** of your environment variables

---

**Need Help?**
- Check Render logs: Dashboard → Your Service → Logs
- Check Supabase status: Supabase Dashboard → Your Project
- See full deployment guide: `DEPLOYMENT.md`
