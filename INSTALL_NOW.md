# 🚀 Install Right Now - Copy & Paste

## Step 1: SSH into your server

```bash
ssh user@your-server-ip
```

## Step 2: Run these commands (copy all at once)

```bash
# Get the project
cd ~
git clone https://github.com/adamelharouchi5-blip/AnalytIQ.git || cd AnalytIQ && git pull
cd AnalytIQ

# Create .env file (edit with your database URL)
cat > .env << 'EOF'
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/postgres
FLASK_ENV=production
FLASK_DEBUG=False
EOF

# Edit .env with your actual database password
nano .env
# Press Ctrl+X, then Y, then Enter to save

# Run the setup (this does EVERYTHING)
chmod +x setup_production.sh
sudo ./setup_production.sh
```

**That's it!** The script handles everything automatically.

---

## What happens:

1. ✅ Installs Nginx
2. ✅ Installs Python packages
3. ✅ Sets up reverse proxy
4. ✅ Creates Flask service
5. ✅ Starts everything

---

## After setup completes:

Test it:
```bash
curl http://www.myanalytiq.org/api/health
```

Visit: **http://www.myanalytiq.org**

---

## Need to set up SSL?

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d www.myanalytiq.org -d myanalytiq.org
```

---

**All you need to do is:**
1. SSH into your server
2. Copy/paste the commands above
3. Done! 🎉

