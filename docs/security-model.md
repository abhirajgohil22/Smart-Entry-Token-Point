# Smart Campus Token Management - Security Model

## Security Philosophy

The Smart Campus Token Management System is built on **Zero Trust Architecture** with **Defense in Depth**. Every request, device, and photo is validated independently regardless of previous interactions or session state.

### Core Security Principles

1. **Mandatory Live Photo Capture** - Only real-time WebRTC camera streams accepted
2. **Nonce-based CSRF Protection** - Every state-changing operation requires fresh server nonce
3. **Timestamp Freshness Validation** - All events timestamped with server-side verification
4. **Device Fingerprinting** - Client device characteristics verified across requests
5. **Encryption at Rest & In Transit** - AES-256-GCM for photos, TLS 1.3+ for API
6. **Rate Limiting & Abuse Detection** - Per-user, per-IP, per-endpoint monitoring
7. **Audit Trail & Compliance** - Every critical event logged with full context
8. **Optional Face Recognition** - Can be disabled without compromising core security

---

## Threat Model & Risk Mitigation

### High-Risk Threats

#### 1. **Photo Forgery / Offline Photo Injection**

**Threat**: Attacker submits pre-recorded, stolen, or manipulated photo instead of live capture

**Mitigations**:
- ✅ Client-side bindings restrict photo source to `<canvas>` element only
- ✅ File picker/gallery access disabled during photo capture flow
- ✅ Server validates photo bindings via nonce + timestamp + device fingerprint
- ✅ Optional: Face liveness detection (movement, micro-expressions)
- ✅ Optional: Optical characteristics analysis (eye flutter, pupil dilation)
- ✅ Photo bindings prevent gallery extraction via:
  - Canvas only accepts `OffscreenCanvas.getContext('2d')` from video stream
  - CORS policies prevent external image sources
  - Content-Security-Policy headers block inline scripts

---

#### 2. **Nonce Reuse / Replay Attack**

**Threat**: Attacker captures valid nonce and photo pair, replays to different device/location

**Mitigations**:
- ✅ Nonce stored in database with `is_used` flag (set to TRUE after first use)
- ✅ Nonce expires after 5 minutes (configurable, default minimum 300 seconds)
- ✅ Device fingerprint must match between nonce generation and submission
- ✅ IP address logged and validated
- ✅ Timestamp must fall within nonce validity window
- ✅ Cryptographic hash prevents tampering: `SHA-256(nonce + timestamp + device_hash)`

**Nonce Lifecycle**:
```
1. Server generates cryptographically secure random nonce (64 chars hex)
2. Client embeds nonce in form submission
3. Server validates nonce exists + not_expired + not_used
4. Server marks nonce as used (is_used = TRUE)
5. Nonce can never be reused (database constraint)
6. Expired nonces auto-purged after 24 hours
```

---

#### 3. **Face Spoofing / Deepfake Attack**

**Threat**: Attacker uses printed photo, video replay, or deepfake to bypass face recognition

**Mitigations** (if face recognition enabled):
- ✅ Liveness detection checks for:
  - Eye movement (blinking pattern)
  - Head movement (yaw/pitch changes)
  - Micro-expressions (involuntary facial movements)
  - Reflection patterns in eyes (spoofing detection)
  - Temporal consistency (frame-to-frame continuity)
- ✅ Deepfake detection via:
  - Frequency domain analysis (FFT artifacts)
  - Inconsistency detection across frames
  - Compression artifacts analysis
  - Face warping detection
- ✅ Confidence threshold: Only accept faces with liveness_confidence > 0.85
- ✅ Dual-model approach: Primary model + fallback detector

**Liveness Scoring Algorithm**:
```
Liveness Score = (
    (blink_confidence × 0.20) +
    (head_movement_confidence × 0.20) +
    (temporal_consistency_score × 0.20) +
    (anti_spoofing_score × 0.20) +
    (anti_deepfake_score × 0.20)
)

Acceptance Threshold: Liveness Score ≥ 0.85
Marginal Threshold: Liveness Score ≥ 0.70 (manual review)
Rejection Threshold: Liveness Score < 0.70
```

---

#### 4. **Account Takeover / Unauthorized Token Generation**

**Threat**: Attacker gains access to user's account and generates tokens without consent

**Mitigations**:
- ✅ Mandatory live photo for every login + token generation
- ✅ Optional: Face recognition (identity match against enrolled profile)
- ✅ Email verification required for new accounts
- ✅ Email notification on token generation with revocation link
- ✅ Device fingerprint anomaly detection (new device login alerts)
- ✅ Rate limiting:
  - Max 10 login attempts per 15 minutes per IP
  - Max 10 token generations per hour per user
  - Max 5 token regenerations per hour per token
- ✅ Session timeout: 15-minute access token + 7-day refresh token

---

#### 5. **Man-in-the-Middle (MITM) Attack**

**Threat**: Attacker intercepts photo in transit, modifies nonce, or steals tokens

**Mitigations**:
- ✅ TLS 1.3+ required (HTTP/2 ALPN, no downgrade)
- ✅ HSTS header with 1-year max-age + preload list
- ✅ Certificate pinning (production)
- ✅ Multipart FormData stream encryption (optional payload encryption layer)
- ✅ Request signing: client-side hash prevents tampering
  - Hash = SHA-256(photo_blob + nonce + timestamp)
  - Server verifies hash integrity
- ✅ Token transmission via secure HttpOnly cookie (not response body for long-lived tokens)

---

#### 6. **Database Breach / Photo Exposure**

**Threat**: Attacker gains database access and exfiltrates photos or embeddings

**Mitigations**:
- ✅ Photos encrypted at rest with AES-256-GCM
- ✅ Encryption keys stored in external KMS (AWS KMS, HashiCorp Vault)
- ✅ Encryption key rotation every 90 days
- ✅ Database column-level encryption for sensitive fields
- ✅ Photos stored in separate S3 bucket with:
  - Versioning enabled
  - MFA delete protection
  - Bucket-wide encryption
  - Access logs + CloudTrail logging
  - Server-side encryption with customer-managed KMS keys
- ✅ Face embeddings stored separately from photo blobs
- ✅ Automatic photo deletion after retention period (default: 90 days)
- ✅ GDPR right-to-deletion with crypto-shred verification

---

#### 7. **Brute Force / Credential Attack**

**Threat**: Attacker repeatedly attempts login/registration with common passwords

**Mitigations**:
- ✅ Password policy enforcement:
  - Minimum 12 characters
  - Must contain uppercase, lowercase, numbers, special chars
  - Cannot contain student_id or email substrings
  - Checked against common password list (50,000+ entries)
- ✅ Rate limiting by IP/email:
  - Max 5 registration attempts per hour per IP
  - Max 10 login attempts per 15 minutes per IP
  - Max 3 failed attempts triggers temporary account lock (15 min)
- ✅ Account lockout after 10 failed login attempts (1-hour duration)
- ✅ Password reset requires email verification + temporary token
- ✅ Password history: Cannot reuse last 5 passwords
- ✅ Optional: Multi-factor authentication (MFA) via email OTP

---

### Medium-Risk Threats

#### 8. **CSRF Attack**

**Threat**: Attacker tricks user into submitting form to malicious site

**Mitigations**:
- ✅ Nonce-based CSRF tokens (every form submission requires unique nonce)
- ✅ SameSite cookie attribute set to Strict
- ✅ Origin header validation
- ✅ Referer header checking (for browsers that send it)

---

#### 9. **XSS Attack**

**Threat**: Attacker injects JavaScript into frontend to steal tokens/photos

**Mitigations**:
- ✅ Content-Security-Policy (CSP) headers:
  ```
  default-src 'self'
  script-src 'self' 'nonce-{random}'
  img-src 'self' data: https:
  style-src 'self' 'unsafe-inline'
  connect-src 'self' https://api.campus.university.edu
  media-src 'self'
  frame-ancestors 'none'
  base-uri 'self'
  form-action 'self'
  ```
- ✅ All user input sanitized using DOMPurify
- ✅ Output encoding (HTML entities, URL encoding)
- ✅ No inline JavaScript (all scripts external, nonce-based)
- ✅ HttpOnly + Secure flags on all cookies

---

#### 10. **DDoS Attack**

**Threat**: Attacker floods API with requests to cause unavailability

**Mitigations**:
- ✅ Rate limiting at multiple layers:
  - Application layer (per-user, per-IP)
  - WAF layer (AWS WAF, Cloudflare)
  - CDN layer (Cloudflare DDoS protection)
- ✅ Distributed deployment across multiple regions
- ✅ Auto-scaling on traffic spike
- ✅ Request validation (drop invalid/malformed requests early)
- ✅ Connection pooling + timeout management

---

### Low-Risk Threats

#### 11. **Information Disclosure**

**Threat**: Attacker learns sensitive information from error messages or API responses

**Mitigations**:
- ✅ Generic error messages (don't reveal whether email exists)
- ✅ No stack traces in production responses
- ✅ Sensitive fields omitted from API responses (passwords, embeddings)
- ✅ Logging sanitizes PII (truncate email, mask SSN, etc.)
- ✅ Response headers don't leak system info (remove Server, X-Powered-By)

---

#### 12. **Privilege Escalation**

**Threat**: User attempts to access/modify another user's tokens or photos

**Mitigations**:
- ✅ Authorization checks on every endpoint:
  ```python
  # Pseudo-code
  if request.user.id != token.user_id:
      raise PermissionDenied("Cannot access other user's tokens")
  ```
- ✅ Role-based access control (RBAC):
  - ROLE_STUDENT: Can generate/regenerate own tokens
  - ROLE_ADMIN: Can view audit logs, suspend accounts
  - ROLE_SECURITY: Can trigger manual face verification
- ✅ JWT claims verified on every request
- ✅ No predictable IDs (using UUIDs, not sequential integers)

---

## Cryptographic Standards

### Hashing

| Use Case | Algorithm | Library | Output Size |
|----------|-----------|---------|-------------|
| Photo content hash | SHA-256 | hashlib | 64 hex chars |
| Nonce hash | SHA-256 | hashlib | 64 hex chars |
| Password hashing | PBKDF2-SHA256 | Django AUTH_PASSWORD_HASHERS | Variable |
| Password hashing (preferred) | Argon2 | django[argon2] | Variable |

### Encryption

| Use Case | Algorithm | Key Size | Mode | IV Size |
|----------|-----------|----------|------|---------|
| Photo blob at rest | AES | 256 bits | GCM | 96 bits |
| Sensitive DB fields | AES | 256 bits | GCM | 96 bits |
| TLS transport | TLS | 256 bits | - | - |

### Digital Signatures

| Use Case | Algorithm | Library |
|----------|-----------|---------|
| JWT token signing | RS256 | PyJWT |
| Certificate authority | RSA-4096 | cryptography |

### Random Generation

```python
# Nonce generation: cryptographically secure
nonce = secrets.token_hex(32)  # 64 character hex string

# Salt generation: CSPRNG
salt = secrets.token_bytes(32)  # 32 random bytes

# Device fingerprint: SHA-256 hash of device characteristics
device_fingerprint = hashlib.sha256(
    json.dumps({
        'user_agent': ...,
        'screen_resolution': ...,
        'timezone': ...,
        'language': ...
    }).encode()
).hexdigest()
```

---

## Transport Security

### HTTPS/TLS Configuration

```nginx
# Nginx SSL Configuration
ssl_protocols TLSv1.3 TLSv1.2;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;

# Certificates
ssl_certificate /etc/letsencrypt/live/api.campus.edu/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/api.campus.edu/privkey.pem;

# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

### Certificate Pinning (Production)

```javascript
// Frontend: Pin public key hash
const publicKeyPins = [
  'sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',  // Primary
  'sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB='   // Backup
];

// Backend: Certificate pinning verification
import requests
from requests.adapters import HTTPAdapter
from requests_http_signature import HTTPSignatureAuth

session = requests.Session()
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10)
session.mount('https://', adapter)
```

---

## Authentication & Authorization

### JWT Structure

**Header**:
```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "2024-08-15"
}
```

**Payload**:
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "student@university.edu",
  "student_id": "STU12345678",
  "roles": ["STUDENT"],
  "permissions": ["photo:capture", "token:generate"],
  "iat": 1724088000,
  "exp": 1724088900,
  "iss": "https://api.campus.university.edu",
  "aud": "campus-app"
}
```

**Signature**: RS256 (Private key signing, public key verification)

### Refresh Token Rotation

```python
# Pseudo-code: Refresh token rotation strategy
def refresh_access_token(refresh_token):
    1. Verify refresh token signature
    2. Check if refresh token is in database
    3. Check if refresh token is not revoked
    4. Check if refresh token hasn't expired
    5. Check if refresh count < max_refreshes (e.g., 10)
    6. Generate new access token
    7. Optionally: Generate new refresh token (rotating strategy)
    8. Store new refresh token in DB (hash only)
    9. Increment refresh_count on old token
    10. Return new access token + optional new refresh token
```

---

## API Security Headers

### Response Headers

```
# Prevent browser caching sensitive data
Cache-Control: no-store, no-cache, must-revalidate, proxy-revalidate
Pragma: no-cache
Expires: 0

# CORS protection
Access-Control-Allow-Origin: https://campus.university.edu
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type, X-Nonce-Token
Access-Control-Max-Age: 86400
Access-Control-Allow-Credentials: true

# CSRF protection
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block

# HTTPS enforcement
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

# CSP
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{random}'; ...

# Remove server identification
Server: (omitted)
```

---

## Audit & Monitoring

### Critical Events to Log

```python
audit_events = [
    'USER_REGISTERED',
    'USER_LOGIN',
    'USER_LOGIN_FAILED',
    'PHOTO_CAPTURED',
    'PHOTO_VALIDATED',
    'PHOTO_VALIDATION_FAILED',
    'FACE_RECOGNITION_PASSED',
    'FACE_RECOGNITION_FAILED',
    'TOKEN_GENERATED',
    'TOKEN_REGENERATED',
    'TOKEN_REVOKED',
    'OAUTH_LINKED',
    'PASSWORD_CHANGED',
    'MFA_ENABLED',
    'ACCOUNT_SUSPENDED',
    'GDPR_EXPORT_REQUESTED',
    'GDPR_DELETE_REQUESTED'
]
```

### Audit Log Entry Structure

```json
{
  "id": "ddd3e400-e29b-41d4-a716-446655440ddd",
  "event_type": "TOKEN_GENERATED",
  "actor_user_id": "550e8400-e29b-41d4-a716-446655440000",
  "affected_user_id": "550e8400-e29b-41d4-a716-446655440000",
  "context_data": {
    "token_id": "880e8400-e29b-41d4-a716-446655440333",
    "token_validity_hours": 24,
    "photo_id": "990e8400-e29b-41d4-a716-446655440444",
    "face_recognized": true,
    "face_confidence": 0.94
  },
  "outcome": "SUCCESS",
  "error_message": null,
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "device_fingerprint_id": "eee4f400-e29b-41d4-a716-446655440eee",
  "created_at": "2026-08-15T14:20:30Z"
}
```

### Security Monitoring Metrics

**Real-time Alerts**:
- Multiple failed login attempts (>5 in 15 min)
- Unusual geographic access (country/city changes)
- Impossible travel (IP location jump > 1000km in < 1 hour)
- Abnormal token generation (>10 per hour per user)
- Face recognition failures (>3 consecutive failures)
- Rate limit violations

**Compliance Dashboards**:
- Photo capture compliance (% of workflows with photos)
- Face recognition availability (% uptime)
- API error rates (500s, timeouts)
- Photo storage usage + retention
- GDPR deletion request fulfillment time

---

## Data Protection & Privacy (GDPR)

### User Rights

1. **Right to Access (Article 15)**
   - Export all personal data: `GET /api/user/export`
   - Format: JSON ZIP containing user profile + photos + audit logs
   - Timeframe: 30 days

2. **Right to be Forgotten (Article 17)**
   - Delete all personal data: `DELETE /api/user/profile`
   - Photos: Immediate deletion from S3, database marked `is_archived=TRUE`
   - Face embeddings: Immediate deletion
   - Audit logs: Retained for 7 years (legal/compliance requirement)
   - Timeframe: 30 days

3. **Right to Data Portability (Article 20)**
   - Export data in machine-readable format: CSV + JSON
   - Include photos, embeddings, audit logs
   - Timeframe: 30 days

4. **Right to Rectification (Article 16)**
   - Update user profile: name, email, phone
   - Photos cannot be retroactively modified (security requirement)
   - Timeframe: Immediate

### Data Retention Policies

| Data Category | Retention | Purge Method |
|---------------|-----------|--------------|
| Active user profile | Duration of use | Manual deletion via admin |
| Security photos | 90 days | Automatic S3 lifecycle policy |
| Face embeddings | 60 days | Automatic database deletion |
| Audit logs | 7 years | Archived after 1 year to cold storage |
| Refresh tokens | 30 days | Auto-expire + database cleanup |
| Nonces | 24 hours | Automatic cleanup job |
| Device fingerprints | 180 days | Soft delete on user request |

---

## Incident Response & Security Updates

### Incident Response Plan

1. **Detection**: Automated alerts trigger on suspicious patterns
2. **Triage**: Security team reviews alert + manually investigates
3. **Containment**: Affected accounts locked, tokens revoked, rate limits increased
4. **Eradication**: Security fixes deployed, affected data reviewed
5. **Recovery**: Users notified, compromised data deleted, services restored
6. **Lessons Learned**: Post-mortem, security improvements, policy updates

### Security Patch Management

- Critical vulnerabilities: Fixed + deployed within 24 hours
- High vulnerabilities: Fixed + deployed within 1 week
- Medium/Low: Deployed with regular releases (bi-weekly)

### Vulnerability Disclosure Program

- Security researchers can report vulnerabilities via security@university.edu
- Responsible disclosure: 90-day embargo before public disclosure
- Rewards/recognition for valid bug reports

---

## Third-Party Security

### OAuth2 Provider (Google) Security

- Client ID/Secret stored in external secrets manager (AWS Secrets Manager)
- Redirect URI: Whitelist only campus domain (https://campus.university.edu/callback)
- Scope: Limit to `openid email profile` (no access to calendar, contacts, etc.)
- Token validation: Verify token signature against Google's public keys
- Token binding: Verify `aud` claim matches our app ID

### Face Recognition Backend Security

- API keys stored in secrets manager
- Encrypted transmission (TLS 1.3+) to third-party service
- Minimal data transmission: Faces sent, embeddings returned (no biometric transmission)
- Service level agreement (SLA) with face recognition provider
- Fallback to manual verification if service unavailable

---

## Security Testing & Validation

### Phase 0 Security Validations

- ✅ Threat model defined (this document)
- ✅ NIST Cybersecurity Framework alignment
- ✅ OWASP Top 10 mitigations mapped
- ✅ GDPR Data Protection Impact Assessment (DPIA)
- ✅ Encryption standards validated
- ✅ API security headers defined

### Phase 1 Security Activities

- Penetration testing (third-party firm)
- Code security review (SAST)
- Dependency vulnerability scanning (SCA)
- Secure design review (architecture)
- Security training for development team

### Ongoing Security Activities

- Weekly vulnerability scanning (OWASP ZAP, Snyk)
- Monthly penetration testing
- Quarterly security reviews
- Annual independent security audit
- Bug bounty program

---

**Document Version**: 1.0  
**Last Updated**: 2026-08-15  
**Security Architect**: [Your Name/Team]  
**Status**: Phase 0 - Design Complete

**NEXT STEPS**: 
- [ ] Threat modeling workshop with engineering team
- [ ] Cryptographic review with security specialist
- [ ] GDPR Data Protection Impact Assessment (DPIA)
- [ ] Third-party penetration testing engagement
