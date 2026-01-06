# API Configuration Guide

## Problem
When deploying to production (`www.myanalytiq.org`), the frontend tries to call `localhost:5001`, which browsers block for security reasons.

## Solution

### Option 1: Deploy Backend to Same Domain (Recommended if possible)
If you can deploy the Flask backend to the same domain:
- Update the API_BASE_URL in the JavaScript files to use a relative path: `/api`

### Option 2: Deploy Backend to Subdomain
Deploy your Flask backend to `api.myanalytiq.org`:
- The code is already configured to use `https://api.myanalytiq.org/api`
- Make sure your DNS points `api.myanalytiq.org` to your backend server

### Option 3: Use a Hosting Service
Deploy your Flask backend to a service like:
- **Railway**: https://railway.app
- **Render**: https://render.com
- **Heroku**: https://heroku.com
- **Fly.io**: https://fly.io
- **PythonAnywhere**: https://pythonanywhere.com

Then update the `API_BASE_URL` in these files to point to your deployed backend:
- `js/api-helper.js`
- `js/auth.js`
- `js/profile.js`

## Current Configuration

The frontend automatically detects the environment:
- **Development** (localhost): Uses `http://localhost:5001/api`
- **Production**: Uses `https://api.myanalytiq.org/api` (update this to your actual backend URL)

## Backend CORS Configuration

The backend (`app.py`) is configured to allow requests from:
- Localhost (all ports)
- `www.myanalytiq.org`
- `myanalytiq.org`
- `adamelharouchi5-blip.github.io`

If you deploy to a different domain, add it to the `ALLOWED_ORIGINS` list in `app.py`.

## Quick Fix (Temporary)

If you need the site to work immediately while setting up the backend:
1. The frontend has localStorage fallbacks, so basic features will work offline
2. User data (profiles, conversations) will be stored locally until the backend is connected
3. Some features like conversation history sync won't work without the backend

## Next Steps

1. **Deploy your Flask backend** to a publicly accessible URL
2. **Update the API_BASE_URL** in the three JavaScript files if needed
3. **Update CORS settings** in `app.py` to include your production domain
4. **Test** by checking the browser console for successful API calls

