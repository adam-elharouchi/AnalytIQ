# ✅ Production Setup - Ready to Go!

I've created automated setup scripts that will configure everything on your server.

## 🎯 What You Need to Do

### On Your Production Server:

```bash
# 1. Get the files on your server
git clone https://github.com/adamelharouchi5-blip/AnalytIQ.git
cd AnalytIQ

# 2. Set up your .env file
nano .env
# Add: DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/postgres

# 3. Run the automated setup (does everything!)
chmod +x setup_production.sh
sudo ./setup_production.sh
```

**That's it!** The script will:
- ✅ Install Nginx
- ✅ Install Python dependencies  
- ✅ Set up reverse proxy
- ✅ Create Flask service
- ✅ Start everything

---

## 📋 Quick Checklist

Before running the script, make sure:
- [ ] You have SSH access to your server
- [ ] You have sudo/root access
- [ ] Your domain (`www.myanalytiq.org`) points to your server IP
- [ ] You've uploaded the project files to the server
- [ ] You've created `.env` file with `DATABASE_URL`

---

## 🧪 After Setup - Test It

```bash
# Test Flask
curl http://127.0.0.1:5000/api/health

# Test Nginx
curl http://localhost/api/health

# Test production
curl http://www.myanalytiq.org/api/health
```

Then visit: **http://www.myanalytiq.org** and try to sign up/sign in!

---

## 📚 Documentation

- **`QUICK_START_SERVER.md`** - Quick reference guide
- **`PRODUCTION_SETUP.md`** - Detailed manual instructions
- **`setup_production.sh`** - Main automated setup script

---

## ⚡ Quick Commands Reference

```bash
# Check Flask service
sudo systemctl status analytiq-api

# Restart Flask
sudo systemctl restart analytiq-api

# View Flask logs
sudo journalctl -u analytiq-api -f

# Restart Nginx
sudo systemctl restart nginx
```

---

All files are committed and pushed to GitHub! Just run the setup script on your server. 🚀

