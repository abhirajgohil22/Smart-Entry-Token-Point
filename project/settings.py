"""
Django settings for Smart Campus Token Management System.

This module configures Django with feature flags for optional components
like face recognition, ensuring the system can operate normally even when
optional libraries are not installed.
"""

import os
import logging
from pathlib import Path
from decouple import config, Csv
import dj_database_url

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# Default to True in local development so the app works immediately with the bundled templates.
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,0.0.0.0,testserver,.app.github.dev,*.app.github.dev,*.vercel.app,vercel.app',
    cast=Csv(),
)

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://*.app.github.dev,https://*.vercel.app,http://localhost:8000,http://127.0.0.1:8000',
    cast=Csv(),
)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# ============================================================================
# FEATURE FLAGS - Optional Components
# ============================================================================

# Face Recognition Feature Gate
# When False, the system operates normally without any ML library dependencies
FACE_RECOGNITION_ENABLED = config('FACE_RECOGNITION_ENABLED', default=False, cast=bool)

# Liveness Detection (only relevant if FACE_RECOGNITION_ENABLED=True)
LIVENESS_ENABLED = config('LIVENESS_ENABLED', default=False, cast=bool)

# Face Recognition Backend selection
FACE_RECOGNITION_BACKEND = config('FACE_RECOGNITION_BACKEND', default='dlib')

# ============================================================================
# Application definition
# ============================================================================

# Determine if Cloudinary should be used (only if credentials are provided)
CLOUDINARY_CLOUD_NAME = config('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = config('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = config('CLOUDINARY_API_SECRET', default='')
USE_CLOUDINARY = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
]

# Add Cloudinary only if credentials are available
if USE_CLOUDINARY:
    INSTALLED_APPS.extend(['cloudinary', 'cloudinary_storage'])

INSTALLED_APPS.extend([
    # Local apps
    'apps.authentication',
    'apps.tokens',
    'apps.security_photos',
    'apps.facerecognition',
    'apps.profile',
    'apps.notifications',
])

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

# ============================================================================
# Database Configuration
# ============================================================================

# Support PostgreSQL (production) or SQLite (development)
DEFAULT_DATABASE_URL = f'sqlite:///{BASE_DIR / "db.sqlite3"}'
DATABASES = {
    'default': {
        **dj_database_url.config(
            default=DEFAULT_DATABASE_URL,
            conn_max_age=600,
        ),
        'ATOMIC_REQUESTS': False,
    }
}

# ============================================================================
# Password validation
# ============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================================================
# Internationalization
# ============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ============================================================================
# Static files (CSS, JavaScript, Images)
# ============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================================
# Cloudinary Configuration - Image Storage
# ============================================================================

if USE_CLOUDINARY:
    import cloudinary
    
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )
    
    # Configure Cloudinary storage for django-cloudinary-storage
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY': CLOUDINARY_API_KEY,
        'API_SECRET': CLOUDINARY_API_SECRET,
    }
    
    # Use Cloudinary for media file storage
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
else:
    # Fall back to local storage if Cloudinary credentials not provided
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================================
# Django REST Framework Configuration
# ============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
}

# ============================================================================
# JWT Configuration
# ============================================================================

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JTI_CLAIM': 'jti',
    'TOKEN_TYPE_CLAIM': 'token_type',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ============================================================================
# CORS Configuration
# ============================================================================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='https://*.app.github.dev,http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000,https://*.vercel.app',
    cast=Csv()
)

CORS_ALLOW_CREDENTIALS = True

# ============================================================================
# Cache Configuration (Redis)
# ============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
        }
    }
}

# Fallback to local memory cache if Redis unavailable
try:
    import django_redis
except ImportError:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# ============================================================================
# AWS / S3 Configuration
# ============================================================================

AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='minioadmin')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='minioadmin')
AWS_S3_BUCKET = config('AWS_S3_BUCKET', default='campus-photos-dev')
AWS_S3_REGION = config('AWS_S3_REGION', default='us-east-1')
AWS_S3_ENDPOINT = config('AWS_S3_ENDPOINT', default='http://localhost:9000')
AWS_KMS_MASTER_KEY_ID = config('AWS_KMS_MASTER_KEY_ID', default='dev-key-id')

# For development with MinIO (S3-compatible)
if DEBUG and 'localhost' in AWS_S3_ENDPOINT or '127.0.0.1' in AWS_S3_ENDPOINT:
    AWS_S3_ADDRESSING_STYLE = 'virtual'
    AWS_S3_SIGNATURE_VERSION = 's3v4'

# ============================================================================
# Email Configuration
# ============================================================================

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='your-gmail-address@gmail.com')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='your-gmail-address@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)

SENDGRID_API_KEY = config('SENDGRID_API_KEY', default='')
if EMAIL_BACKEND == 'anymail.backends.sendgrid.EmailBackend':
    ANYMAIL = {
        'SENDGRID_API_KEY': SENDGRID_API_KEY,
    }

# ============================================================================
# Logging Configuration
# ============================================================================

LOG_LEVEL = config('LOG_LEVEL', default='INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {name} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}

# ============================================================================
# Security Settings
# ============================================================================

SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# Security headers
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "'unsafe-inline'"),  # Relax in dev, tighten in prod
    'style-src': ("'self'", "'unsafe-inline'"),
    'img-src': ("'self'", 'data:', 'https:'),
    'font-src': ("'self'",),
    'connect-src': ("'self'", 'http://localhost:8000', 'http://localhost:3000'),
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# App-Specific Settings
# ============================================================================

# Nonce expiration time (seconds)
NONCE_EXPIRATION_TIME = 300  # 5 minutes

# Photo constraints
PHOTO_MAX_SIZE_MB = 5  # 5MB maximum
PHOTO_MIN_SIZE_KB = 100  # 100KB minimum
PHOTO_ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png']
PHOTO_ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png']

# Token constraints
TOKEN_VALIDITY_HOURS_DEFAULT = 24
TOKEN_VALIDITY_HOURS_MIN = 1
TOKEN_VALIDITY_HOURS_MAX = 72

# Rate limiting
RATE_LIMIT_PHOTO_CAPTURE = '10/hour'
RATE_LIMIT_LOGIN = '10/15m'
RATE_LIMIT_TOKEN_GENERATION = '10/hour'
RATE_LIMIT_REGISTRATION = '5/hour'

# ============================================================================
# Optional Component Status Logging
# ============================================================================

logger = logging.getLogger(__name__)

if __name__ != '__main__':
    # Log feature flag status at startup
    logger.info(f"FACE_RECOGNITION_ENABLED: {FACE_RECOGNITION_ENABLED}")
    if FACE_RECOGNITION_ENABLED:
        logger.info(f"FACE_RECOGNITION_BACKEND: {FACE_RECOGNITION_BACKEND}")
        logger.info(f"LIVENESS_ENABLED: {LIVENESS_ENABLED}")
    else:
        logger.info("Face recognition feature disabled - system will operate with single-factor photo verification")
