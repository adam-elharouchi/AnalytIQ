# Code Assistant Debug Guide

## Issue
The code assistant API doesn't work locally but works in the published version.

## What the Code Assistant Uses
The code assistant uses **Google's Gemini API directly** (NOT our backend API):
- API Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- API Key: Stored in `js/code-assistant.js` as `GEMINI_API_KEY`

## Possible Issues

### 1. **API Key is Blocked** (Most Likely)
The hardcoded API key `AIzaSyDURc7Q5UxgJZs_L9H3DaJzQD9Rysme_Ws` appears to be blocked:
- Error: `403 PERMISSION_DENIED - API_KEY_SERVICE_BLOCKED`
- The published version might be using a different API key

**Solution**: Use a valid Gemini API key

### 2. **Backend API Dependency**
The code calls `preferencesAPI.get()` during initialization, which requires:
- Backend server running on `http://localhost:5001`
- User to be logged in (has `currentUser` in localStorage)

**Check**: 
- Is backend running? `curl http://localhost:5001/api/health`
- Are you logged in? Check browser console for errors

### 3. **CORS Issues**
Local development might have CORS issues with Google's API

### 4. **Network/Firewall**
Local network might be blocking requests to `generativelanguage.googleapis.com`

## Quick Checks

1. **Open Browser Console (F12)** when using code assistant
   - Look for errors related to:
     - `generativelanguage.googleapis.com`
     - `API_KEY_SERVICE_BLOCKED`
     - `PERMISSION_DENIED`
     - `preferencesAPI`
     - Network errors

2. **Check if backend is running**:
   ```bash
   curl http://localhost:5001/api/health
   ```

3. **Check if user is logged in**:
   - Open browser console
   - Run: `JSON.parse(localStorage.getItem('currentUser'))`
   - Should return user object, not null

4. **Test Gemini API directly**:
   ```bash
   curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"contents":[{"role":"user","parts":[{"text":"test"}]}]}'
   ```

## Differences: Local vs Published

The published version works, which suggests:
- Published version might use a different API key
- Published version might not call `preferencesAPI` (fallback to localStorage)
- Published version might have different CORS configuration
- Published version might proxy requests through a backend

## Next Steps

1. Check browser console for specific error messages
2. Verify backend server is running
3. Verify you're logged in
4. Check if the Gemini API key is valid
5. Compare the published version's code with local version

