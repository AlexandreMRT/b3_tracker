# Google OAuth 403 Error Troubleshooting

You're getting a 403 error from Google OAuth. This means Google is rejecting the authentication request.

## Verified Configuration

✅ **Redirect URI in code**: `http://localhost:8000/auth/callback`  
✅ **Client ID**: `527179835320-e9ekfegmk1er004vl47tq33lb82vep9o.apps.googleusercontent.com`  
✅ **Application is correctly sending the request to Google**

## Common Causes of 403 Error

### 1. OAuth App in Testing Mode (MOST COMMON)

If your OAuth app is in "Testing" mode, you MUST add your email to test users:

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Check the "Publishing status"
3. If it says **"Testing"**, scroll down to "Test users"
4. Click "ADD USERS"
5. Add your Google account email address
6. Click "SAVE"

### 2. Authorized Redirect URIs Not Saved

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click on your OAuth 2.0 Client ID: `527179835320-e9ekfegmk1er004vl47tq33lb82vep9o`
3. Under "Authorized redirect URIs", verify you have:
   ```
   http://localhost:8000/auth/callback
   ```
4. Click "SAVE" at the bottom
5. **Wait 5-10 minutes** for Google to propagate the changes

### 3. OAuth Consent Screen Not Configured

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Fill in required fields:
   - App name
   - User support email
   - Developer contact email
3. Add scopes: `openid`, `email`, `profile`
4. Save and continue

### 4. Wrong Google Cloud Project

Make sure you're looking at the correct project in Google Cloud Console. The project should contain the client ID starting with `527179835320-`.

## Testing Steps

After making changes:

1. **Clear your browser cookies** for localhost
2. **Wait 5-10 minutes** for Google to propagate changes
3. Try logging in again at: http://localhost:8000/login

## Alternative: Create New OAuth Credentials

If nothing works, create fresh credentials:

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click "CREATE CREDENTIALS" → "OAuth 2.0 Client ID"
3. Application type: "Web application"
4. Name: "B3 Tracker Local Dev"
5. Authorized redirect URIs: `http://localhost:8000/auth/callback`
6. Click "CREATE"
7. Copy the new Client ID and Client Secret
8. Update your `.env` file with the new credentials
9. Restart the API: `docker compose restart api`
