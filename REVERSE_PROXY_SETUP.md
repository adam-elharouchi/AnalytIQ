# Reverse Proxy Setup Guide

## Overview
Since you're using relative URLs (`/api`), you need to set up a reverse proxy so that:
- Your frontend (static files) is served from `www.myanalytiq.org`
- Your backend API is accessible at `www.myanalytiq.org/api`

## Option 1: Nginx Reverse Proxy (Recommended)

### Step 1: Install Nginx
```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install nginx

# On macOS (with Homebrew)
brew install nginx
```

### Step 2: Configure Nginx

Create/edit `/etc/nginx/sites-available/myanalytiq` (or `/usr/local/etc/nginx/servers/myanalytiq` on macOS):

```nginx
server {
    listen 80;
    server_name www.myanalytiq.org myanalytiq.org;

    # Serve static files (frontend)
    location / {
        root /path/to/your/AnalytIQ;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to Flask backend
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers (if needed)
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
        
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
}
```

### Step 3: Enable the Site
```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/myanalytiq /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
# or on macOS
sudo nginx -s reload
```

### Step 4: Update Flask App
Make sure your Flask app runs on `127.0.0.1:5000` (which it already does based on your changes).

## Option 2: Apache Reverse Proxy

### Step 1: Enable Required Modules
```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod rewrite
```

### Step 2: Configure Apache

Create/edit `/etc/apache2/sites-available/myanalytiq.conf`:

```apache
<VirtualHost *:80>
    ServerName www.myanalytiq.org
    ServerAlias myanalytiq.org

    # Serve static files
    DocumentRoot /path/to/your/AnalytIQ
    
    <Directory /path/to/your/AnalytIQ>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    # Proxy API requests
    ProxyPreserveHost On
    ProxyPass /api http://127.0.0.1:5000/api
    ProxyPassReverse /api http://127.0.0.1:5000/api
</VirtualHost>
```

### Step 3: Enable the Site
```bash
sudo a2ensite myanalytiq.conf
sudo systemctl reload apache2
```

## Option 3: Using a Process Manager (PM2/systemd)

### With systemd (Linux)

Create `/etc/systemd/system/analytiq-api.service`:

```ini
[Unit]
Description=AnalytIQ Flask API
After=network.target

[Service]
User=your-username
WorkingDirectory=/path/to/your/AnalytIQ
Environment="PATH=/path/to/your/venv/bin"
ExecStart=/path/to/your/venv/bin/python app.py

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable analytiq-api
sudo systemctl start analytiq-api
```

### With PM2 (Node.js process manager)

```bash
# Install PM2
npm install -g pm2

# Start Flask app with PM2
pm2 start app.py --interpreter python3 --name analytiq-api

# Save PM2 configuration
pm2 save
pm2 startup
```

## Option 4: Cloudflare Workers / Cloudflare Pages Functions

If you're using Cloudflare:
1. Deploy your static files to Cloudflare Pages
2. Use Cloudflare Workers to proxy `/api` requests to your backend
3. Set up a Worker script to forward requests

## Testing

After setup, test that:
1. Frontend loads: `https://www.myanalytiq.org`
2. API is accessible: `https://www.myanalytiq.org/api/users/signup` (should return JSON, not 404)
3. CORS works: Check browser console for no CORS errors

## Important Notes

1. **HTTPS**: Set up SSL certificates (Let's Encrypt is free) for production
2. **Security**: Make sure your Flask app only listens on `127.0.0.1` (localhost) so it's not directly accessible from the internet
3. **Environment Variables**: Make sure your `.env` file with `DATABASE_URL` is accessible to the Flask process
4. **Port**: Your Flask app is configured to run on port 5000, which matches the proxy configuration above

## Quick Test

Once set up, you can test the API endpoint:
```bash
curl https://www.myanalytiq.org/api/users/signup
```

Should return a JSON response (likely an error about missing data, but that confirms the proxy is working).

