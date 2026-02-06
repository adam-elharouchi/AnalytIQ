# Supabase Setup Guide

## Getting Your Supabase URL and Anon Key

### Step 1: Go to Your Supabase Project Dashboard
1. Visit https://supabase.com/dashboard
2. Select your project (or create one if you haven't)

### Step 2: Get Your Credentials

#### Option A: From Project Settings
1. Click on the **Settings** icon (gear icon) in the left sidebar
2. Click on **API** in the settings menu
3. You'll see two important values:

**Project URL**:
```
https://your-project-id.supabase.co
```
Copy this - this is your `SUPABASE_URL`

**anon/public key** (under "Project API keys"):
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
Copy this - this is your `SUPABASE_KEY`

#### Option B: Quick Access
1. From your project dashboard, look for the **Connect** button
2. The URL and anon key are usually displayed there

### Step 3: Add to Your .env File

Add these lines to `/Users/aelharouchi/Documents/GitHub/AnalytIQ/.env`:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_BUCKET=pdfs
```

### Step 4: Verify Storage Bucket

1. In Supabase Dashboard, go to **Storage** (bucket icon in sidebar)
2. You should see your `pdfs` bucket
3. Click on the bucket → **Settings**
4. Make sure it's set to **Public** (or configure RLS policies if you want private)

---

## Redis Setup (Without Homebrew)

Since Homebrew is not installed, here are alternative ways to install Redis:

### Option 1: Install Homebrew First (Recommended)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# After installation, install Redis
brew install redis
brew services start redis
```

### Option 2: Use Docker (If you have Docker)
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

### Option 3: Download Redis Manually
```bash
# Download and compile Redis
cd /tmp
curl -O http://download.redis.io/redis-stable.tar.gz
tar xzvf redis-stable.tar.gz
cd redis-stable
make
sudo make install

# Start Redis server
redis-server
```

### Option 4: Use Cloud Redis (No local installation needed)
- **Upstash**: https://upstash.com (Free tier available)
- **Redis Cloud**: https://redis.com/try-free (Free tier available)

If using cloud Redis, update your `.env`:
```bash
REDIS_URL=redis://your-cloud-redis-url:6379
```

---

## Testing Your Setup

Once you have both Supabase and Redis configured:

```bash
# Test Supabase connection
python3 -c "
from supabase_storage import check_storage_health
result = check_storage_health()
print(result)
"

# Test Redis connection
python3 -c "
from cache import cache_health_check
result = cache_health_check()
print(result)
"
```

---

## Quick Start Commands

```bash
# 1. Start Redis (if installed locally)
redis-server

# 2. Start Celery worker (in another terminal)
cd /Users/aelharouchi/Documents/GitHub/AnalytIQ
celery -A celery_app worker --loglevel=info

# 3. Start Flask app (in another terminal)
cd /Users/aelharouchi/Documents/GitHub/AnalytIQ
python app.py
```
