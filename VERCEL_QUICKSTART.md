# Vercel Deployment - Quick Start

## 🚀 What's Ready

Your Smart Entry Token Point app is now configured for Vercel deployment!

### Files Created/Updated

| File | Purpose |
|------|---------|
| `requirements-prod.txt` | Lightweight production dependencies |
| `vercel.json` | Vercel build & deployment configuration |
| `build.sh` | Build script for Vercel |
| `.env.vercel` | Environment template for Vercel |
| `VERCEL_DEPLOYMENT.md` | Complete deployment guide |

### Key Changes

✅ Replaced `psycopg2-binary` → `psycopg` (fixes build errors)  
✅ Updated `ALLOWED_HOSTS` for Vercel domains  
✅ Created production-only requirements file  
✅ Added Vercel-specific routing configuration  
✅ Configured for Django in serverless environment  

---

## ⚡ Quick Deployment (5 minutes)

### 1. Prepare Credentials
- Neon PostgreSQL connection string
- Cloudinary API credentials
- Gmail app password

### 2. Push to GitHub
```bash
git add .
git commit -m "Add Vercel deployment configuration"
git push origin main
```

### 3. Deploy via Vercel CLI
```bash
npm install -g vercel
vercel login
vercel
```

### 4. Add Environment Variables
In Vercel Project Settings → Environment Variables:

```
DATABASE_URL=postgresql://...
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
SECRET_KEY=your-generated-key
DEBUG=False
```

### 5. Redeploy
```bash
vercel redeploy --prod
```

---

## 🔍 Verify Deployment

```bash
# Test your app
curl https://your-app.vercel.app/health/

# Access admin panel
https://your-app.vercel.app/admin/

# Test registration API
curl -X POST https://your-app.vercel.app/api/v1/auth/register/ \
  -F "email=test@example.com" \
  -F "password=TestPassword123!" \
  -F "first_name=Test" \
  -F "live_photo=@image.jpg"
```

---

## 📋 Production Requirements File

The new `requirements-prod.txt` includes only essential packages:
- Django 4.2.4
- PostgreSQL driver (psycopg 3.1)
- REST Framework & JWT
- Cloudinary storage
- WhiteNoise for static files
- Gunicorn (optional, Vercel handles WSGI)

**Size Reduction:**
- Old: 178 packages (~500MB)
- New: ~25 packages (~50MB) ✅

---

## 🛠️ Build Configuration

### vercel.json
- Python 3.12 runtime
- Build command: `bash build.sh`
- Output directory: `staticfiles/`
- Routes configured for Django
- Function timeout: 60 seconds

### build.sh
```bash
pip install -r requirements-prod.txt
python manage.py collectstatic --noinput --clear
```

---

## 🔒 Security Defaults

Vercel environment automatically enables:
- `DEBUG = False`
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`

---

## 📚 Full Guide

See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) for:
- Step-by-step deployment instructions
- Environment variable setup
- Database migration guide
- Troubleshooting tips
- Custom domain configuration
- Performance optimization

---

## ✅ Deployment Checklist

- [ ] Neon PostgreSQL database created
- [ ] Cloudinary account with credentials
- [ ] Gmail app password generated
- [ ] GitHub repository with latest code
- [ ] Vercel account created
- [ ] GitHub connected to Vercel
- [ ] Environment variables configured
- [ ] Build and deployment successful
- [ ] Admin user created
- [ ] API endpoints tested
- [ ] Email verification working

---

## 🎯 Next Steps

1. **Immediate**: Push code and connect to Vercel
2. **Soon**: Create admin user and test endpoints
3. **Later**: Configure custom domain and monitoring

```bash
# Get started now
git push origin main
vercel
```

---

## 🆘 Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `pg_config not found` | ✅ Fixed - using psycopg |
| `ModuleNotFoundError` | Check requirements-prod.txt installed |
| `CSRF token missing` | Add domain to CSRF_TRUSTED_ORIGINS |
| `Static files 404` | Run `vercel redeploy --prod` |

---

**Ready to deploy? Follow [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)! 🚀**
