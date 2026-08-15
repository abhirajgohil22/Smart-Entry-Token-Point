# Smart Campus Token Management - Database Design

## Database Technology Stack

- **Primary DBMS**: PostgreSQL 14+ (ACID compliance, UUID support, JSONB)
- **Connection Pool**: pgBouncer for connection management
- **Backup Strategy**: WAL archiving + Point-in-Time Recovery (PITR)
- **Replication**: Primary + 2 Read Replicas (hot standby)

## Core Data Model

### Entity Relationship Diagram (Conceptual)

```
┌─────────────────┐
│     User        │
│  (Student Acct) │
└────────┬────────┘
         │ 1:N
         ├──────────────────────┐
         │                      │
    ┌────▼──────────┐    ┌─────▼────────┐
    │ SecurityPhoto │    │ CampusToken  │
    │   (Events)    │    │  (Generated) │
    └────┬──────────┘    └──────────────┘
         │
         │ 1:N
         │
    ┌────▼──────────────────────┐
    │ FaceRecognitionResult      │
    │ (Optional ML Data)         │
    └────────────────────────────┘

    ┌──────────────────┐
    │ RefreshToken     │
    │ (Session Mgmt)   │
    └──────────────────┘

    ┌──────────────────┐
    │ AuditLog         │
    │ (Compliance)     │
    └──────────────────┘

    ┌──────────────────┐
    │ DeviceFingerprint│
    │ (Security)       │
    └──────────────────┘
```

---

## Table Schemas

### 1. USER Table

**Purpose**: Core student account data

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity Information
    email VARCHAR(255) NOT NULL UNIQUE,
    student_id VARCHAR(50) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    
    -- Authentication
    password_hash VARCHAR(255),  -- Nullable for OAuth-only accounts
    password_salt VARCHAR(255),
    is_oauth_only BOOLEAN DEFAULT FALSE,
    
    -- Account Status
    account_status ENUM('PENDING_VERIFICATION', 'ACTIVE', 'SUSPENDED', 'DEACTIVATED') 
        DEFAULT 'PENDING_VERIFICATION',
    is_email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    
    -- OAuth Integration
    google_oauth_id VARCHAR(255) UNIQUE,
    google_oauth_token_refresh VARCHAR(500),
    google_oauth_link_date TIMESTAMP WITH TIME ZONE,
    
    -- Profile Data
    phone_number VARCHAR(20),
    profile_picture_photo_id UUID REFERENCES security_photos(id) ON DELETE SET NULL,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    
    -- Compliance
    gdpr_consent_given BOOLEAN DEFAULT FALSE,
    gdpr_consent_date TIMESTAMP WITH TIME ZONE,
    terms_accepted_version VARCHAR(20),
    
    -- Indexes
    CONSTRAINT email_format CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'),
    CONSTRAINT password_complexity CHECK (
        password_hash IS NULL OR 
        (LENGTH(password_hash) > 0 AND is_oauth_only = FALSE)
    )
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_student_id ON users(student_id);
CREATE INDEX idx_users_google_oauth_id ON users(google_oauth_id);
CREATE INDEX idx_users_account_status ON users(account_status);
CREATE INDEX idx_users_created_at ON users(created_at DESC);
```

---

### 2. SECURITY_PHOTO Table

**Purpose**: Core mandatory live photo capture records (4 workflows)

```sql
CREATE TABLE security_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Ownership & Context
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workflow_event ENUM(
        'REGISTRATION',      -- Workflow 1
        'LOGIN',             -- Workflow 2
        'TOKEN_GENERATION',  -- Workflow 3
        'TOKEN_REGENERATION' -- Workflow 4
    ) NOT NULL,
    
    -- Photo Data
    photo_blob_s3_key VARCHAR(500) NOT NULL UNIQUE,  -- S3 path
    photo_file_size_bytes INTEGER NOT NULL,
    photo_mime_type VARCHAR(50) DEFAULT 'image/jpeg',
    photo_dimensions_width INTEGER,
    photo_dimensions_height INTEGER,
    
    -- Encryption & Security
    encryption_algorithm VARCHAR(50) DEFAULT 'AES-256-GCM',
    encryption_key_id VARCHAR(100) NOT NULL,  -- KMS key ID
    photo_content_hash VARCHAR(64) NOT NULL,  -- SHA-256 hex
    
    -- Nonce & Freshness Validation
    nonce_value VARCHAR(128) NOT NULL UNIQUE,
    nonce_generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    nonce_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    photo_captured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Client Device Fingerprint
    device_fingerprint_id UUID REFERENCES device_fingerprints(id),
    client_user_agent TEXT,
    client_ip_address INET,
    
    -- Optional Face Recognition (if enabled)
    face_recognized BOOLEAN DEFAULT FALSE,
    face_recognition_error VARCHAR(255),  -- NULL if successful/not run
    face_embedding_id UUID REFERENCES face_recognition_results(id) ON DELETE SET NULL,
    
    -- Nonce Validation Results
    nonce_valid BOOLEAN NOT NULL DEFAULT FALSE,
    timestamp_valid BOOLEAN NOT NULL DEFAULT FALSE,
    fingerprint_valid BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Overall Status
    validation_status ENUM(
        'PENDING',          -- Received, awaiting validation
        'VALIDATED',        -- All checks passed
        'REJECTED',         -- Failed validation
        'PROCESSING'        -- Face recognition in progress
    ) DEFAULT 'PENDING',
    
    validation_error_message TEXT,
    
    -- Audit Trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Data Retention Policy
    retention_policy_expires_at TIMESTAMP WITH TIME ZONE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT valid_dimensions CHECK (
        (photo_dimensions_width IS NULL AND photo_dimensions_height IS NULL) OR
        (photo_dimensions_width > 0 AND photo_dimensions_height > 0)
    ),
    CONSTRAINT freshness_window CHECK (photo_captured_at BETWEEN nonce_generated_at AND nonce_expires_at),
    CONSTRAINT archived_with_timestamp CHECK (
        (is_archived = FALSE AND archived_at IS NULL) OR
        (is_archived = TRUE AND archived_at IS NOT NULL)
    )
);

CREATE INDEX idx_security_photos_user_id ON security_photos(user_id);
CREATE INDEX idx_security_photos_workflow_event ON security_photos(workflow_event);
CREATE INDEX idx_security_photos_validation_status ON security_photos(validation_status);
CREATE INDEX idx_security_photos_created_at ON security_photos(created_at DESC);
CREATE INDEX idx_security_photos_nonce_expires_at ON security_photos(nonce_expires_at);
CREATE INDEX idx_security_photos_retention_expires_at ON security_photos(retention_policy_expires_at);
CREATE INDEX idx_security_photos_s3_key ON security_photos(photo_blob_s3_key);
```

---

### 3. CAMPUS_TOKEN Table

**Purpose**: Temporary entry tokens generated after live photo validation

```sql
CREATE TABLE campus_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Token Ownership
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    generated_from_photo_id UUID NOT NULL REFERENCES security_photos(id) ON DELETE RESTRICT,
    
    -- Token Value & Type
    token_value VARCHAR(500) NOT NULL UNIQUE,  -- JWT or cryptographic token
    token_type ENUM('JWT', 'OPAQUE') DEFAULT 'JWT',
    
    -- Token Lifecycle
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoke_reason VARCHAR(255),
    
    -- Usage Tracking
    activation_status ENUM(
        'ACTIVE',
        'EXPIRED',
        'REVOKED',
        'REDEEMED'
    ) DEFAULT 'ACTIVE',
    
    -- QR Code & Presentation
    qr_code_s3_key VARCHAR(500),
    display_format ENUM('QR_CODE', 'TEXT_TOKEN', 'BARCODE') DEFAULT 'QR_CODE',
    
    -- Metadata
    issuing_device_fingerprint_id UUID REFERENCES device_fingerprints(id),
    issuing_client_ip INET,
    
    -- Multi-use Token Support
    max_uses INTEGER DEFAULT -1,  -- -1 = unlimited
    current_uses INTEGER DEFAULT 0,
    usage_log_entries JSONB DEFAULT '[]'::jsonb,  -- [{timestamp, access_point, result}, ...]
    
    -- Token Regeneration Chain
    regenerated_from_token_id UUID REFERENCES campus_tokens(id) ON DELETE SET NULL,
    regeneration_count INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_lifecycle CHECK (
        (revoked_at IS NULL AND revoke_reason IS NULL) OR
        (revoked_at IS NOT NULL AND revoke_reason IS NOT NULL)
    ),
    CONSTRAINT expires_after_issued CHECK (expires_at > issued_at),
    CONSTRAINT usage_tracking CHECK (
        (max_uses = -1) OR 
        (max_uses > 0 AND current_uses >= 0 AND current_uses <= max_uses)
    )
);

CREATE INDEX idx_campus_tokens_user_id ON campus_tokens(user_id);
CREATE INDEX idx_campus_tokens_activation_status ON campus_tokens(activation_status);
CREATE INDEX idx_campus_tokens_token_value ON campus_tokens(token_value);
CREATE INDEX idx_campus_tokens_expires_at ON campus_tokens(expires_at);
CREATE INDEX idx_campus_tokens_created_at ON campus_tokens(created_at DESC);
CREATE INDEX idx_campus_tokens_generated_from_photo_id ON campus_tokens(generated_from_photo_id);
```

---

### 4. FACE_RECOGNITION_RESULT Table

**Purpose**: Optional face recognition embeddings & liveness detection (only if enabled)

```sql
CREATE TABLE face_recognition_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Photo Association
    security_photo_id UUID NOT NULL UNIQUE REFERENCES security_photos(id) ON DELETE CASCADE,
    
    -- Face Detection
    face_detected BOOLEAN NOT NULL,
    face_count INTEGER DEFAULT 0,
    primary_face_confidence FLOAT,  -- 0.0-1.0
    
    -- Liveness Detection (optional)
    liveness_detected BOOLEAN DEFAULT FALSE,
    liveness_confidence FLOAT,  -- 0.0-1.0
    liveness_algorithm VARCHAR(100),  -- e.g., "deepface", "facenet", custom
    
    -- Face Embedding
    face_embedding_vector FLOAT8[] NOT NULL,  -- PostgreSQL float array
    face_embedding_model VARCHAR(100) DEFAULT 'facenet',  -- Model used to generate
    face_embedding_dimension INTEGER DEFAULT 512,
    
    -- Identity Verification (against enrolled photos)
    identity_match_found BOOLEAN DEFAULT FALSE,
    matched_enrollment_photo_id UUID REFERENCES security_photos(id) ON DELETE SET NULL,
    identity_match_confidence FLOAT,  -- 0.0-1.0
    identity_match_distance FLOAT,  -- Euclidean distance
    
    -- Recognition Process Metadata
    processing_backend VARCHAR(100),  -- e.g., "face_recognition_library", "deepface", "aws_rekognition"
    processing_duration_ms INTEGER,
    processing_error TEXT,
    
    -- Server-side Validation
    validation_passed BOOLEAN DEFAULT FALSE,
    validation_error_message TEXT,
    
    -- Timestamp
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT face_detected_constraint CHECK (
        (face_detected = FALSE AND face_count = 0) OR
        (face_detected = TRUE AND face_count > 0)
    ),
    CONSTRAINT confidence_range_primary CHECK (
        (primary_face_confidence IS NULL) OR 
        (primary_face_confidence >= 0.0 AND primary_face_confidence <= 1.0)
    ),
    CONSTRAINT confidence_range_liveness CHECK (
        (liveness_confidence IS NULL) OR
        (liveness_confidence >= 0.0 AND liveness_confidence <= 1.0)
    ),
    CONSTRAINT confidence_range_identity CHECK (
        (identity_match_confidence IS NULL) OR
        (identity_match_confidence >= 0.0 AND identity_match_confidence <= 1.0)
    ),
    CONSTRAINT embedding_dimension_match CHECK (
        array_length(face_embedding_vector, 1) = face_embedding_dimension
    )
);

CREATE INDEX idx_face_recognition_results_security_photo_id ON face_recognition_results(security_photo_id);
CREATE INDEX idx_face_recognition_results_matched_enrollment_photo_id ON face_recognition_results(matched_enrollment_photo_id);
CREATE INDEX idx_face_recognition_results_validation_passed ON face_recognition_results(validation_passed);
CREATE INDEX idx_face_recognition_results_processed_at ON face_recognition_results(processed_at DESC);

-- Vector similarity search (if using pgvector extension)
-- CREATE INDEX ON face_recognition_results USING ivfflat (face_embedding_vector vector_cosine_ops)
```

---

### 5. DEVICE_FINGERPRINT Table

**Purpose**: Track and validate device/browser combinations for security

```sql
CREATE TABLE device_fingerprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Device Identification
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_unique_hash VARCHAR(128) NOT NULL UNIQUE,  -- SHA-256 of fingerprint components
    
    -- Browser & Device Info
    user_agent TEXT NOT NULL,
    browser_name VARCHAR(100),
    browser_version VARCHAR(50),
    operating_system VARCHAR(100),
    device_type ENUM('DESKTOP', 'MOBILE', 'TABLET') DEFAULT 'DESKTOP',
    
    -- Device Characteristics
    screen_resolution VARCHAR(50),  -- "1920x1080"
    timezone VARCHAR(100),
    language VARCHAR(50),
    
    -- Network Info
    ip_address INET,
    ip_geolocation JSONB,  -- {country, city, latitude, longitude}
    
    -- Trust Status
    is_trusted BOOLEAN DEFAULT FALSE,
    trust_date TIMESTAMP WITH TIME ZONE,
    
    -- Usage History
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 1,
    
    -- Risk Assessment
    risk_score FLOAT DEFAULT 0.0,  -- 0.0-1.0
    anomaly_detected BOOLEAN DEFAULT FALSE,
    anomaly_reason TEXT,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_device_fingerprints_user_id ON device_fingerprints(user_id);
CREATE INDEX idx_device_fingerprints_device_unique_hash ON device_fingerprints(device_unique_hash);
CREATE INDEX idx_device_fingerprints_is_trusted ON device_fingerprints(is_trusted);
CREATE INDEX idx_device_fingerprints_anomaly_detected ON device_fingerprints(anomaly_detected);
```

---

### 6. REFRESH_TOKEN Table

**Purpose**: Session management and JWT refresh tokens

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Token Ownership
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Token Value
    token_hash VARCHAR(255) NOT NULL UNIQUE,  -- Hashed for security
    token_salt VARCHAR(255),
    
    -- Token Lifecycle
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoke_reason VARCHAR(255),
    
    -- Session Context
    device_fingerprint_id UUID REFERENCES device_fingerprints(id),
    ip_address INET,
    
    -- Usage Tracking
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    refresh_count INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_is_active ON refresh_tokens(is_active);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
```

---

### 7. AUDIT_LOG Table

**Purpose**: Compliance & security audit trail of all critical events

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event Classification
    event_type ENUM(
        'USER_REGISTERED',
        'USER_LOGIN',
        'USER_LOGOUT',
        'PHOTO_CAPTURED',
        'PHOTO_VALIDATED',
        'PHOTO_REJECTED',
        'FACE_RECOGNITION_RUN',
        'FACE_RECOGNITION_PASSED',
        'FACE_RECOGNITION_FAILED',
        'TOKEN_GENERATED',
        'TOKEN_REGENERATED',
        'TOKEN_REVOKED',
        'TOKEN_REDEEMED',
        'OAUTH_LINKED',
        'OAUTH_UNLINKED',
        'PASSWORD_CHANGED',
        'MFA_ENABLED',
        'MFA_DISABLED',
        'GDPR_EXPORT_REQUESTED',
        'GDPR_DELETE_REQUESTED',
        'ACCOUNT_SUSPENDED',
        'SECURITY_INCIDENT'
    ) NOT NULL,
    
    -- Actor Information
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_type ENUM('USER', 'ADMIN', 'SYSTEM', 'AUTOMATION') DEFAULT 'USER',
    
    -- Resource Information
    affected_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    affected_photo_id UUID REFERENCES security_photos(id) ON DELETE SET NULL,
    affected_token_id UUID REFERENCES campus_tokens(id) ON DELETE SET NULL,
    
    -- Event Context
    context_data JSONB DEFAULT '{}'::jsonb,  -- Flexible schema for event-specific data
    description TEXT,
    
    -- Security & Compliance
    ip_address INET,
    user_agent TEXT,
    device_fingerprint_id UUID REFERENCES device_fingerprints(id),
    
    -- Outcome
    outcome ENUM('SUCCESS', 'FAILURE', 'PARTIAL') DEFAULT 'SUCCESS',
    error_message TEXT,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Data Retention
    retention_until TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT at_least_one_actor CHECK (
        actor_user_id IS NOT NULL OR actor_type IN ('ADMIN', 'SYSTEM', 'AUTOMATION')
    )
);

CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_actor_user_id ON audit_logs(actor_user_id);
CREATE INDEX idx_audit_logs_affected_user_id ON audit_logs(affected_user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_outcome ON audit_logs(outcome);
CREATE INDEX idx_audit_logs_retention_until ON audit_logs(retention_until);
```

---

### 8. NONCE_TABLE

**Purpose**: Track and validate server-generated nonces for CSRF/freshness prevention

```sql
CREATE TABLE nonces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Nonce Value
    nonce_value VARCHAR(128) NOT NULL UNIQUE,
    nonce_hash VARCHAR(255) NOT NULL UNIQUE,  -- SHA-256
    
    -- Nonce Purpose
    nonce_purpose ENUM(
        'PHOTO_CAPTURE_REGISTRATION',
        'PHOTO_CAPTURE_LOGIN',
        'PHOTO_CAPTURE_TOKEN_GENERATION',
        'PHOTO_CAPTURE_TOKEN_REGENERATION',
        'CSRF_FORM_PROTECTION'
    ) NOT NULL,
    
    -- Issuance & Expiry
    issued_to_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Usage
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP WITH TIME ZONE,
    
    -- Context
    session_id VARCHAR(255),
    ip_address INET,
    
    -- Constraints
    CONSTRAINT used_state_consistency CHECK (
        (is_used = FALSE AND used_at IS NULL) OR
        (is_used = TRUE AND used_at IS NOT NULL)
    )
);

CREATE INDEX idx_nonces_nonce_value ON nonces(nonce_value);
CREATE INDEX idx_nonces_issued_to_user_id ON nonces(issued_to_user_id);
CREATE INDEX idx_nonces_expires_at ON nonces(expires_at);
CREATE INDEX idx_nonces_is_used ON nonces(is_used);
```

---

## Database Views

### View: user_photo_timeline

**Purpose**: Historical view of all photos captured by a user

```sql
CREATE VIEW user_photo_timeline AS
SELECT
    sp.id,
    sp.user_id,
    sp.workflow_event,
    sp.photo_captured_at,
    sp.validation_status,
    sp.nonce_valid,
    sp.timestamp_valid,
    sp.fingerprint_valid,
    COALESCE(frr.validation_passed, FALSE) AS face_validation_passed,
    u.email,
    u.student_id
FROM security_photos sp
LEFT JOIN face_recognition_results frr ON sp.id = frr.security_photo_id
LEFT JOIN users u ON sp.user_id = u.id
ORDER BY sp.photo_captured_at DESC;
```

### View: active_tokens_by_user

**Purpose**: Current valid tokens for each user

```sql
CREATE VIEW active_tokens_by_user AS
SELECT
    ct.user_id,
    ct.id AS token_id,
    ct.issued_at,
    ct.expires_at,
    ct.current_uses,
    ct.max_uses,
    ct.activation_status,
    CURRENT_TIMESTAMP < ct.expires_at AS is_active,
    u.email,
    u.student_id
FROM campus_tokens ct
LEFT JOIN users u ON ct.user_id = u.id
WHERE ct.activation_status IN ('ACTIVE', 'EXPIRED')
ORDER BY ct.expires_at DESC;
```

---

## Data Lifecycle & Retention

### User Personal Data (GDPR Compliance)

| Data Type | Retention Period | Deletion Policy |
|-----------|------------------|-----------------|
| User Account (active) | Duration of use + 1 year | On account deactivation |
| Security Photos | 90 days | Automatic purge + crypto-shred |
| Face Embeddings | 60 days | Automatic purge (if enabled) |
| Refresh Tokens | 30 days | Auto-expire + revoke |
| Audit Logs | 7 years | Archived after 1 year |
| Device Fingerprints | 180 days | Soft delete on request |

---

## Database Performance Tuning

### Query Optimization

1. **Photo Lookup by User**: `idx_security_photos_user_id` + time-range filtering
2. **Token Expiry Scanning**: Nightly batch using `idx_campus_tokens_expires_at`
3. **Audit Log Retention**: Partition by date using `created_at`
4. **Nonce Validation**: Redis cache layer (15-second TTL) before DB lookup

### Partitioning Strategy

```sql
-- Partition security_photos by created_at (monthly)
ALTER TABLE security_photos
PARTITION BY RANGE (DATE_TRUNC('month', created_at));

-- Partition audit_logs by created_at (quarterly)
ALTER TABLE audit_logs
PARTITION BY RANGE (DATE_TRUNC('quarter', created_at));
```

### Caching Strategy (Redis)

- **Nonce Cache**: `nonce:{nonce_value}` (15 sec TTL)
- **User Session**: `session:{session_id}` (configurable TTL)
- **Device Fingerprint**: `device_fp:{hash}` (24 hr TTL)
- **Active Tokens**: `tokens:{user_id}` (1 hour TTL)

---

## Database Initialization & Migrations

### Phase 0 Tasks

1. ✅ Create all table schemas with constraints
2. ✅ Define all indexes and foreign key relationships
3. ✅ Create views for common queries
4. ✅ Set up replication + backups
5. ✅ Configure GDPR compliance automated policies
6. ✅ Design migration strategy (Alembic for Django)

### Migration Framework

- **Tool**: Django Migrations (Alembic-compatible)
- **Version Control**: All `.py` migration files in `migrations/`
- **Zero-Downtime**: Non-blocking migration strategy (add column → populate → drop old)

---

**Document Version**: 1.0  
**Last Updated**: 2026-08-15  
**Database Architect**: [Your Name/Team]  
**Status**: Phase 0 - Design Complete
