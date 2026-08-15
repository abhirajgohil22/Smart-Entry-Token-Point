# Smart Campus Token Management - Live Photo Capture Design

## Live Photo Capture Architecture

The live photo capture mechanism is the **foundational security layer** of the entire Smart Campus Token Management System. Every one of the four critical workflows (REGISTRATION, LOGIN, TOKEN_GENERATION, TOKEN_REGENERATION) is gated by this mechanism.

---

## Core Live Photo Capture Flow

### Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER BROWSER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. REQUEST NONCE                                              │
│  ┌─────────────────┐                                           │
│  │ Server generates │                                           │
│  │ unique nonce +   │                                           │
│  │ timestamp        │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  2. DISPLAY VIDEO STREAM                                       │
│  ┌────────────────────────┐                                   │
│  │ navigator.mediaDevices │                                   │
│  │ .getUserMedia({        │                                   │
│  │   video: true,         │                                   │
│  │   audio: false         │                                   │
│  │ })                     │                                   │
│  │                        │                                   │
│  │ Display in <video>     │                                   │
│  │ element (live stream)  │                                   │
│  └────────┬───────────────┘                                   │
│           │                                                     │
│           ▼                                                     │
│  3. USER CAPTURES FRAME                                        │
│  ┌────────────────────────┐                                   │
│  │ User clicks [Capture]  │                                   │
│  │ button at desired      │                                   │
│  │ moment                 │                                   │
│  └────────┬───────────────┘                                   │
│           │                                                     │
│           ▼                                                     │
│  4. EXTRACT FRAME TO CANVAS                                    │
│  ┌────────────────────────────────────────┐                 │
│  │ const canvas = ...                     │                 │
│  │ const ctx = canvas.getContext('2d')   │                 │
│  │ ctx.drawImage(videoElement, 0, 0)    │                 │
│  │                                        │                 │
│  │ [Canvas now contains current frame]   │                 │
│  └────────┬─────────────────────────────┘                 │
│           │                                                   │
│           ▼                                                   │
│  5. BLOB CONVERSION                                            │
│  ┌────────────────────────────────────────┐                 │
│  │ canvas.toBlob((blob) => {              │                 │
│  │   // blob = JPEG/PNG binary data      │                 │
│  │   // size checked (100KB - 5MB)        │                 │
│  │   // dimensions checked (320x240+)     │                 │
│  │ }, 'image/jpeg', 0.9)                 │                 │
│  └────────┬─────────────────────────────┘                 │
│           │                                                   │
│           ▼                                                   │
│  6. HASH & SIGN                                                │
│  ┌────────────────────────────────────────┐                 │
│  │ const photoHash = SHA256(blob)         │                 │
│  │ const timestamp = new Date().toISO()   │                 │
│  │ const clientHash =                     │                 │
│  │   SHA256(nonce + timestamp +           │                 │
│  │   deviceFingerprint + photoHash)       │                 │
│  └────────┬─────────────────────────────┘                 │
│           │                                                   │
│           ▼                                                   │
│  7. MULTIPART FORM ASSEMBLY                                   │
│  ┌──────────────────────────────────────────┐               │
│  │ const formData = new FormData()          │               │
│  │ formData.append('photo', blob,           │               │
│  │   'photo.jpg')                           │               │
│  │ formData.append('nonce_token', nonce)    │               │
│  │ formData.append('photo_timestamp',       │               │
│  │   timestamp)                             │               │
│  │ formData.append('device_fingerprint',    │               │
│  │   deviceHash)                            │               │
│  │ formData.append('client_hash',           │               │
│  │   clientHash)                            │               │
│  └────────┬─────────────────────────────────┘               │
│           │                                                   │
│           ▼                                                   │
│  8. HTTPS POST REQUEST                                        │
│  ┌────────────────────────────────┐                         │
│  │ POST /api/auth/login/photo     │                         │
│  │ Content-Type: multipart/form   │                         │
│  │ Authorization: Bearer (if auth)│                         │
│  │ X-Client-Hash: <hash>          │                         │
│  └────────┬───────────────────────┘                         │
│           │                                                   │
└───────────┼──────────────────────────────────────────────────┘
            │
            │ ═══════════════════════════════════════════════════
            │                    TLS 1.3+ Encryption
            │ ═══════════════════════════════════════════════════
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND SERVER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  9. RECEIVE MULTIPART REQUEST                                  │
│  ┌────────────────────────────────────────┐                 │
│  │ Parse multipart form data              │                 │
│  │ Extract photo blob binary              │                 │
│  │ Read metadata fields                   │                 │
│  └────────┬─────────────────────────────┘                 │
│           │                                                   │
│           ▼                                                   │
│  10. VALIDATE REQUEST                                         │
│  ┌────────────────────────────────────────────────┐          │
│  │ 1. Check authorization header                 │          │
│  │ 2. Verify JWT signature (if authenticated)    │          │
│  │ 3. Extract user_id from JWT claims            │          │
│  └────────┬─────────────────────────────────────┘          │
│           │                                                   │
│           ▼                                                   │
│  11. NONCE VALIDATION                                         │
│  ┌──────────────────────────────────────────────┐           │
│  │ 1. Query nonces table: WHERE                 │           │
│  │    nonce_value = provided_nonce              │           │
│  │ 2. Check: nonce NOT expired                  │           │
│  │    (now < expires_at)                        │           │
│  │ 3. Check: nonce NOT previously used          │           │
│  │    (is_used = FALSE)                         │           │
│  │ 4. Mark nonce as used: UPDATE nonces         │           │
│  │    SET is_used = TRUE                        │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  12. DEVICE FINGERPRINT VALIDATION                           │
│  ┌──────────────────────────────────────────────┐           │
│  │ 1. Recompute device fingerprint from         │           │
│  │    request context:                          │           │
│  │    - User-Agent header                       │           │
│  │    - IP address                              │           │
│  │    - Accept-Language header                  │           │
│  │    - Other browser characteristics           │           │
│  │ 2. Compare with client-provided              │           │
│  │    deviceFingerprint                         │           │
│  │ 3. Check: If mismatch, flag for manual       │           │
│  │    review                                    │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  13. TIMESTAMP FRESHNESS CHECK                              │
│  ┌──────────────────────────────────────────────┐           │
│  │ 1. Parse photo_timestamp from request        │           │
│  │ 2. Verify: nonce_generated_at <             │           │
│  │    photo_timestamp < now                     │           │
│  │ 3. Check: photo_timestamp within             │           │
│  │    ±30 seconds of server time (clock skew)  │           │
│  │ 4. Verify: now < nonce_expires_at            │           │
│  │    (within 5-min nonce window)               │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  14. PHOTO FILE VALIDATION                                   │
│  ┌──────────────────────────────────────────────┐           │
│  │ 1. Check MIME type: image/jpeg or image/png │           │
│  │ 2. Verify magic bytes:                       │           │
│  │    - JPEG: FFD8FF...                         │           │
│  │    - PNG: 89504E47...                        │           │
│  │ 3. Check file size:                          │           │
│  │    100KB (min) - 5MB (max)                   │           │
│  │ 4. Parse image dimensions:                   │           │
│  │    Minimum 320x240 pixels                    │           │
│  │    Maximum 8000x8000 pixels                  │           │
│  │ 5. Verify image integrity (no corruption)   │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  15. CLIENT HASH VERIFICATION                               │
│  ┌──────────────────────────────────────────────┐           │
│  │ 1. Recalculate: photoHash =                 │           │
│  │    SHA256(photo_blob)                        │           │
│  │ 2. Recalculate: serverHash =                │           │
│  │    SHA256(nonce + timestamp +                │           │
│  │    deviceFingerprint + photoHash)            │           │
│  │ 3. Compare with client-provided              │           │
│  │    client_hash                               │           │
│  │ 4. If mismatch: REJECT (tampering detected) │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  16. OPTIONAL FACE DETECTION                                │
│  ┌──────────────────────────────────────────────┐           │
│  │ IF FACE_RECOGNITION_ENABLED = True:          │           │
│  │  1. Load face recognition model              │           │
│  │  2. Detect faces in image                    │           │
│  │  3. Check: Exactly 1 face detected           │           │
│  │  4. Check: Face fills ~50% of image          │           │
│  │  5. Generate face_embedding vector           │           │
│  │  ELSE:                                       │           │
│  │  Skip face processing (optional feature)     │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  17. OPTIONAL LIVENESS DETECTION                            │
│  ┌──────────────────────────────────────────────┐           │
│  │ IF FACE_RECOGNITION_ENABLED = True:          │           │
│  │  1. Analyze temporal motion patterns         │           │
│  │     from video stream (if available)         │           │
│  │  2. Check for micro-expressions              │           │
│  │  3. Detect spoofing artifacts                │           │
│  │  4. Generate liveness_confidence score       │           │
│  │  5. Require: liveness_confidence > 0.85      │           │
│  │  ELSE:                                       │           │
│  │  Skip liveness check (optional feature)      │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  18. OPTIONAL IDENTITY VERIFICATION                         │
│  ┌──────────────────────────────────────────────┐           │
│  │ IF FACE_RECOGNITION_ENABLED = True:          │           │
│  │  1. Query user's enrollment photos           │           │
│  │  2. Compare current embedding vs.            │           │
│  │     stored enrollment embeddings             │           │
│  │  3. Calculate similarity distance            │           │
│  │  4. If similarity > threshold (0.60):        │           │
│  │     face_match = TRUE                        │           │
│  │  5. For LOGIN/TOKEN: Require match           │           │
│  │  6. For REGISTRATION: Optional (not req.)    │           │
│  │  ELSE:                                       │           │
│  │  Skip identity matching (optional feature)   │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  19. STORE PHOTO IN S3                                       │
│  ┌──────────────────────────────────────────────┐           │
│  │ 1. Generate unique photo ID (UUID)           │           │
│  │ 2. Encrypt blob:                             │           │
│  │    - Fetch KMS master key                    │           │
│  │    - Generate random IV (96 bits)            │           │
│  │    - Encrypt with AES-256-GCM                │           │
│  │ 3. Upload to S3:                             │           │
│  │    s3://campus-photos/                       │           │
│  │    {user_id}/{photo_id}.jpg.enc              │           │
│  │ 4. Verify upload complete (ETag match)       │           │
│  │ 5. Store S3 key in database                  │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  20. CREATE SECURITY_PHOTO RECORD                           │
│  ┌──────────────────────────────────────────────┐           │
│  │ INSERT INTO security_photos (                │           │
│  │   id = UUID,                                 │           │
│  │   user_id = authenticated_user_id,           │           │
│  │   workflow_event = 'LOGIN',                  │           │
│  │   photo_blob_s3_key = 's3://...',            │           │
│  │   photo_file_size_bytes = size,              │           │
│  │   photo_mime_type = 'image/jpeg',            │           │
│  │   photo_dimensions = {width, height},        │           │
│  │   nonce_value = nonce,                       │           │
│  │   photo_captured_at = timestamp,             │           │
│  │   nonce_valid = TRUE,                        │           │
│  │   timestamp_valid = TRUE,                    │           │
│  │   fingerprint_valid = TRUE/FALSE,            │           │
│  │   validation_status = 'VALIDATED',           │           │
│  │   face_recognized = TRUE/FALSE,              │           │
│  │   liveness_confidence = score,               │           │
│  │   created_at = NOW()                         │           │
│  │ )                                            │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  21. OPTIONAL FACE EMBEDDING STORAGE                        │
│  ┌──────────────────────────────────────────────┐           │
│  │ IF FACE_RECOGNITION_ENABLED = True:          │           │
│  │  1. Create face_recognition_results record  │           │
│  │  2. Store embedding vector (512-dim)        │           │
│  │  3. Encrypt embedding + store in DB          │           │
│  │  4. Link embedding to photo via foreign key │           │
│  │  ELSE:                                       │           │
│  │  Skip embedding storage (optional feature)  │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  22. CREATE AUDIT LOG ENTRY                                 │
│  ┌──────────────────────────────────────────────┐           │
│  │ INSERT INTO audit_logs (                     │           │
│  │   event_type = 'PHOTO_CAPTURED',             │           │
│  │   actor_user_id = user_id,                   │           │
│  │   affected_user_id = user_id,                │           │
│  │   affected_photo_id = photo_id,              │           │
│  │   context_data = {                           │           │
│  │     workflow_event: 'LOGIN',                 │           │
│  │     validation_status: 'VALIDATED',          │           │
│  │     face_recognized: true,                   │           │
│  │     liveness_confidence: 0.94                │           │
│  │   },                                         │           │
│  │   outcome = 'SUCCESS',                       │           │
│  │   ip_address = client_ip,                    │           │
│  │   user_agent = request.headers['User-Agent'] │           │
│  │ )                                            │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  23. PROCEED TO NEXT WORKFLOW STEP                          │
│  ┌──────────────────────────────────────────────┐           │
│  │ Photo validation complete + successful       │           │
│  │                                              │           │
│  │ For LOGIN: Generate JWT access token        │           │
│  │ For TOKEN_GENERATION: Generate campus token │           │
│  │ For REGISTRATION: Send email verification   │           │
│  │ For TOKEN_REGENERATION: Generate new token  │           │
│  └────────┬─────────────────────────────────────┘           │
│           │                                                   │
│           ▼                                                   │
│  24. RETURN SUCCESS RESPONSE                                │
│  ┌──────────────────────────────────────────────┐           │
│  │ HTTP 200 OK / 201 CREATED                    │           │
│  │ {                                            │           │
│  │   "success": true,                           │           │
│  │   "photo": {                                 │           │
│  │     "id": "...",                             │           │
│  │     "validation_status": "VALIDATED"         │           │
│  │   },                                         │           │
│  │   "next_step": "..."                         │           │
│  │ }                                            │           │
│  └────────────────────────────────────────────────┘           │
│                                                               │
└───────────────────────────────────────────────────────────────┘
            │
            │ ═══════════════════════════════════════════════════
            │             TLS 1.3+ Encryption Response
            │ ═══════════════════════════════════════════════════
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       USER BROWSER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  25. RECEIVE SUCCESS RESPONSE                                  │
│  ┌────────────────────────────────────────┐                 │
│  │ Parse JSON response                    │                 │
│  │ Update UI to show photo validated      │                 │
│  │ Proceed to next workflow step          │                 │
│  │ (e.g., generate token, display QR)     │                 │
│  └────────────────────────────────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Photo Capture Implementation Details

### Client-Side (JavaScript/TypeScript)

#### 1. Request Nonce

```javascript
async function requestNonce(workflowEvent) {
  const response = await fetch('/api/auth/nonce/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      workflow_event: workflowEvent,
      device_fingerprint: await getDeviceFingerprint()
    })
  });
  
  if (!response.ok) throw new Error('Nonce generation failed');
  return response.json();
}

async function getDeviceFingerprint() {
  const userAgent = navigator.userAgent;
  const language = navigator.language;
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const screenResolution = `${screen.width}x${screen.height}`;
  
  const fingerprintData = {
    user_agent: userAgent,
    language,
    timezone,
    screen_resolution: screenResolution
  };
  
  const fingerprintString = JSON.stringify(fingerprintData);
  const hashBuffer = await crypto.subtle.digest('SHA-256', 
    new TextEncoder().encode(fingerprintString));
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
```

#### 2. Request Camera Permission & Display Video Stream

```javascript
async function initializeCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'user'
      },
      audio: false
    });
    
    const videoElement = document.getElementById('camera-stream');
    videoElement.srcObject = stream;
    
    return stream;
  } catch (error) {
    if (error.name === 'NotAllowedError') {
      alert('Camera permission denied. Cannot proceed without camera access.');
    } else if (error.name === 'NotFoundError') {
      alert('No camera device found. Please attach a camera and try again.');
    }
    throw error;
  }
}
```

#### 3. Capture Frame to Canvas

```javascript
function capturePhotoFromVideo(videoElement) {
  const canvas = document.createElement('canvas');
  canvas.width = videoElement.videoWidth;
  canvas.height = videoElement.videoHeight;
  
  const context = canvas.getContext('2d');
  context.drawImage(videoElement, 0, 0);
  
  return { canvas, width: canvas.width, height: canvas.height };
}
```

#### 4. Convert Canvas to Blob

```javascript
async function canvasToBlob(canvas, quality = 0.9) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) reject(new Error('Failed to create blob'));
        
        // Validate blob size
        const minSize = 100 * 1024;    // 100 KB
        const maxSize = 5 * 1024 * 1024; // 5 MB
        
        if (blob.size < minSize || blob.size > maxSize) {
          reject(new Error(
            `Photo size ${blob.size} bytes out of range [${minSize}, ${maxSize}]`
          ));
        }
        
        resolve(blob);
      },
      'image/jpeg',
      quality
    );
  });
}
```

#### 5. Calculate Client-Side Hash

```javascript
async function calculatePhotoHash(photoBlob) {
  const buffer = await photoBlob.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function calculateClientHash(nonceToken, timestamp, deviceFingerprint, photoHash) {
  const hashInput = `${nonceToken}${timestamp}${deviceFingerprint}${photoHash}`;
  const buffer = new TextEncoder().encode(hashInput);
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
```

#### 6. Assemble Multipart FormData

```javascript
async function assemblePhotoForm(
  photoBlob,
  nonceToken,
  deviceFingerprint,
  additionalFields = {}
) {
  const timestamp = new Date().toISOString();
  const photoHash = await calculatePhotoHash(photoBlob);
  const clientHash = await calculateClientHash(
    nonceToken,
    timestamp,
    deviceFingerprint,
    photoHash
  );
  
  const formData = new FormData();
  formData.append('photo', photoBlob, 'photo.jpg');
  formData.append('nonce_token', nonceToken);
  formData.append('photo_timestamp', timestamp);
  formData.append('device_fingerprint_hash', deviceFingerprint);
  formData.append('client_hash', clientHash);
  
  // Add workflow-specific fields
  Object.entries(additionalFields).forEach(([key, value]) => {
    formData.append(key, value);
  });
  
  return formData;
}
```

#### 7. Submit Photo via HTTPS POST

```javascript
async function submitPhoto(
  endpoint,
  formData,
  accessToken = null
) {
  const headers = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  
  const response = await fetch(endpoint, {
    method: 'POST',
    headers,
    body: formData,
    credentials: 'include' // Include cookies for HttpOnly refresh token
  });
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(
      `Photo submission failed: ${errorData.error} - ${errorData.message}`
    );
  }
  
  return response.json();
}
```

#### 8. Complete Client Flow Example

```javascript
async function performLivePhotoCapture(workflowEvent) {
  try {
    // Step 1: Request nonce
    const { nonce_token, device_fingerprint_hash } = 
      await requestNonce(workflowEvent);
    
    // Step 2: Initialize camera
    const stream = await initializeCamera();
    
    // Step 3: Wait for user to click Capture button
    const photoBlob = await waitForUserCapture();
    
    // Step 4-5: Convert to blob + calculate hash (done in photoCapture)
    const deviceFingerprint = device_fingerprint_hash;
    
    // Step 6: Assemble form
    const formData = await assemblePhotoForm(
      photoBlob,
      nonce_token,
      deviceFingerprint,
      { workflow_event: workflowEvent }
    );
    
    // Step 7: Submit photo
    const result = await submitPhoto(
      `/api/auth/login/photo`, // or /api/tokens/generate/photo, etc.
      formData,
      getAccessToken() // if authenticated
    );
    
    // Stop camera stream
    stream.getTracks().forEach(track => track.stop());
    
    // Success!
    console.log('Photo validated:', result);
    return result;
    
  } catch (error) {
    console.error('Photo capture failed:', error);
    // Show error message to user
    throw error;
  }
}
```

---

### Server-Side (Python/Django)

#### 1. Nonce Validation

```python
from django.utils import timezone
from datetime import timedelta
from apps.photos.models import Nonce

def validate_nonce(nonce_value, device_fingerprint_hash, request):
    """
    Validate nonce for freshness, usage, and device match
    """
    try:
        nonce_obj = Nonce.objects.get(nonce_value=nonce_value)
    except Nonce.DoesNotExist:
        raise ValidationError("Invalid nonce token")
    
    # Check expiration
    if timezone.now() > nonce_obj.expires_at:
        raise ValidationError("Nonce token has expired")
    
    # Check if already used
    if nonce_obj.is_used:
        # Log suspicious activity
        logger.warning(f"Nonce reuse attempt: {nonce_value} by {request.user}")
        raise ValidationError("Nonce token has already been used")
    
    # Device fingerprint must match
    if nonce_obj.device_fingerprint_hash != device_fingerprint_hash:
        logger.warning(f"Device fingerprint mismatch for nonce: {nonce_value}")
        # Don't immediately fail - could be legitimate variation
        # Just log and continue with warning
    
    # Mark as used
    nonce_obj.is_used = True
    nonce_obj.used_at = timezone.now()
    nonce_obj.save()
    
    return True
```

#### 2. Timestamp Freshness Validation

```python
from datetime import timedelta

def validate_timestamp_freshness(photo_timestamp_str, nonce_obj, clock_skew_seconds=30):
    """
    Ensure photo was captured during nonce validity window
    """
    try:
        photo_timestamp = datetime.fromisoformat(photo_timestamp_str)
    except ValueError:
        raise ValidationError("Invalid timestamp format")
    
    now = timezone.now()
    
    # Photo must be captured after nonce generation
    if photo_timestamp < nonce_obj.issued_at:
        raise ValidationError("Photo timestamp predates nonce generation")
    
    # Photo must be captured before nonce expiry
    if photo_timestamp > nonce_obj.expires_at:
        raise ValidationError("Photo timestamp is after nonce expiry")
    
    # Allow clock skew for client/server time differences
    if abs((now - photo_timestamp).total_seconds()) > clock_skew_seconds:
        raise ValidationError(
            f"Photo timestamp is too far from current time "
            f"(difference: {abs((now - photo_timestamp).total_seconds())} seconds)"
        )
    
    return True
```

#### 3. Photo File Validation

```python
import imghdr
import io
from PIL import Image

def validate_photo_file(photo_blob, max_size_mb=5, min_size_kb=100):
    """
    Validate photo format, size, and dimensions
    """
    min_size_bytes = min_size_kb * 1024
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Check file size
    if len(photo_blob) < min_size_bytes:
        raise ValidationError(
            f"Photo too small ({len(photo_blob)} bytes). "
            f"Minimum: {min_size_bytes} bytes"
        )
    if len(photo_blob) > max_size_bytes:
        raise ValidationError(
            f"Photo too large ({len(photo_blob)} bytes). "
            f"Maximum: {max_size_bytes} bytes"
        )
    
    # Check MIME type
    file_type = imghdr.what(None, h=photo_blob[:32])
    if file_type not in ['jpeg', 'png']:
        raise ValidationError(f"Invalid file type: {file_type}")
    
    # Verify magic bytes
    if file_type == 'jpeg' and photo_blob[:2] != b'\xff\xd8':
        raise ValidationError("JPEG magic bytes invalid")
    if file_type == 'png' and photo_blob[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValidationError("PNG magic bytes invalid")
    
    # Check image dimensions
    try:
        img = Image.open(io.BytesIO(photo_blob))
        width, height = img.size
        
        if width < 320 or height < 240:
            raise ValidationError(
                f"Image dimensions too small ({width}x{height}). "
                f"Minimum: 320x240"
            )
        if width > 8000 or height > 8000:
            raise ValidationError(
                f"Image dimensions too large ({width}x{height}). "
                f"Maximum: 8000x8000"
            )
        
        img.close()
    except Exception as e:
        raise ValidationError(f"Failed to parse image: {str(e)}")
    
    return {'width': width, 'height': height, 'format': file_type}
```

#### 4. Client Hash Verification

```python
import hashlib

def verify_client_hash(nonce_token, photo_timestamp_str, device_fingerprint_hash, photo_blob, provided_client_hash):
    """
    Recompute client hash server-side and verify integrity
    """
    # Compute photo hash from blob
    photo_hash = hashlib.sha256(photo_blob).hexdigest()
    
    # Recompute client hash using same algorithm as client
    hash_input = f"{nonce_token}{photo_timestamp_str}{device_fingerprint_hash}{photo_hash}"
    expected_client_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    
    if expected_client_hash != provided_client_hash:
        logger.warning(f"Client hash mismatch detected. Possible tampering.")
        raise ValidationError("Photo integrity check failed (hash mismatch)")
    
    return True
```

#### 5. Optional Face Liveness Detection

```python
import os
from apps.face_recognition.services import FaceRecognitionService

def check_face_liveness(photo_blob):
    """
    Optional: Detect if face in photo is live (not spoofed/deepfaked)
    Only runs if FACE_RECOGNITION_ENABLED = True
    """
    if not settings.FACE_RECOGNITION_ENABLED:
        return None  # Skip if feature disabled
    
    try:
        face_service = FaceRecognitionService()
        result = face_service.detect_liveness(photo_blob)
        
        liveness_confidence = result.get('liveness_confidence', 0.0)
        
        if liveness_confidence < 0.70:
            raise ValidationError(
                f"Face liveness check failed (confidence: {liveness_confidence:.2f}). "
                f"Please ensure you are looking at the camera."
            )
        
        return {
            'liveness_detected': True,
            'liveness_confidence': liveness_confidence,
            'algorithm': 'deepface_liveness_detector'
        }
    except ImportError:
        logger.warning("Face recognition libraries not installed. Skipping liveness check.")
        return None
    except Exception as e:
        logger.error(f"Face liveness detection failed: {str(e)}")
        # Don't fail - gracefully degrade to single-factor verification
        return None
```

#### 6. Store Photo in S3

```python
import boto3
import uuid
from django.conf import settings
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import os as crypto_os

def store_photo_in_s3(photo_blob, user_id):
    """
    Encrypt and upload photo to S3
    """
    # Generate unique photo ID
    photo_id = str(uuid.uuid4())
    
    # Get KMS client and master key
    kms_client = boto3.client('kms')
    master_key_id = settings.AWS_KMS_MASTER_KEY_ID
    
    # Generate data encryption key from KMS
    dek_response = kms_client.generate_data_key(
        KeyId=master_key_id,
        KeySpec='AES_256'
    )
    plaintext_key = dek_response['Plaintext']
    encrypted_key = dek_response['CiphertextBlob']
    
    # Encrypt photo blob
    iv = crypto_os.urandom(12)  # 96-bit IV for GCM
    cipher = AESGCM(plaintext_key)
    ciphertext = cipher.encrypt(iv, photo_blob, None)
    
    # Upload to S3
    s3_client = boto3.client('s3')
    s3_key = f"{user_id}/{photo_id}.jpg.enc"
    
    try:
        s3_client.put_object(
            Bucket=settings.AWS_S3_PHOTOS_BUCKET,
            Key=s3_key,
            Body=iv + ciphertext,  # Prepend IV for decryption later
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=master_key_id,
            Metadata={
                'encrypted-key': encrypted_key.hex(),
                'original-size': str(len(photo_blob))
            }
        )
    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise
    
    return {
        'photo_id': photo_id,
        's3_key': s3_key,
        'encrypted_key': encrypted_key.hex(),
        'iv': iv.hex()
    }
```

#### 7. Create SecurityPhoto Record

```python
from apps.photos.models import SecurityPhoto

def create_security_photo_record(
    user_id,
    workflow_event,
    s3_key,
    photo_blob,
    photo_metadata,
    nonce_value,
    photo_timestamp,
    device_fingerprint_id,
    client_ip,
    user_agent,
    face_liveness_result=None,
    face_identity_result=None
):
    """
    Create SecurityPhoto database record
    """
    security_photo = SecurityPhoto.objects.create(
        user_id=user_id,
        workflow_event=workflow_event,
        photo_blob_s3_key=s3_key,
        photo_file_size_bytes=len(photo_blob),
        photo_mime_type='image/jpeg',
        photo_dimensions_width=photo_metadata['width'],
        photo_dimensions_height=photo_metadata['height'],
        encryption_algorithm='AES-256-GCM',
        encryption_key_id=settings.AWS_KMS_MASTER_KEY_ID,
        photo_content_hash=hashlib.sha256(photo_blob).hexdigest(),
        nonce_value=nonce_value,
        nonce_generated_at=...,  # from nonce object
        nonce_expires_at=...,    # from nonce object
        photo_captured_at=photo_timestamp,
        device_fingerprint_id=device_fingerprint_id,
        client_user_agent=user_agent,
        client_ip_address=client_ip,
        nonce_valid=True,
        timestamp_valid=True,
        fingerprint_valid=True,
        validation_status='VALIDATED',
        face_recognized=face_liveness_result is not None and face_liveness_result['liveness_confidence'] > 0.85,
        processed_at=timezone.now()
    )
    
    return security_photo
```

---

## Photo Capture Constraints & Specifications

### Client-Side Constraints (Enforced by UI)

| Constraint | Implementation |
|-----------|-----------------|
| Photo source = Live video only | Canvas drawing ONLY from `<video>` element |
| No file picker access | Input type="file" disabled during capture flow |
| No gallery/clipboard | JavaScript prevents copy/paste of images |
| Camera required | Flow blocked if `getUserMedia()` denied |
| Single frame capture | Only one frame extracted from video stream |

### Server-Side Validations (Enforced by API)

| Validation | Requirement |
|-----------|------------|
| MIME type | image/jpeg OR image/png only |
| Magic bytes | JPEG: FFD8FF... / PNG: 89504E47... |
| File size | 100 KB min, 5 MB max |
| Dimensions | 320x240 min, 8000x8000 max |
| Nonce freshness | Nonce must be unused + not expired |
| Timestamp window | Photo timestamp must fall within nonce validity period |
| Client hash | Computed hash must match photo blob integrity |
| Device fingerprint | Must match nonce issuance device (with tolerance) |

---

## Photo Retention & Deletion

### Automatic Retention Policy

```python
from django.utils import timezone
from datetime import timedelta

def purge_expired_photos():
    """
    Automatic daily task to purge photos older than retention period
    """
    retention_period = timedelta(days=90)
    cutoff_date = timezone.now() - retention_period
    
    # Find photos to delete
    photos_to_delete = SecurityPhoto.objects.filter(
        created_at__lt=cutoff_date,
        is_archived=False
    )
    
    for photo in photos_to_delete:
        # Delete from S3
        s3_client = boto3.client('s3')
        try:
            s3_client.delete_object(
                Bucket=settings.AWS_S3_PHOTOS_BUCKET,
                Key=photo.photo_blob_s3_key
            )
        except Exception as e:
            logger.error(f"Failed to delete S3 object: {str(e)}")
        
        # Delete from database
        photo.is_archived = True
        photo.archived_at = timezone.now()
        photo.save()
        
        logger.info(f"Purged photo {photo.id} (user: {photo.user_id})")
```

### User-Initiated Deletion (GDPR)

```python
def delete_user_photo(user_id, photo_id):
    """
    User requests deletion of specific photo (GDPR Right to be Forgotten)
    """
    photo = SecurityPhoto.objects.get(id=photo_id, user_id=user_id)
    
    # Schedule for deletion (allow recovery window)
    photo.is_archived = True
    photo.archived_at = timezone.now()
    photo.retention_policy_expires_at = timezone.now() + timedelta(days=7)
    photo.save()
    
    # Send confirmation email
    send_deletion_scheduled_email(user_id, photo_id)
    
    # Schedule background task for permanent deletion after 7 days
    schedule_permanent_photo_deletion(photo_id, delay=timedelta(days=7))
```

---

## Troubleshooting & Error Handling

### Common User Errors & Mitigations

| Error | User Experience | Recovery |
|-------|-----------------|----------|
| Camera permission denied | Clear message: "Camera access required" | Retry with permission granted |
| Poor lighting | Optional: Show "Better lighting recommended" hint | Allow retry |
| Multiple faces detected | Reject: "Only one face should be visible" | Retry single-face capture |
| Low liveness confidence | Reject: "Please look at camera, blink naturally" | Retry with more movement |
| Slow connection | Show spinner: "Uploading photo..." | Automatic retry on timeout |

### Server-Side Error Responses

```json
{
  "success": false,
  "error": "PHOTO_VALIDATION_FAILED",
  "message": "Live photo validation failed: Face liveness check failed (confidence: 0.42)",
  "status_code": 422,
  "details": {
    "field": "photo",
    "reason": "LIVENESS_CHECK_FAILED",
    "confidence": 0.42,
    "threshold": 0.85
  }
}
```

---

## Performance Metrics & SLAs

### Photo Capture Processing SLAs

| Step | Target Latency | Timeout |
|------|-----------------|---------|
| Nonce generation | <100ms | 5s |
| Camera initialization | <2s | 10s |
| Video stream display | <500ms (real-time) | N/A |
| Frame extraction | <100ms | 5s |
| Blob conversion | <1s | 10s |
| Multipart encoding | <100ms | 5s |
| HTTPS POST | <5s | 30s |
| Server-side validation | <2s | 10s |
| Face detection (optional) | <3s | 15s |
| S3 upload | <5s | 30s |
| Database commit | <500ms | 10s |
| **Total workflow** | **<20s** | **60s** |

---

**Document Version**: 1.0  
**Last Updated**: 2026-08-15  
**Photo Design Lead**: [Your Name/Team]  
**Status**: Phase 0 - Design Complete

**CRITICAL IMPLEMENTATION NOTES**:
- Canvas source binding enforced via CSP headers + JavaScript restrictions
- Nonce validation is non-negotiable security requirement
- Optional face recognition MUST NOT block core workflow
- All photo data encrypted at rest + in transit
- Regular photo purge required for GDPR compliance
