# Phase 1 Installation & Setup Guide

## Overview

Phase 1 establishes the Django foundation for the Smart Campus Token Management System with:
- Django REST Framework and JWT authentication
- PostgreSQL database support (with SQLite fallback for development)
- Feature flags for optional face recognition
- Strict service boundary for face recognition modules
- Complete graceful degradation when ML libraries are unavailable

## Prerequisites

- Python 3.10+
- PostgreSQL 14+ (for production) or SQLite (for development)
- Redis (optional, for caching)

## Installation Steps

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/abhirajgohil22/Smart-Entry-Token-Point.git
cd Smart-Entry-Token-Point

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Copy environment file
cp .env.example .env
```

### 2. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# For development with additional tools
pip install -r requirements-dev.txt  # (when created)
```

### 3. Configure Django Settings

Edit `.env` to configure your environment:

```bash
# Database Configuration
# For PostgreSQL:
DATABASE_URL=postgresql://user:password@localhost:5432/campus_tokens

# For SQLite (default, development):
DATABASE_URL=sqlite:///db.sqlite3

# Feature Flags
FACE_RECOGNITION_ENABLED=False  # Set to True to enable face recognition
LIVENESS_ENABLED=False          # Only relevant if FACE_RECOGNITION_ENABLED=True

# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
```

### 4. Initialize Database

```bash
# Run migrations to create database schema
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser
```

### 5. Verify Installation

```bash
# Check Django configuration
python manage.py check

# Run health check
curl http://localhost:8000/health/check/

# Expected response:
# {"status": "healthy", "database": "connected"}
```

## Running the Application

### Development Server

```bash
# Start Django development server
python manage.py runserver

# Server runs on http://localhost:8000
```

### Docker Compose (Recommended)

```bash
# Start all services (Django, PostgreSQL, Redis, MinIO)
docker-compose up

# Stop services
docker-compose down

# View logs
docker-compose logs -f django
```

### Using Makefile

```bash
# View all available commands
make help

# Install dependencies
make install

# Set up development environment
make dev-setup

# Run development server
make dev

# Run with Docker
make docker-dev
```

## Testing

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Or using make
make test
```

### Test Face Recognition Integration

```bash
# Run only face recognition tests
pytest apps/facerecognition/tests.py -v

# Or using make
make test-face
```

### Key Test Scenarios

The test suite verifies:

1. **Django Boots Cleanly** - Django initializes successfully even without face recognition libraries
2. **Feature Flag Behavior** - When `FACE_RECOGNITION_ENABLED=False`, system uses disabled backend
3. **Graceful Degradation** - When face_recognition library is missing, system falls back gracefully
4. **Service Factory** - Appropriate backend is selected based on settings
5. **Backend Implementations** - Each backend correctly implements the strategy interface

### Expected Test Output

```
apps/facerecognition/tests.py::DisabledBackendTests::test_backend_name PASSED
apps/facerecognition/tests.py::DisabledBackendTests::test_detect_face_returns_not_enabled PASSED
apps/facerecognition/tests.py::DlibBackendTests::test_backend_name PASSED
apps/facerecognition/tests.py::DjangoBootstrapTests::test_django_boots_without_face_recognition_library PASSED
apps/facerecognition/tests.py::DjangoBootstrapTests::test_facerecognition_app_no_import_on_startup PASSED

======================== 20 passed in 0.42s ========================
```

## Project Structure

```
Smart-Entry-Token-Point/
├── project/                      # Django project settings
│   ├── settings.py              # Main Django settings
│   ├── urls.py                  # URL routing
│   ├── wsgi.py                  # WSGI application
│   └── __init__.py
│
├── apps/                        # Django applications
│   ├── core/                    # Core utilities and exceptions
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py             # Health check endpoint
│   │   ├── exceptions.py        # Custom exception handlers
│   │   ├── urls.py
│   │   └── __init__.py
│   │
│   ├── authentication/          # User authentication
│   │   ├── apps.py
│   │   ├── models.py            # User, DeviceFingerprint, RefreshToken (Phase 1)
│   │   ├── urls.py
│   │   └── __init__.py
│   │
│   ├── tokens/                  # Campus token generation
│   │   ├── apps.py
│   │   ├── models.py            # CampusToken, TokenHistory (Phase 1)
│   │   ├── urls.py
│   │   └── __init__.py
│   │
│   ├── security_photos/         # Live photo management
│   │   ├── apps.py
│   │   ├── models.py            # SecurityPhoto, Nonce (Phase 1)
│   │   ├── urls.py
│   │   └── __init__.py
│   │
│   └── facerecognition/         # Optional face recognition (STRICT SERVICE BOUNDARY)
│       ├── apps.py              # No imports of face_recognition at startup
│       ├── models.py
│       ├── tests.py             # Comprehensive test suite
│       ├── urls.py
│       ├── __init__.py
│       ├── services/            # Service layer
│       │   ├── __init__.py      # FaceRecognitionService factory
│       │   └── base.py          # BaseFaceRecognitionBackend interface
│       └── backends/            # Backend implementations
│           ├── __init__.py
│           └── dlib_backend.py  # DisabledFaceRecognitionBackend, DlibFaceRecognitionBackend
│
├── manage.py                    # Django management command
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest configuration
├── conftest.py                  # Pytest fixtures
├── docker-compose.yml           # Docker Compose setup
├── Dockerfile.dev               # Development Dockerfile
├── Makefile                     # Development commands
├── .env.example                 # Environment variables template
├── .gitignore
└── docs/                        # Architecture documentation (Phase 0)
```

## Face Recognition Feature Gate

The face recognition feature is completely optional and can be toggled via environment variable:

### When FACE_RECOGNITION_ENABLED=False (Default)

```python
# In your code:
from apps.facerecognition.services import get_face_recognition_service

service = get_face_recognition_service()
result = service.detect_face(image_bytes)

# Result will always have status=NOT_ENABLED
# System operates with single-factor photo verification
```

### When FACE_RECOGNITION_ENABLED=True

```python
# Same code path as above
# Service automatically uses DlibFaceRecognitionBackend (or falls back gracefully)
# System enables optional dual-factor photo + face verification
```

### Adding Face Recognition (Optional)

To enable face recognition support:

1. Install optional dependencies:
```bash
pip install face-recognition dlib
```

2. Update `.env`:
```bash
FACE_RECOGNITION_ENABLED=True
FACE_RECOGNITION_BACKEND=dlib
LIVENESS_ENABLED=True  # Optional
```

3. Restart Django - it will automatically use the face recognition backend

## API Endpoints (Phase 1 Placeholder)

Health check endpoint is available:

```bash
# Check system health
curl http://localhost:8000/health/check/

# Response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "message": "Smart Campus Token Management System is operational"
# }
```

Full API endpoints will be implemented in Phase 1 continuation:
- `/api/v1/auth/` - Authentication endpoints
- `/api/v1/tokens/` - Token management endpoints
- `/api/v1/photos/` - Photo management endpoints
- `/api/v1/face-recognition/` - Face recognition endpoints (if enabled)

## Database Configuration

### PostgreSQL (Production/Staging)

```bash
# Set DATABASE_URL in .env
DATABASE_URL=postgresql://user:password@localhost:5432/campus_tokens

# Install PostgreSQL adapter
pip install psycopg2-binary
```

### SQLite (Development)

```bash
# Default - no additional setup needed
DATABASE_URL=sqlite:///db.sqlite3
```

### Migrations

```bash
# Create migrations from model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Squash migrations (optional, for cleaner history)
python manage.py squashmigrations [app_label] [migration_number]
```

## Redis Configuration (Optional)

For caching and session management:

```bash
# Set REDIS_URL in .env
REDIS_URL=redis://localhost:6379/0

# Start Redis
redis-server

# Verify Redis is running
redis-cli ping  # Should return PONG
```

## Troubleshooting

### Django won't start

```bash
# Check configuration
python manage.py check

# View full error traceback
python manage.py runserver --traceback
```

### Database connection errors

```bash
# Verify PostgreSQL is running
psql -U user -d campus_tokens

# Check DATABASE_URL format
echo $DATABASE_URL
# Expected: postgresql://user:password@localhost:5432/campus_tokens
```

### Face recognition library import errors

This is expected if `FACE_RECOGNITION_ENABLED=False`. The system is designed to work without it.

```bash
# If you want to enable face recognition:
pip install face-recognition dlib
```

### Tests failing

```bash
# Run with verbose output
pytest -vv

# Run single test
pytest apps/facerecognition/tests.py::DjangoBootstrapTests::test_django_boots_without_face_recognition_library -v

# Show print statements
pytest -s
```

## Code Quality

### Lint Code

```bash
# Check code style
flake8 apps/ project/

# Or using make
make lint
```

### Format Code

```bash
# Format with black and isort
black apps/ project/
isort apps/ project/

# Or using make
make format
```

### Security Check

```bash
# Run bandit security analysis
bandit -r apps/ project/ -ll

# Or using make
make security-check
```

## Admin Interface

```bash
# Start development server
python manage.py runserver

# Visit admin interface
# http://localhost:8000/admin/

# Log in with superuser credentials created during setup
```

## Next Steps

Phase 1 continues with:
1. Database models implementation (User, SecurityPhoto, CampusToken, etc.)
2. REST API endpoints for authentication and token generation
3. Live photo capture mechanics implementation
4. Rate limiting and security middleware
5. Full test coverage

See [development-phases.md](../docs/development-phases.md) for the complete Phase 1 roadmap.

## Additional Resources

- [Architecture Documentation](../docs/architecture.md)
- [Database Design](../docs/database-design.md)
- [API Design](../docs/api-design.md)
- [Security Model](../docs/security-model.md)
- [Development Phases](../docs/development-phases.md)
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
