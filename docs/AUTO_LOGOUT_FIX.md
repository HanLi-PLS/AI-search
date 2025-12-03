# Auto-Logout Issue - Root Cause and Fix

## Problem Summary
All users are automatically logged out every time the backend restarts (via `pm2 restart all`).

## Root Cause
**SECRET_KEY is not set in environment variables**, causing the following sequence:

1. When backend starts, `backend/app/config.py` checks for `SECRET_KEY` environment variable
2. If `SECRET_KEY` is not set, a **NEW random key is generated** (lines 154-160):
   ```python
   if not self.SECRET_KEY:
       import secrets
       self.SECRET_KEY = secrets.token_urlsafe(32)  # NEW random key each restart
   ```
3. All JWT authentication tokens were signed with the **OLD key**
4. Backend now uses the **NEW key** to verify tokens
5. All existing tokens become invalid → **All users logged out**

## How to Verify the Issue

Check your EC2 instance backend logs after restart:
```bash
pm2 logs ai-search-backend | grep "SECRET_KEY"
```

You should see a warning:
```
SECRET_KEY not set. Generated temporary key for development.
Set SECRET_KEY environment variable for production!
```

## Solution: Set a Persistent SECRET_KEY

### Step 1: Generate a secure SECRET_KEY
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

This will output something like:
```
XyZ123abcDEF456-GhiJKL789mnoPQRst_uvwXyz
```

### Step 2: Add SECRET_KEY to .env file on EC2
```bash
cd /opt/ai-search
nano .env
```

Add this line (replace with your generated key):
```
SECRET_KEY=XyZ123abcDEF456-GhiJKL789mnoPQRst_uvwXyz
```

### Step 3: Restart backend
```bash
pm2 restart ai-search-backend
```

### Step 4: Verify the fix
```bash
pm2 logs ai-search-backend | grep "SECRET_KEY"
```

You should **NOT** see the warning about generating a temporary key.

## Result
✅ Users will stay logged in across backend restarts
✅ JWT tokens remain valid after `pm2 restart all`
✅ Sessions persist with the same SECRET_KEY

## Why This Happens

JWT tokens are cryptographically signed using the SECRET_KEY. When you restart the backend:
- **Without persistent SECRET_KEY**: New random key → All old tokens invalid → All users logged out
- **With persistent SECRET_KEY**: Same key used → Tokens remain valid → Users stay logged in

## Additional Notes

- This is NOT related to EC2 resources (memory: 12Gi available, disk: 30G available - both healthy)
- This is NOT related to the recent code changes (only added API parameters)
- This is a configuration issue that affects any JWT-based authentication system
- The same issue would occur even without any code changes if you restart the backend

## Security Best Practice

In production, you should:
1. Set SECRET_KEY in environment variables (not hardcoded)
2. Use a strong, randomly generated key (at least 32 characters)
3. Never commit SECRET_KEY to git
4. Rotate SECRET_KEY periodically (will log out all users, so plan accordingly)
