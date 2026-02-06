# Quick Start Guide - Phase 3 Setup

## Current Status
✅ Supabase Storage: **WORKING**
✅ Python Libraries: **INSTALLED**
⏳ Homebrew: **INSTALLING** (waiting for password)
❌ Redis Server: **NOT INSTALLED YET**

---

## Step 1: Complete Homebrew Installation

**In your terminal**, you should see:
```
Password:
```

Type your Mac password and press Enter (characters won't show - this is normal).

---

## Step 2: Install Redis (After Homebrew Completes)

Run these commands:
```bash
brew install redis
brew services start redis
```

Verify Redis is running:
```bash
redis-cli ping
# Should respond: PONG
```

---

## Step 3: Test Everything

```bash
cd /Users/aelharouchi/Documents/GitHub/AnalytIQ

# Test Supabase (already working)
python3 -c "from supabase_storage import check_storage_health; print(check_storage_health())"

# Test Redis (after step 2)
python3 -c "from cache import cache_health_check; print(cache_health_check())"

# Test Celery configuration
python3 -c "from celery_app import celery_app; print('Celery OK')"
```

---

## Step 4: Start Services (Optional - For Testing)

### Terminal 1: Redis
```bash
redis-server
# Or if using brew services: brew services start redis
```

### Terminal 2: Celery Worker
```bash
cd /Users/aelharouchi/Documents/GitHub/AnalytIQ
celery -A celery_app worker --loglevel=info
```

### Terminal 3: Flask App
```bash
cd /Users/aelharouchi/Documents/GitHub/AnalytIQ
python app.py
```

---

## Step 5: Enable Features (When Ready)

Edit `.env` to enable features:
```bash
FEATURE_ASYNC_TASKS=True   # Enable Celery background tasks
FEATURE_CACHING=True       # Enable Redis caching
```

---

## Step 6: Migrate PDFs (When Ready)

```bash
# Dry run first (safe - no changes)
python scripts/migrate_pdfs.py --dry-run

# Actual migration
python scripts/migrate_pdfs.py

# Clear database PDFs (after verifying all work)
python scripts/migrate_pdfs.py --clear-data
```

---

## Troubleshooting

### Redis Won't Start
```bash
# Check if already running
brew services list

# Restart Redis
brew services restart redis

# Check logs
brew services info redis
```

### Celery Won't Start
```bash
# Make sure Redis is running first
redis-cli ping

# Check for errors
celery -A celery_app worker --loglevel=debug
```

### Supabase Connection Issues
```bash
# Verify credentials in .env
cat .env | grep SUPABASE

# Test connection
python3 -c "from supabase_storage import check_storage_health; print(check_storage_health())"
```

---

## What's Working Right Now

Even without Redis, you can:

1. **Upload PDFs to Supabase**:
   ```python
   from supabase_storage import upload_pdf
   with open('test.pdf', 'rb') as f:
       url = upload_pdf(f.read(), 'test.pdf')
       print(url)
   ```

2. **Run the Flask app** (without async features):
   ```bash
   python app.py
   ```

3. **Test the migration script** (dry run):
   ```bash
   python scripts/migrate_pdfs.py --dry-run
   ```

---

## Next Steps Summary

1. ⏳ Enter password in terminal to complete Homebrew installation
2. 📦 Install Redis: `brew install redis && brew services start redis`
3. ✅ Test everything works
4. 🚀 Enable features when ready
5. 📁 Migrate PDFs when ready

**Estimated time**: 10-15 minutes
