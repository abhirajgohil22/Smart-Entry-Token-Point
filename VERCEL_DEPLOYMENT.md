# Smart Entry Token Point - Vercel Deployment Guide

## ✅ Pre-Deployment Checklist

- [ ] Neon PostgreSQL database created and connection string ready
- [ ] Cloudinary account set up with API credentials
- [ ] Gmail account with app password ready for email verification
- [ ] GitHub repository pushed with latest code
- [ ] Vercel account connected to GitHub

---

## Step 1: Prepare Neon Database

1. Go to [https://neon.tech](https://neon.tech) and create a free PostgreSQL database
2. Copy the connection string in the format: `postgresql://user:password@host/database?sslmode=require`
3. Keep this for later - you'll add it to Vercel environment variables

---

## Step 2: Deploy to Vercel

### Via Vercel CLI (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy from project directory
cd /workspaces/Smart-Entry-Token-Point
vercel
```

### Via Vercel Dashboard

1. Go to [https://vercel.com](https://vercel.com) and sign in
2. Click "Add New..." → "Project"
3. Import your GitHub repository
4. In "Build and Output Settings", leave as default
5. Click "Deploy"

---

## Step 3: Configure Environment Variables

In Vercel Project Settings → Environment Variables, add:

### Database
```
DATABASE_URL = postgresql://neondb_owner:npg_C9ZwMHvyVBJ1@ep-shy-meadow-a7o6hj2y-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

### Django Settings
```
DEBUG = False
SECRET_KEY = your-secret-key (generate a new one!)
ALLOWED_HOSTS = your-app.vercel.app
```

### Cloudinary
```
CLOUDINARY_CLOUD_NAME = your-cloud-name
CLOUDINARY_API_KEY = your-api-key
CLOUDINARY_API_SECRET = your-api-secret
```

### Gmail Email
```
EMAIL_BACKEND = django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST = smtp.gmail.com
EMAIL_PORT = 587
EMAIL_HOST_USER = your-email@gmail.com
EMAIL_HOST_PASSWORD = your-16-char-app-password
DEFAULT_FROM_EMAIL = your-email@gmail.com
EMAIL_USE_TLS = True
```

### Security Headers
```
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = HTTP_X_FORWARDED_PROTO,https
```

---

## Step 4: Generate Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Add this value to `SECRET_KEY` in Vercel environment variables.

---

## Step 5: Configure Vercel Build

The `vercel.json` file in the project root handles:
- Python 3.12 runtime
- Build command using `requirements-prod.txt`
- Static file collection
- Route configuration for Django

**Vercel.json Configuration:**
```json
{
  "buildCommand": "bash build.sh",
  "outputDirectory": "staticfiles",
  "framework": "django",
  "python": {
    "version": "3.12"
  }
}
```

---

## Step 6: First Deployment

1. After configuring environment variables, trigger a redeploy:
   - Go to Deployments → Latest deployment
   - Click "Redeploy"

2. Monitor build logs for errors
3. Check the Vercel URL once deployment completes

---

## Step 7: Run Migrations (One-time)

Option A: Via Vercel CLI
```bash
vercel env pull
python manage.py migrate
```

Option B: Manually via your database provider (Neon dashboard)
- Neon provides SQL execution capabilities
- Run migration scripts from Neon SQL editor

Option C: Uncomment in build.sh
```bash
# Open build.sh and uncomment the migration line
# python manage.py migrate --noinput
```

---

## Step 8: Create Admin User

### Option 1: Manual Creation (Recommended)
```bash
vercel env pull
python manage.py createsuperuser
```

### Option 2: Via Django Shell
```bash
vercel env pull
python manage.py shell
```

---

## Testing After Deployment

### 1. Check Health
```
https://your-app.vercel.app/health/
```

### 2. Access Admin
```
https://your-app.vercel.app/admin/
```

### 3. Test Registration
```
POST https://your-app.vercel.app/api/v1/auth/register/
```

### 4. Test Email
Register with a test email - you should receive OTP

---

## Troubleshooting

### Build Fails with "pg_config not found"
✅ **Fixed** - Using `psycopg` instead of `psycopg2-binary`

### Static Files Not Loading
```bash
# Rebuild and redeploy
vercel redeploy --prod
```

### Database Connection Error
1. Verify DATABASE_URL is set correctly in Vercel
2. Check Neon PostgreSQL connection string
3. Ensure IP whitelisting if needed

### Email Not Sending
1. Verify EMAIL_HOST_PASSWORD is the Gmail App Password (not regular password)
2. Check email configuration in environment variables
3. Verify the email account has "Less secure app access" enabled

### CSRF Token Error
1. Add your Vercel domain to CSRF_TRUSTED_ORIGINS
2. Redeploy after updating environment

---

## Monitoring & Logs

### View Logs
```bash
vercel logs --follow
```

### Monitor Performance
- Vercel Dashboard → Functions → Analytics
- Check function execution times
- Monitor database query times

### Common Issues
- **Database pool exhausted**: Increase pool size in Neon
- **Timeout errors**: Extend function timeout in `vercel.json`
- **Memory errors**: Reduce batch sizes in operations

---

## Domain Configuration (Optional)

1. Go to Vercel Project Settings → Domains
2. Add your custom domain
3. Update DNS records as shown by Vercel
4. Update ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS

---

## Performance Tips

1. **Database**: Use Neon's connection pooling
2. **Static Files**: Served with CDN caching (1 year)
3. **Media Files**: Cloudinary handles CDN distribution
4. **API**: Consider adding caching headers for GET requests

---

## Security Checklist

- [ ] DEBUG = False in production
- [ ] SECRET_KEY is unique and secure
- [ ] DATABASE_URL uses SSL mode
- [ ] Email credentials are app passwords (not main password)
- [ ] SECURE_SSL_REDIRECT = True
- [ ] SESSION_COOKIE_SECURE = True
- [ ] CORS origins are restricted to your domains

---

## Rollback Strategy

If deployment fails:

```bash
# View previous deployments
vercel deployments

# Promote a previous deployment
vercel promote <deployment-id>
```

---

## Next Steps

1. ✅ Deploy app to Vercel
2. ✅ Configure environment variables
3. ✅ Test all endpoints
4. ✅ Monitor logs for errors
5. Consider adding custom domain
6. Set up monitoring/alerts

**Need help?**
- Vercel Docs: https://vercel.com/docs
- Django Deployment: https://docs.djangoproject.com/en/4.2/howto/deployment/
- Neon Docs: https://neon.tech/docs
