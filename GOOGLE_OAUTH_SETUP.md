# 🔐 Google OAuth Setup Guide

Follow these steps to get your Google OAuth credentials:

## Step 1: Go to Google Cloud Console

Visit: https://console.cloud.google.com/

## Step 2: Create or Select a Project

1. Click on the project dropdown at the top
2. Click "New Project" or select an existing project
3. Give it a name like "B3 Tracker"

## Step 3: Enable Google+ API

1. Go to **APIs & Services** → **Library**
2. Search for "Google+ API" or "Google Identity"
3. Click **Enable**

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - **User Type**: External (for testing)
   - **App name**: B3 Tracker
   - **User support email**: Your email
   - **Developer contact**: Your email
   - Click **Save and Continue**
   - **Scopes**: You can skip this for now
   - **Test users**: Add your own email
   - Click **Save and Continue**

4. Back to **Create OAuth client ID**:
   - **Application type**: Web application
   - **Name**: B3 Tracker Web Client
   - **Authorized redirect URIs**: Click **+ Add URI**
     - Add: `http://localhost:8000/auth/callback`
     - (Optional) Add: `http://127.0.0.1:8000/auth/callback`
   - Click **Create**

## Step 5: Copy Your Credentials

You'll see a modal with:
- **Client ID**: Something like `xxxxx.apps.googleusercontent.com`
- **Client Secret**: Something like `GOCSPX-xxxxx`

## Step 6: Update Your .env File

Open `/home/alex/Documents/projects/b3_tracker/.env` and update:

```env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
```

## Step 7: Restart the API

```bash
cd /home/alex/Documents/projects/b3_tracker
docker compose restart api
```

## Step 8: Test the Login

Visit: http://localhost:8000/auth/login

You should be redirected to Google login, and after authentication, redirected back with a JWT token!

## Troubleshooting

### "Redirect URI mismatch"
- Make sure you added `http://localhost:8000/auth/callback` exactly
- Check that you're using `localhost` not `127.0.0.1` (or vice versa)

### "Access blocked: This app's request is invalid"
- Make sure you enabled the Google+ API
- Check that you configured the OAuth consent screen

### "This app isn't verified"
- This is normal for development
- Click "Advanced" → "Go to B3 Tracker (unsafe)"
- This won't appear once you add your email as a test user

---

**When you're done**, paste your credentials in the terminal or let me know and we'll test it together!
