# Backend API Setup

This application now uses a PostgreSQL database (Supabase) for user management instead of localStorage.

## Setup Instructions

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Configure Environment

Make sure your `.env` file contains:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.omjttmkczfpnwyzrdzqi.supabase.co:5432/postgres
```

### 3. Create Database Tables

```bash
python3 create_tables.py
```

This will create the necessary tables:
- `users` - User accounts
- `user_profiles` - User profile information
- `user_settings` - User preferences

### 4. Start the Backend Server

```bash
python3 app.py
```

The API will run on `http://localhost:5000`

## API Endpoints

- `POST /api/users/signup` - Sign up a new user
- `POST /api/users/signin` - Sign in a user
- `GET /api/users/profile?user_id=...` - Get user profile
- `PUT /api/users/profile` - Update user profile
- `GET /api/users/settings?user_id=...` - Get user settings
- `PUT /api/users/settings` - Update user settings
- `PUT /api/users/password` - Update user password
- `DELETE /api/users/delete?user_id=...` - Delete user account
- `GET /api/health` - Health check

## Migration from localStorage

If you have existing users in localStorage, follow these steps:

### Option 1: Using the Export Tool (Recommended)

1. Open `export_users.html` in your browser
2. Click **"Export Users to CSV"** button to download `users_export.csv`
3. Run the migration:
   ```bash
   python3 migrate_users.py users_export.csv
   ```

### Option 2: Using Browser Console

1. Open your browser's Developer Console (F12)
2. Copy and paste the contents of `export_script.js`
3. Copy the CSV output from the console
4. Save it as `users_export.csv` in the project directory
5. Run the migration:
   ```bash
   python3 migrate_users.py users_export.csv
   ```

### Option 3: JSON Format (also supported)

If you prefer JSON:
1. Use `export_users.html` and click "Export All User Data"
2. Download as `users_export.json`
3. Run: `python3 migrate_users.py users_export.json`

### Option 4: Interactive Mode

```bash
python3 migrate_users.py
```

This will prompt you to paste the JSON data directly.

## Frontend Configuration

The frontend JavaScript files (`js/auth.js` and `js/profile.js`) are configured to use the API at `http://localhost:5000/api`.

**Important**: Make sure the backend server is running before using the application, or users will see connection errors.

## Production Deployment

For production:
1. Update `API_BASE_URL` in `js/auth.js` and `js/profile.js` to point to your production API URL
2. Deploy the Flask app (e.g., Heroku, Railway, Render, etc.)
3. Ensure CORS is configured to allow requests from your frontend domain

