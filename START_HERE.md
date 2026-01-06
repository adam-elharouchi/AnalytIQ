# 🚀 Quick Start Guide

## ⚠️ Important: Don't Open HTML Files Directly!

**DO NOT:**
- ❌ Double-click `login.html` or `index.html`
- ❌ Open files with `file://` protocol
- ❌ Drag HTML files into browser

**This will cause CORS errors!**

## ✅ Correct Way to Run the Application

### Step 1: Start the Servers

Open your terminal and run:

```bash
cd /Users/aelharouchi/Documents/GitHub/AnalytIQ
./start_all.sh
```

This will:
- ✅ Start Flask backend on port 5000
- ✅ Start frontend proxy server on port 8080

### Step 2: Open in Browser

**Open your browser and go to:**

```
http://localhost:8080
```

**NOT** `file:///Users/.../login.html`

---

## 🎯 What's Happening?

1. **Flask Backend** (`localhost:5000`) - Handles API requests (signup, signin, etc.)
2. **Frontend Proxy** (`localhost:8080`) - Serves your HTML/JS files and forwards `/api/*` to Flask
3. **Your Browser** - Accesses everything through `http://localhost:8080`

---

## 🔧 Manual Start (Alternative)

If the script doesn't work, start manually:

**Terminal 1:**
```bash
cd /Users/aelharouchi/Documents/GitHub/AnalytIQ
python3 app.py
```

**Terminal 2:**
```bash
cd /Users/aelharouchi/Documents/GitHub/AnalytIQ
python3 start_server.py
```

Then open: **http://localhost:8080**

---

## ❌ Common Mistakes

### Mistake 1: Opening files directly
```
❌ file:///Users/aelharouchi/Documents/GitHub/AnalytIQ/login.html
```
**Error:** `Access to fetch at 'file:///api/users/signin'...`

### Mistake 2: Only starting Flask, not the proxy
```
✅ Flask running on :5000
❌ No proxy server running
```
**Problem:** Can't serve HTML files properly

### Correct:
```
✅ Flask running on :5000
✅ Proxy server running on :8080
✅ Browser accessing http://localhost:8080
```

---

## 🐛 Troubleshooting

### "Failed to fetch" error
- ✅ Make sure Flask is running: Check Terminal 1
- ✅ Make sure proxy server is running: Check Terminal 2
- ✅ Make sure you're using `http://localhost:8080` (NOT file://)

### Port already in use
```bash
# Check what's using port 5000
lsof -i :5000

# Check what's using port 8080
lsof -i :8080

# Kill the process if needed
kill <PID>
```

### Can't find Flask backend
- Check that `app.py` is in the project directory
- Check that `.env` file exists with `DATABASE_URL`
- Check Flask terminal for error messages

---

## ✅ Success Checklist

- [ ] Flask backend running (you see "Starting Flask server on port 5000...")
- [ ] Proxy server running (you see "Frontend proxy is running...")
- [ ] Browser shows `http://localhost:8080` in address bar
- [ ] No `file://` in the URL
- [ ] Can access login page
- [ ] Can sign up/sign in without errors

---

**Remember: Always use `http://localhost:8080` not `file://`!**

