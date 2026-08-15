# Smart Campus Token Management System - Architecture

## Executive Summary

The Smart Campus Token Management System is a production-ready web application that enables students to generate temporary digital entry tokens when they forget or lose their physical student ID cards. The system enforces mandatory live photo capture across four critical user journeys while maintaining graceful degradation when optional face recognition services are unavailable.

## Core Architectural Principles

### 1. **Mandatory Live Photo Capture**
- Live photo capture is **non-negotiable** across four key events:
  - **REGISTRATION**: Initial account setup
  - **LOGIN**: Every authentication session
  - **TOKEN GENERATION**: Creating new temporary access tokens
  - **TOKEN REGENERATION**: Reissuing expired or revoked tokens

- **Photo Source Constraints**:
  - Only real-time video stream captures via `navigator.mediaDevices.getUserMedia()` are accepted
  - Existing photos (profile pictures, gallery images, old security photos) are **explicitly rejected**
  - Client-side canvas rendering enforces photo freshness via server-side nonce validation
  - No file uploads or historical photo substitution permitted

### 2. **Optional Face Recognition**
- Face recognition is **feature-gated** via `FACE_RECOGNITION_ENABLED=True/False` environment variable
- System operates normally regardless of face recognition service availability
- When enabled: Used for advanced security verification (liveness detection, identity matching)
- When disabled: System gracefully degrades to single-factor live photo verification

### 3. **Zero Hard Dependencies on ML Libraries**
- The application **must operate without**:
  - `face_recognition` library
  - `dlib` backend
  - `opencv-python` dependencies
- These are optional dependencies that only load if explicitly enabled and properly installed
- Core functionality remains unaffected if ML libraries are absent

### 4. **Authentication & Authorization Integration**
- Google OAuth2 / Social login **integrates seamlessly** but does NOT bypass mandatory live photo steps
- Email OTP verification layers cleanly with the live photo workflow
- Multi-factor authentication (MFA) supported without conflicting with photo capture requirements

## System Architecture Layers

### Frontend Layer
```
├── Web Browser (Chrome, Firefox, Safari)
├── WebRTC API (navigator.mediaDevices.getUserMedia)
├── Canvas Drawing API (frame capture)
├── File API (Blob creation)
├── Form API (Multipart FormData)
└── REST Client (XHR/Fetch)
```

**Responsibilities:**
- Real-time video stream capture from user's camera
- Canvas-based frame extraction at user-initiated moment
- Blob conversion for HTTP transmission
- Multipart FormData assembly with nonce/metadata
- Server response handling and UI state management

### Backend Layer
```
├── REST API (Django REST Framework)
├── Authentication Module (JWT + OAuth2)
├── Photo Processing Pipeline (Validation & Nonce Check)
├── Security Photo Service (Storage & Metadata)
├── Optional Face Recognition Service (if enabled)
├── Token Generation Engine (JWT creation)
└── Database Layer (PostgreSQL)
```

**Responsibilities:**
- Request validation (nonce, timestamp, device fingerprint)
- Photo integrity verification
- Optional face recognition processing
- Secure token generation
- Audit logging of all photo events

## Four Mandatory Workflows

### 1. REGISTRATION Workflow
```
User Initiates Registration
    ↓
Camera Permission Grant (WebRTC)
    ↓
Live Video Stream Display
    ↓
User Captures Live Photo (Canvas)
    ↓
Blob Creation + Nonce Embedding
    ↓
Multipart FormData Assembly
    ↓
POST /api/auth/register/photo
    ↓
Server: Nonce Validation
    ↓
Server: Photo Format & Freshness Check
    ↓
Server: Optional Face Liveness Detection
    ↓
Server: SecurityPhoto Record Creation
    ↓
Complete Registration (Email Verification)
```

### 2. LOGIN Workflow
```
Email/Username + Password Entry
    ↓
Camera Permission Grant
    ↓
Live Video Stream Display
    ↓
User Captures Live Photo (Canvas)
    ↓
Blob Creation + Nonce Embedding
    ↓
POST /api/auth/login/photo
    ↓
Server: Photo Validation (same as Registration)
    ↓
Server: Optional Face Recognition (vs. stored profile)
    ↓
Token Generation (JWT)
    ↓
Session Creation + Audit Log
```

### 3. TOKEN GENERATION Workflow
```
Authenticated User Requests Token
    ↓
Camera Permission Check
    ↓
Live Video Stream Display
    ↓
User Captures Live Photo (Canvas)
    ↓
Blob Creation + Nonce Embedding
    ↓
POST /api/tokens/generate/photo
    ↓
Server: Identity Verification (from session)
    ↓
Server: Photo Validation & Nonce Check
    ↓
Server: Optional Face Recognition (liveness only)
    ↓
SecurityPhoto Record + Audit Entry
    ↓
Generate & Return Temporary Token
    ↓
Display QR Code / Token to User
```

### 4. TOKEN REGENERATION Workflow
```
User Initiates Token Regeneration
    ↓
Existing Token Verification
    ↓
Camera Permission Grant
    ↓
Live Video Stream Display
    ↓
User Captures Live Photo (Canvas)
    ↓
Blob Creation + Nonce Embedding
    ↓
POST /api/tokens/regenerate/photo
    ↓
Server: Existing Token Validation
    ↓
Server: Photo Validation & Nonce Check
    ↓
Server: Optional Face Recognition
    ↓
SecurityPhoto Record Creation
    ↓
Revoke Old Token + Issue New Token
    ↓
Display New Token/QR Code
```

## Technology Stack

### Frontend
- **Core Framework**: React/Vue with TypeScript
- **WebRTC**: Native browser API (no external library required)
- **State Management**: Redux/Vuex for camera/form state
- **HTTP Client**: Axios/Fetch for API communication
- **UI Framework**: Material-UI / Bootstrap for responsive design

### Backend
- **Framework**: Django 4.2+ with Django REST Framework
- **Authentication**: djangorestframework-simplejwt + python-social-auth
- **Database**: PostgreSQL 14+ (PostGIS optional for campus location tracking)
- **Task Queue**: Celery + Redis for async photo processing
- **Email**: Django-anymail + SendGrid/AWS SES
- **Face Recognition** (Optional):
  - Primary: `face_recognition` library (ageitgey/face_recognition)
  - Alternative: DeepFace backend
  - Conditional: Only imported if `FACE_RECOGNITION_ENABLED=True`

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Web Server**: Gunicorn + Nginx reverse proxy
- **Message Queue**: Redis for caching + Celery tasks
- **Storage**: AWS S3 / MinIO for encrypted photo storage
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or CloudWatch

## Data Flow Architecture

### Live Photo Capture Data Pipeline
```
User (Browser)
    ↓
navigator.mediaDevices.getUserMedia()
    ├─ Requests camera permission
    ├─ Establishes video stream
    └─ Renders in <video> element

Canvas Drawing API
    ├─ Extracts current frame to canvas
    ├─ Converts to ImageData
    └─ Generates bitmap representation

Photo Processing (Client)
    ├─ Canvas.toBlob() for compression
    ├─ Associates server nonce
    ├─ Embeds timestamp
    └─ Calculates client-side hash

FormData Assembly
    ├─ Appends photo blob
    ├─ Embeds nonce & timestamp
    ├─ Includes device fingerprint
    ├─ Adds context (workflow type)
    └─ Multipart/form-data encoding

HTTP Transmission
    └─ POST to REST endpoint

Server Reception
    ├─ Multipart parsing
    ├─ Photo binary validation
    ├─ Nonce expiration check
    ├─ Timestamp freshness validation
    └─ Device fingerprint verification

Photo Validation
    ├─ File type verification (JPEG/PNG)
    ├─ Magic number validation
    ├─ Dimension constraints
    ├─ Liveness scoring (if face recognition enabled)
    └─ No duplicate detection

Secure Storage
    ├─ Generate unique photo ID (UUID)
    ├─ Encrypt blob with KMS master key
    ├─ Upload to S3 (versioned bucket)
    ├─ Create SecurityPhoto database record
    └─ Link to User + Event context

Optional Face Recognition
    ├─ Extract face embedding (if enabled)
    ├─ Compare against stored profile embeddings
    ├─ Generate liveness confidence score
    ├─ Log all recognition attempts
    └─ Return pass/fail result

Audit & Logging
    ├─ Log workflow event
    ├─ Record photo metadata
    ├─ Track face recognition results
    ├─ Monitor anomalies
    └─ Compliance audit trail
```

## Security Considerations

### Photo Authenticity
- **Nonce Mechanism**: Server generates nonce, embeds in HTML, client includes in form submission
- **Timestamp Validation**: Photo submission must occur within 60 seconds of nonce generation
- **Client Fingerprint**: Device ID + Browser fingerprint prevents photo replay from different devices
- **Hash Chain**: Client-side content hash prevents tampering en route

### Face Recognition Safety
- Face embeddings stored separately from photos
- Embeddings never transmitted to third-party services
- Optional feature can be completely disabled without system degradation
- All recognition attempts logged with confidence scores and outcomes

### Photo Storage Security
- Server-side encryption (AES-256-GCM) at rest
- TLS 1.3+ encryption in transit
- S3 bucket versioning + MFA delete protection
- Automatic photo retention/purge policies
- GDPR-compliant data deletion workflows

### API Security
- Rate limiting per user (10 requests/minute, 100 requests/hour)
- DDoS protection at edge (Cloudflare / AWS Shield)
- CSRF token protection for forms
- CORS policy restricted to campus domain only
- API versioning for backward compatibility

## Deployment Topology

### Development Environment
```
Local Machine
├─ Docker container (PostgreSQL)
├─ Docker container (Redis)
├─ Django dev server (localhost:8000)
├─ React dev server (localhost:3000)
└─ MinIO (local S3-compatible storage)
```

### Staging Environment
```
AWS / GCP
├─ Application Load Balancer (ALB)
├─ ECS/GKE cluster (3 replicas)
├─ RDS PostgreSQL (Multi-AZ)
├─ ElastiCache Redis
├─ S3 bucket (versioned)
├─ Secrets Manager (for environment variables)
└─ CloudWatch / DataDog monitoring
```

### Production Environment
```
AWS / GCP Enterprise
├─ Global load balancer
├─ Multi-region deployment
├─ Auto-scaling Kubernetes cluster
├─ Database: Primary + Read replicas + Backup
├─ Redis cluster (high availability)
├─ S3 with cross-region replication
├─ KMS for encryption key management
├─ WAF + DDoS protection
├─ VPC + Private subnets
└─ Centralized logging + alerting
```

## System Resilience & Graceful Degradation

### Face Recognition Unavailability
- System continues normal operation if face recognition fails to initialize
- All 4 workflows proceed without face verification when `FACE_RECOGNITION_ENABLED=False`
- Logging captures ML service status (available/unavailable)
- Admin dashboard alerts when optional services become unavailable

### Camera Permission Denial
- Clear UX messaging explaining why camera is required
- Fallback option: Retry with refreshed permissions dialog
- No token generation permitted without live photo capture
- Audit logs record denied camera attempts

### Network Interruption
- Client-side queue for failed photo submissions
- Automatic retry with exponential backoff
- User notification of sync status
- No data loss on connection recovery

## Integration Points

### Google OAuth2
- OAuth flow completes with user identity verified
- **Still requires** live photo capture during login or token generation
- Session established only after both OAuth AND photo validation succeed
- User profile linked to captured photo metadata

### Email OTP Verification
- OTP sent after initial credentials verification
- OTP validation succeeds but doesn't grant access
- User must then capture live photo to complete login
- Multi-factor authentication: (Password + OTP) + Live Photo

### Campus Access Control Systems
- Token validation API for door locks/turnstiles
- Real-time token status checking (valid/expired/revoked)
- Audit trail of token usage attempts
- Integration with physical campus security logs

## Success Criteria for Phase 0

✅ Complete architectural documentation defining all 4 workflows  
✅ Live photo capture mechanism fully specified (WebRTC → Canvas → Blob → API)  
✅ Optional face recognition design with graceful degradation  
✅ Security model with nonce + timestamp validation  
✅ Database schema defined for all entities  
✅ API contract fully specified (endpoints, request/response formats)  
✅ Deployment topology and infrastructure requirements  
✅ Development phases clearly sequenced (Phase 1-5)  

---

**Document Version**: 1.0  
**Last Updated**: 2026-08-15  
**Architecture Lead**: [Your Name/Team]  
**Status**: Phase 0 - Design Complete
