# Fix Gemini API 403 Error

## The Problem
The Gemini API key `REDACTED_GEMINI_API_KEY` is blocked (403 Forbidden).

## Solutions

### Option 1: Get a New API Key (Recommended)
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Enable the Generative Language API:
   - Go to https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com
   - Select your project
   - Click "Enable"
4. Replace the API key in `js/code-assistant.js` line 16:
   ```javascript
   const GEMINI_API_KEY = 'YOUR_NEW_API_KEY_HERE';
   ```

### Option 2: Use Your Own API Key from localStorage
The code already checks localStorage for `geminiApiKey` or `aiApiKey`. You can:
1. Open browser console
2. Run: `localStorage.setItem('geminiApiKey', 'YOUR_API_KEY')`
3. Refresh the page

### Option 3: Check if API is Enabled
The error might be that the API isn't enabled for the project:
1. Go to https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com
2. Make sure the API is enabled for the project associated with your API key

## Why Published Version Works
The published version likely:
- Uses a different API key
- Has the API enabled for that key's project
- Or proxies requests through a backend

