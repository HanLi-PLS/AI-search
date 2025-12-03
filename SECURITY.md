# Security Documentation

This document outlines the security measures implemented in the AI Search application.

## 🔒 Security Features

### 1. CORS (Cross-Origin Resource Sharing) Protection

**Status**: ✅ Implemented

**Configuration**:
- Restricted to specific allowed origins (no wildcard `*` in production)
- Configurable via `CORS_ORIGINS` environment variable
- Explicit HTTP methods allowed: GET, POST, PUT, DELETE, OPTIONS
- Specific headers whitelisted
- Preflight request caching (1 hour)

**Production Setup**:
```bash
# Set in .env or environment
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=true
ENVIRONMENT=production
```

**Validation**:
- Application will refuse to start in production if `CORS_ORIGINS` contains `*`
- Logs all allowed origins on startup

---

### 2. Security Headers

**Status**: ✅ Implemented

**Headers Applied**:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: (production only)
```

**Content Security Policy** (Production):
```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval';
style-src 'self' 'unsafe-inline';
img-src 'self' data: https:;
font-src 'self' data:;
connect-src 'self' https:;
frame-ancestors 'none';
```

---

### 3. Rate Limiting

**Status**: ✅ Implemented

**Library**: slowapi

**Rate Limits**:
- **Default**: 60 requests/minute (general endpoints)
- **Search**: 20 requests/minute (AI-powered search)
- **Upload**: 10 requests/minute (file uploads)
- **Auth**: 5 requests/minute (login/register)

**Configuration**:
```bash
# Adjust in .env based on your needs
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_SEARCH=20/minute
RATE_LIMIT_UPLOAD=10/minute
RATE_LIMIT_AUTH=5/minute
```

**Protected Endpoints**:
- `/api/search` - AI document search
- `/api/upload` - File uploads
- `/api/auth/login` - Authentication
- `/api/auth/register` - User registration

**Response**: HTTP 429 (Too Many Requests) when limit exceeded

---

### 4. XSS (Cross-Site Scripting) Protection

**Status**: ✅ Implemented

**Frontend Protection**:
- **DOMPurify**: All markdown-to-HTML conversions sanitized
- **Allowed Tags**: Whitelist of safe HTML tags only
- **Attribute Filtering**: Only safe attributes (href, target, rel, class)
- **No Data Attributes**: `ALLOW_DATA_ATTR: false`

**Backend Protection**:
- Input validation on all endpoints
- SQL injection prevention via SQLAlchemy ORM
- Parameterized queries

**Sanitized Components**:
- AI search results (markdown answers)
- Stock data news/analysis
- User-generated content

---

### 5. Authentication & Authorization

**Status**: ✅ Implemented

**Features**:
- JWT (JSON Web Tokens) for authentication
- Secure password hashing (bcrypt)
- Token expiration (configurable, default 30 minutes)
- Admin approval workflow for new users
- Role-based access control (admin/user)

**Security Measures**:
- Passwords hashed with bcrypt (cost factor 12)
- JWT tokens signed with secret key
- Rate-limited login attempts (5/minute)
- Password reset with secure tokens
- Email enumeration prevention

**SECRET_KEY Requirements**:
```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set in environment
SECRET_KEY=your-generated-secure-key-here
```

**Production Validation**:
- Application refuses to start if `SECRET_KEY` is not set or is default value
- Warning logged if using development secret key

---

### 6. File Upload Security

**Status**: ✅ Implemented

**Protections**:
- File type validation (whitelist of allowed extensions)
- File size limits (default 100MB, configurable)
- Automatic filtering of system/temporary files
- Sanitized filenames (path traversal prevention)
- Virus scanning (recommended via external service)

**Filtered Files**:
- Hidden files (starting with `.`)
- Microsoft Office temp files (`~$`)
- macOS metadata (`__MACOSX`, `.DS_Store`)
- ZIP bomb protection (max depth, size limits)

**Configuration**:
```bash
MAX_FILE_SIZE_MB=100
```

---

### 7. Database Security

**Status**: ✅ Implemented

**Measures**:
- SQLAlchemy ORM prevents SQL injection
- Prepared statements for all queries
- User passwords hashed, never stored in plaintext
- Database credentials in environment variables
- Connection pooling with limits

---

### 8. Secrets Management

**Status**: ✅ Implemented

**Options**:

**Option 1: Environment Variables**
```bash
OPENAI_API_KEY=sk-...
FINNHUB_API_KEY=...
TUSHARE_API_TOKEN=...
```

**Option 2: AWS Secrets Manager** (Recommended for Production)
```bash
USE_AWS_SECRETS=true
AWS_SECRET_NAME_OPENAI=openai-api-key
AWS_SECRET_NAME_FINNHUB=finnhub-api-key
AWS_SECRET_NAME_TUSHARE=tushare-api-token
AWS_REGION=us-west-2
```

**Best Practices**:
- Never commit `.env` files to git
- Use AWS Secrets Manager in production
- Rotate API keys regularly
- Separate dev/staging/prod secrets

---

## 🚨 Known Security Considerations

### 1. Password Reset (TODO)
- Password reset tokens generated but email not sent
- TODO: Implement email service with SendGrid/AWS SES
- Tokens expire after 1 hour

### 2. Email Validation
- Email validator library used
- No email confirmation flow (relies on admin approval)

### 3. Session Management
- JWT tokens stored in HTTP-only cookies (recommended)
- No refresh token rotation yet
- Consider implementing refresh token flow

### 4. API Key Exposure
- API keys in environment variables
- Logged during startup (INFO level) - consider reducing verbosity
- Ensure logs are secured in production

### 5. File Storage
- Uploaded files stored locally or S3
- Consider implementing file encryption at rest
- Implement retention policy for uploaded files

---

## 📋 Security Checklist for Production

### Critical (Must Do)
- [ ] Generate and set secure `SECRET_KEY`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `CORS_ORIGINS` with specific domains
- [ ] Enable HTTPS/TLS (use Let's Encrypt)
- [ ] Set up firewall rules (allow only 80/443)
- [ ] Implement backup strategy
- [ ] Configure AWS Secrets Manager
- [ ] Review and adjust rate limits

### Recommended
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Enable access logging
- [ ] Implement email service for password reset
- [ ] Add CAPTCHA to registration/login
- [ ] Set up vulnerability scanning
- [ ] Implement refresh token rotation
- [ ] Enable audit logging for admin actions
- [ ] Set up automated security updates

### Optional
- [ ] Implement 2FA (Two-Factor Authentication)
- [ ] Add IP whitelisting for admin endpoints
- [ ] Implement file encryption at rest
- [ ] Add DDoS protection (CloudFlare, AWS Shield)
- [ ] Implement session replay protection
- [ ] Add request signing for API calls

---

## 🔍 Security Testing

### Manual Testing
```bash
# Test CORS
curl -H "Origin: https://malicious-site.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS http://localhost:8000/api/search

# Test rate limiting
for i in {1..30}; do
  curl -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"test"}'
done

# Test XSS
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"<script>alert(1)</script>"}'
```

### Automated Security Scanning
```bash
# Install OWASP ZAP
# Run vulnerability scan
zap-cli quick-scan http://localhost:8000

# Or use Bandit for Python security
pip install bandit
bandit -r backend/

# Or use npm audit for frontend
cd frontend && npm audit
```

---

## 📞 Security Incident Response

### If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email security contact immediately
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline:
- **24 hours**: Acknowledge receipt
- **72 hours**: Initial assessment
- **7 days**: Patch development
- **14 days**: Patch deployment

---

## 📚 Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [React Security Best Practices](https://snyk.io/blog/10-react-security-best-practices/)
- [DOMPurify Documentation](https://github.com/cure53/DOMPurify)
- [slowapi Rate Limiting](https://github.com/laurents/slowapi)

---

**Last Updated**: 2025-01-20
**Security Version**: 1.0.0
