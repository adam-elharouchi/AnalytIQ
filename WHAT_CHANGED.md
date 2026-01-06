# What Changed and Why?

## The Problem

**Before:** Your site was probably only working **locally** (on your computer).

**Now:** When you deployed to **production** (`www.myanalytiq.org`), it stopped working because:

### Browser Security Feature

Modern browsers **block** public websites from accessing `localhost`. This is a security feature called "Private Network Access" or "CORS for localhost".

**What happened:**
- ✅ **Local testing** (`localhost:8080` → `localhost:5001`) = Works fine
- ❌ **Production** (`www.myanalytiq.org` → `localhost:5001`) = Browser blocks it

This is **not a bug** - it's a browser security feature to prevent websites from accessing your local network.

---

## The Simple Fix

You have **2 options**:

### Option 1: Keep Using Localhost (For Local Testing Only)

If you **only** test locally and don't need production to work, we can revert the changes:

```javascript
// Simple - always use localhost:5001
const API_BASE_URL = 'http://localhost:5001/api';
```

**But this means production will NEVER work.**

---

### Option 2: Use Relative URLs (For Production)

This is what I changed it to. Now:
- **Local:** `http://localhost:8080` → Uses `/api` (via proxy) → Flask on `localhost:5001`
- **Production:** `www.myanalytiq.org` → Uses `/api` → Needs reverse proxy → Flask on server

**This requires setting up the reverse proxy, BUT it works everywhere.**

---

## Why the Reverse Proxy?

The reverse proxy makes it so:
- Your HTML files are served from `www.myanalytiq.org/`
- Your API requests go to `www.myanalytiq.org/api`
- Nginx forwards `/api` requests to Flask on the same server
- **Everything is on the same domain = No CORS issues!**

---

## What Do You Want?

**Question:** Was your site actually working on `www.myanalytiq.org` before, or only locally?

### If it was ONLY working locally:
- **Nothing broke!** We just need to set up production properly
- The reverse proxy setup is one-time
- After that, it will work everywhere

### If it WAS working on production:
- Something else might have changed (check git history)
- Or maybe Flask was deployed differently before?
- Let me know and I can help figure out what was different

---

## Simplest Solution

If you want the **easiest** path forward:

1. **For local development:** Just use `./start_all.sh` (already works)
2. **For production:** Run the setup script once (5 minutes), then it works forever

The setup script I created does everything automatically - it's not as complicated as it seems!

---

## Alternative: Don't Use Production

If you **don't need** the site to work on `www.myanalytiq.org`:
- Keep testing locally
- Don't set up the reverse proxy
- Revert to simple `localhost:5001` everywhere

**But then users can't access it online.**

---

Let me know what you prefer! I can:
1. **Simplify** - Revert changes if you only need local
2. **Help set up production** - Guide you through the reverse proxy (it's actually simple)
3. **Find the old way** - If something else was working before, let's figure it out

