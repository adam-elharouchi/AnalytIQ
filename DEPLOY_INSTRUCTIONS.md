# How to Deploy Changes to GitHub Pages

## Quick Steps to Update Your Published Site

### Step 1: Save All Files
Make sure all your files are saved in your editor (Cursor/VS Code).

### Step 2: Commit and Push Changes

Run these commands in your terminal:

```bash
# Navigate to your project directory
cd /Users/aelharouchi/Documents/GitHub/AnalytIQ

# Check what files have changed
git status

# Add all changes
git add .

# Commit the changes
git commit -m "Update code assistant UI and styling"

# Push to GitHub
git push origin main
```

### Step 3: Wait for GitHub Pages to Update

GitHub Pages usually updates within 1-2 minutes after you push. However, sometimes it can take up to 10 minutes.

### Step 4: Clear Browser Cache

If changes don't appear after pushing:

1. **Hard refresh your browser:**
   - Chrome/Edge: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
   - Firefox: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
   - Safari: `Cmd+Option+R`

2. **Or clear cache:**
   - Open browser settings
   - Clear browsing data/cache
   - Reload the GitHub Pages site

### Step 5: Verify GitHub Pages is Enabled

1. Go to: https://github.com/adamelharouchi5-blip/AnalytIQ/settings/pages
2. Make sure:
   - Source is set to `main` branch
   - Folder is set to `/ (root)`
   - It shows "Your site is live at https://adamelharouchi5-blip.github.io/AnalytIQ/"

### Troubleshooting

**If changes still don't appear:**

1. **Check if files were actually committed:**
   ```bash
   git log --oneline -3
   ```
   You should see your latest commit.

2. **Force a GitHub Pages rebuild:**
   - Go to: https://github.com/adamelharouchi5-blip/AnalytIQ/settings/pages
   - Click "Save" (even if nothing changed) - this triggers a rebuild

3. **Check the Actions tab:**
   - Go to: https://github.com/adamelharouchi5-blip/AnalytIQ/actions
   - Look for any failed deployments

4. **Verify the files on GitHub:**
   - Go to: https://github.com/adamelharouchi5-blip/AnalytIQ
   - Check if your latest changes are in the files (especially `css/styles.css` and `code-assistant.html`)

## Your GitHub Pages URL

Your site should be live at:
**https://adamelharouchi5-blip.github.io/AnalytIQ/**

## Note About Code Assistant Behavior

If the code assistant behaves differently on GitHub Pages vs locally, it might be because:

1. **API Keys:** The GitHub Pages version can't access your local API keys stored in localStorage
2. **CORS Issues:** Some APIs might have CORS restrictions
3. **Browser Differences:** Different browsers or browser settings

Make sure users know they need to configure their API keys in the GitHub Pages version too!

