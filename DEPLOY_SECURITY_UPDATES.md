# Deploy Security Updates to EC2

## Quick Deploy Commands

```bash
# SSH into your EC2 instance
ssh ec2-user@your-instance-ip

# Navigate to project directory
cd /opt/ai-search

# Pull latest changes
git fetch origin
git checkout claude/evaluate-html-to-react-01D6i6R5AMZQrJChq2S5j3J1
git pull origin claude/evaluate-html-to-react-01D6i6R5AMZQrJChq2S5j3J1

# Update backend dependencies
source venv/bin/activate
pip install -r requirements.txt

# Update frontend dependencies
cd frontend
npm install

# Rebuild frontend
npm run build

# Update environment variables (CRITICAL!)
cd /opt/ai-search
nano .env
# Add the new environment variables (see below)

# Restart services
pm2 restart all

# Verify services are running
pm2 status
pm2 logs --lines 50
```

---

## Detailed Step-by-Step Guide

### 1. SSH into EC2 Instance

```bash
ssh ec2-user@your-ec2-instance-ip
# Or if using key file:
ssh -i your-key.pem ec2-user@your-ec2-instance-ip
```

### 2. Pull Latest Code

```bash
cd /opt/ai-search

# Check current branch
git branch

# Fetch latest changes
git fetch origin

# Checkout and pull the security updates branch
git checkout claude/evaluate-html-to-react-01D6i6R5AMZQrJChq2S5j3J1
git pull origin claude/evaluate-html-to-react-01D6i6R5AMZQrJChq2S5j3J1
```

### 3. Update Backend Dependencies

The security updates added **slowapi** for rate limiting.

```bash
cd /opt/ai-search

# Activate virtual environment
source venv/bin/activate

# Install new dependencies
pip install -r requirements.txt

# Verify slowapi was installed
pip list | grep slowapi
# Should show: slowapi==0.1.9
```

### 4. Update Frontend Dependencies

The security updates added **dompurify** for XSS protection.

```bash
cd /opt/ai-search/frontend

# Install new dependencies
npm install

# Verify dompurify was installed
npm list | grep dompurify
# Should show: dompurify@3.0.8 and isomorphic-dompurify@2.9.0
```

### 5. Rebuild Frontend

```bash
cd /opt/ai-search/frontend

# Build production bundle
npm run build

# Verify build completed
ls -la dist/
```

### 6. **CRITICAL: Update Environment Variables**

You **must** add these new environment variables to your `.env` file:

```bash
cd /opt/ai-search
nano .env
```

**Add these new variables:**

```bash
# CORS Configuration (REQUIRED!)
# Replace with your actual domain
CORS_ORIGINS=https://pivotalbiovpai.com,https://www.pivotalbiovpai.com
CORS_ALLOW_CREDENTIALS=true

# Security Configuration (REQUIRED!)
ENVIRONMENT=production

# SECRET_KEY (CRITICAL - Generate a new one!)
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=YOUR_GENERATED_SECRET_KEY_HERE

# Rate Limiting (Optional - adjust based on your needs)
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_SEARCH=20/minute
RATE_LIMIT_UPLOAD=10/minute
RATE_LIMIT_AUTH=5/minute
```

**To generate a secure SECRET_KEY:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy the output and paste it as SECRET_KEY value
```

**Important Notes:**
- **CORS_ORIGINS**: Replace with your actual domain(s), comma-separated
- **SECRET_KEY**: Must be set or the app won't start in production!
- **ENVIRONMENT**: Must be set to `production` for production deployment
- Keep existing variables (OPENAI_API_KEY, etc.) unchanged

### 7. Restart Services

```bash
# Restart all PM2 processes
pm2 restart all

# Or restart individually:
pm2 restart ai-search-backend
pm2 restart ai-search-worker
pm2 restart ai-search-frontend
```

### 8. Verify Deployment

```bash
# Check PM2 status
pm2 status

# Check logs for errors
pm2 logs ai-search-backend --lines 50
pm2 logs ai-search-frontend --lines 50

# Look for these success messages in backend logs:
# "Rate limiting enabled: 60/minute"
# "CORS enabled for origins: ['https://yourdomain.com']"
```

### 9. Test the Application

**Open your browser and test:**

1. **Visit your site**: https://pivotalbiovpai.com
2. **Test login**: Verify authentication works
3. **Test file upload**: Upload a small test file
4. **Test AI search**: Run a search query
5. **Check browser console**: Look for any errors

**Test rate limiting (optional):**

```bash
# From your local machine, test rate limiting
for i in {1..10}; do
  curl -X POST https://pivotalbiovpai.com/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"wrong"}'
  sleep 0.5
done
# Should see "429 Too Many Requests" after 5 attempts
```

---

## Troubleshooting

### If Backend Won't Start

**Check logs:**
```bash
pm2 logs ai-search-backend --err --lines 100
```

**Common issues:**

1. **Missing SECRET_KEY:**
   ```
   ValueError: SECRET_KEY must be set in production!
   ```
   **Solution**: Add SECRET_KEY to `.env` file

2. **Invalid CORS configuration:**
   ```
   ValueError: CORS_ORIGINS cannot contain '*' in production!
   ```
   **Solution**: Set specific domains in CORS_ORIGINS

3. **Missing slowapi:**
   ```
   ModuleNotFoundError: No module named 'slowapi'
   ```
   **Solution**: `pip install -r requirements.txt`

### If Frontend Shows Errors

**Check browser console for:**

1. **DOMPurify errors:**
   - Clear browser cache
   - Ensure `npm install` ran successfully
   - Check `npm list | grep dompurify`

2. **CORS errors:**
   - Verify CORS_ORIGINS in `.env` matches your domain exactly
   - Check backend logs for "CORS enabled for origins"
   - Restart backend: `pm2 restart ai-search-backend`

### If Rate Limiting Too Strict

**Adjust limits in `.env`:**

```bash
# Example for higher limits
RATE_LIMIT_SEARCH=50/minute
RATE_LIMIT_UPLOAD=20/minute
```

Then restart: `pm2 restart ai-search-backend`

### View Current Configuration

```bash
# Check environment variables
cat /opt/ai-search/.env

# Check what's running
pm2 status
pm2 describe ai-search-backend

# Check disk space
df -h
```

---

## Rollback Plan (If Something Goes Wrong)

If you encounter critical issues:

```bash
# Stop services
pm2 stop all

# Rollback to previous commit
cd /opt/ai-search
git checkout <previous-commit-hash>

# Example: git checkout 0c82812

# Reinstall old dependencies
source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build

# Restart services
pm2 restart all
```

---

## Post-Deployment Checklist

- [ ] Backend started successfully
- [ ] Frontend accessible via browser
- [ ] Login/authentication works
- [ ] File upload works
- [ ] AI search works
- [ ] No errors in PM2 logs
- [ ] No errors in browser console
- [ ] Rate limiting tested (optional)
- [ ] CORS working (no CORS errors in browser)

---

## Security Validation

After deployment, verify security improvements:

```bash
# Check security headers
curl -I https://pivotalbiovpai.com

# Should see:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000; includeSubDomains
```

---

## Need Help?

- **Check logs**: `pm2 logs --lines 100`
- **Check status**: `pm2 status`
- **View process info**: `pm2 describe ai-search-backend`
- **Review**: SECURITY.md for detailed security documentation
- **Backend port**: Should be running on port 8000
- **Frontend**: Should serve on configured port (likely 5173 or 3000)

---

**Deployment Date**: Run `date` to record when deployed
**Branch**: `claude/evaluate-html-to-react-01D6i6R5AMZQrJChq2S5j3J1`
**Commit**: `1e4338f - Implement comprehensive security improvements`
