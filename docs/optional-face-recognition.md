# Smart Campus Token Management - Optional Face Recognition Design

## Face Recognition Philosophy

Face recognition is an **optional, feature-gated enhancement** to the core security model. The system is designed to operate with full functionality even if face recognition is completely disabled, unavailable, or fails to process.

**Core Principle**: "Live photo capture is mandatory. Face recognition is optional."

---

## Feature Gating Mechanism

### Environment Variable Control

```bash
# Enable face recognition feature
FACE_RECOGNITION_ENABLED=True
FACE_RECOGNITION_BACKEND=face_recognition_library  # or "deepface"

# Disable face recognition feature (default)
FACE_RECOGNITION_ENABLED=False
```

### Runtime Availability Check

```python
# settings.py
import importlib

def check_face_recognition_available():
    """
    Check if optional ML libraries are installed + importable
    """
    if not os.getenv('FACE_RECOGNITION_ENABLED', 'False').lower() == 'true':
        return False
    
    try:
        import face_recognition
        import cv2
        import dlib
        import numpy as np
        return True
    except ImportError as e:
        logger.warning(f"Face recognition libraries unavailable: {e}")
        return False

FACE_RECOGNITION_AVAILABLE = check_face_recognition_available()
FACE_RECOGNITION_ENABLED = (
    os.getenv('FACE_RECOGNITION_ENABLED', 'False').lower() == 'true' 
    and FACE_RECOGNITION_AVAILABLE
)
```

### Graceful Degradation Flow

```python
def process_photo_with_optional_face_recognition(photo_blob, user_id):
    """
    Process photo with optional face recognition feature
    """
    # Step 1: Always perform core photo validation (mandatory)
    try:
        photo_metadata = validate_photo_file(photo_blob)
    except ValidationError as e:
        return {
            'validation_passed': False,
            'error': str(e),
            'face_recognized': False,
            'face_error': None
        }
    
    # Step 2: Optional face recognition (graceful degradation)
    face_result = None
    if settings.FACE_RECOGNITION_ENABLED:
        try:
            face_result = perform_face_recognition(photo_blob, user_id)
        except Exception as e:
            logger.warning(f"Face recognition failed: {e}")
            face_result = {
                'face_detected': False,
                'face_error': str(e),
                'liveness_confidence': 0.0
            }
    
    # Step 3: Continue regardless of face recognition outcome
    return {
        'validation_passed': True,
        'photo_metadata': photo_metadata,
        'face_recognized': face_result is not None and face_result.get('face_detected'),
        'face_result': face_result
    }
```

---

## Face Recognition Capabilities

### 1. Face Detection

**Purpose**: Detect whether a face is present in the photo

**Implementation**:
```python
import face_recognition
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

def detect_face(photo_blob):
    """
    Detect if face exists in photo
    """
    try:
        # Load image
        image = Image.open(io.BytesIO(photo_blob)).convert('RGB')
        image_array = np.array(image)
        
        # Detect face locations
        face_locations = face_recognition.face_locations(
            image_array,
            model='hog'  # or 'cnn' for higher accuracy
        )
        
        if not face_locations:
            return {
                'face_detected': False,
                'face_count': 0,
                'face_confidence': 0.0
            }
        
        # Calculate confidence based on face size
        image_area = image_array.shape[0] * image_array.shape[1]
        face_area = 0
        for (top, right, bottom, left) in face_locations:
            face_area += (right - left) * (bottom - top)
        
        face_coverage = face_area / image_area
        face_confidence = min(face_coverage * 2, 1.0)  # 0.0-1.0
        
        return {
            'face_detected': len(face_locations) == 1,
            'face_count': len(face_locations),
            'face_confidence': face_confidence,
            'face_location': face_locations[0] if face_locations else None,
            'face_coverage_percent': face_coverage * 100
        }
    
    except Exception as e:
        logger.error(f"Face detection failed: {e}")
        raise
```

**Acceptance Criteria**:
- Exactly 1 face detected (not 0, not >1)
- Face confidence score ≥ 0.50
- Face covers ~30-80% of image area

---

### 2. Liveness Detection

**Purpose**: Verify the face is "live" (not a photo, video, or deepfake)

**Implementation**:
```python
from deepface import DeepFace

def detect_liveness(photo_blob):
    """
    Detect if face is live (not spoofed)
    Uses multiple heuristics to detect spoofing attempts
    """
    try:
        # Load image
        image_array = np.frombuffer(photo_blob, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        # Method 1: Temporal Consistency (if video stream available)
        # Check for frame-to-frame movement patterns
        temporal_consistency = check_temporal_consistency(image)
        
        # Method 2: Frequency Domain Analysis
        # Deepfakes/video recordings show different frequency signatures
        frequency_score = analyze_frequency_domain(image)
        
        # Method 3: Texture Analysis
        # Real faces have specific texture patterns
        texture_score = analyze_texture_patterns(image)
        
        # Method 4: Micro-Expression Detection
        # Real faces show involuntary micro-expressions
        micro_expression_score = detect_micro_expressions(image)
        
        # Method 5: Reflection/Pupil Analysis
        # Real eyes have specific reflection patterns
        reflection_score = analyze_eye_reflections(image)
        
        # Combine scores
        liveness_confidence = (
            (temporal_consistency * 0.20) +
            (frequency_score * 0.20) +
            (texture_score * 0.20) +
            (micro_expression_score * 0.20) +
            (reflection_score * 0.20)
        )
        
        return {
            'liveness_detected': liveness_confidence > 0.85,
            'liveness_confidence': liveness_confidence,
            'method_scores': {
                'temporal_consistency': temporal_consistency,
                'frequency_domain': frequency_score,
                'texture_analysis': texture_score,
                'micro_expression': micro_expression_score,
                'eye_reflection': reflection_score
            },
            'spoofing_risk': 'LOW' if liveness_confidence > 0.85 else (
                'MEDIUM' if liveness_confidence > 0.70 else 'HIGH'
            )
        }
    
    except Exception as e:
        logger.error(f"Liveness detection failed: {e}")
        raise
```

**Acceptance Criteria**:
- Liveness confidence ≥ 0.85 (PASS)
- Liveness confidence 0.70-0.85 (MARGINAL - manual review)
- Liveness confidence < 0.70 (FAIL)

**Anti-Spoofing Techniques Implemented**:

| Attack Vector | Detection Method |
|---------------|-----------------|
| Printed photo | Frequency analysis, texture patterns |
| Video replay | Temporal consistency, compression artifacts |
| Deepfake | Micro-expression analysis, frequency domain |
| Mask/silicone | Texture patterns, eye reflections, micro-movements |
| Screen recording | Compression artifacts, frequency signatures |

---

### 3. Face Embedding Generation

**Purpose**: Generate 512-dimensional face embedding for identity matching

**Implementation**:
```python
def generate_face_embedding(photo_blob):
    """
    Generate face embedding vector for later identity comparison
    """
    try:
        # Load image
        image_array = np.frombuffer(photo_blob, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_image)
        
        if not face_locations:
            raise ValueError("No face detected in photo")
        
        if len(face_locations) != 1:
            raise ValueError(f"Expected 1 face, found {len(face_locations)}")
        
        # Generate embedding (512-dimensional vector)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        if not face_encodings:
            raise ValueError("Failed to generate face encoding")
        
        embedding = face_encodings[0].tolist()  # Convert to list for JSON/DB storage
        
        return {
            'face_embedding': embedding,
            'embedding_model': 'facenet',
            'embedding_dimension': len(embedding),
            'face_location': face_locations[0]
        }
    
    except Exception as e:
        logger.error(f"Face embedding generation failed: {e}")
        raise
```

**Storage**:
```python
# Database: Stored as FLOAT8[] type in PostgreSQL
embedding_vector = [0.234, -0.156, 0.892, ...]  # 512 floats

# Encryption: Encrypted at rest with AES-256-GCM before storage
# Separate storage from photo blob (for additional security)
```

---

### 4. Identity Verification (Face Matching)

**Purpose**: Verify captured face matches stored enrollment photo(s)

**Implementation**:
```python
def match_face_identity(
    captured_face_embedding,
    enrollment_face_embeddings,
    distance_threshold=0.60
):
    """
    Compare captured face against enrolled faces
    Uses Euclidean distance for similarity measurement
    """
    matches = []
    
    for i, enrollment_embedding in enumerate(enrollment_face_embeddings):
        # Calculate Euclidean distance
        distance = np.linalg.norm(
            np.array(captured_face_embedding) - np.array(enrollment_embedding)
        )
        
        # Convert distance to similarity confidence (0-1)
        # Lower distance = higher confidence
        similarity = 1.0 / (1.0 + distance)  # Sigmoid-like transformation
        
        match_result = {
            'enrollment_index': i,
            'euclidean_distance': float(distance),
            'similarity_confidence': float(similarity),
            'is_match': distance < distance_threshold
        }
        
        matches.append(match_result)
    
    # Find best match
    best_match = min(matches, key=lambda x: x['euclidean_distance'])
    
    return {
        'best_match': best_match,
        'all_matches': matches,
        'identity_confirmed': best_match['is_match'],
        'confidence': best_match['similarity_confidence']
    }
```

**Acceptance Criteria**:
- Euclidean distance ≤ 0.60 (MATCH)
- Euclidean distance 0.60-0.70 (MARGINAL)
- Euclidean distance > 0.70 (NO MATCH)

---

## Workflow Integration: When Face Recognition is Used

### 1. REGISTRATION Workflow

```
User submits registration with live photo
    ↓
Photo validation (mandatory)
    ✅ Pass
    ↓
IF FACE_RECOGNITION_ENABLED:
    ├─ Face Detection
    │  ├─ 1 face found: Continue
    │  └─ 0 or >1 faces: OPTIONAL - Reject or allow
    │
    ├─ Liveness Detection
    │  ├─ Confidence > 0.85: Continue
    │  ├─ Confidence 0.70-0.85: Log warning, allow with flag
    │  └─ Confidence < 0.70: Log warning, allow with flag
    │
    └─ Face Enrollment
       ├─ Generate embedding
       ├─ Store in DB (mark as PRIMARY_ENROLLMENT)
       └─ Continue
ELSE:
    └─ Skip face processing
    ↓
Complete registration (email verification)
```

**Decision Logic**:
- Face detection: OPTIONAL (informational only)
- Liveness check: OPTIONAL (warning if failed, but allow)
- Face enrollment: OPTIONAL (store for future login matching)

---

### 2. LOGIN Workflow

```
User enters credentials + captures live photo
    ↓
Photo validation (mandatory)
    ✅ Pass
    ↓
IF FACE_RECOGNITION_ENABLED:
    ├─ Face Detection
    │  └─ Exactly 1 face required (reject if not)
    │
    ├─ Liveness Detection
    │  ├─ Confidence > 0.85: Continue
    │  ├─ Confidence 0.70-0.85: Marginal (log, continue)
    │  └─ Confidence < 0.70: FAIL LOGIN
    │
    └─ Identity Matching
       ├─ Query user's enrollment embeddings
       ├─ Calculate similarity distance
       ├─ Distance ≤ 0.60: Identity confirmed
       ├─ Distance 0.60-0.70: Marginal (log, continue)
       └─ Distance > 0.70: FAIL LOGIN
ELSE:
    └─ Skip face processing
    ↓
Generate access token + refresh token
    ↓
Grant login access
```

**Decision Logic**:
- Face detection: REQUIRED (must have 1 face)
- Liveness check: REQUIRED (confidence > 0.70)
- Identity matching: REQUIRED (distance < 0.70)

---

### 3. TOKEN_GENERATION Workflow

```
Authenticated user requests token with live photo
    ↓
Photo validation (mandatory)
    ✅ Pass
    ↓
IF FACE_RECOGNITION_ENABLED:
    ├─ Face Detection
    │  └─ Exactly 1 face required
    │
    ├─ Liveness Detection
    │  ├─ Confidence > 0.85: Continue
    │  ├─ Confidence 0.70-0.85: Marginal (log, continue)
    │  └─ Confidence < 0.70: FAIL TOKEN GENERATION
    │
    └─ Note: Identity matching OPTIONAL
       (Already authenticated via JWT)
ELSE:
    └─ Skip face processing
    ↓
Generate temporary campus token
    ↓
Display token/QR code
```

**Decision Logic**:
- Face detection: REQUIRED (exactly 1)
- Liveness check: REQUIRED (confidence > 0.70)
- Identity matching: OPTIONAL (already authenticated)

---

### 4. TOKEN_REGENERATION Workflow

```
User regenerates expired/revoked token with live photo
    ↓
Photo validation (mandatory)
    ✅ Pass
    ↓
IF FACE_RECOGNITION_ENABLED:
    ├─ Face Detection
    │  └─ Exactly 1 face required
    │
    ├─ Liveness Detection
    │  ├─ Confidence > 0.85: Continue
    │  ├─ Confidence 0.70-0.85: Marginal (log, continue)
    │  └─ Confidence < 0.70: FAIL REGENERATION
    │
    └─ Identity matching: OPTIONAL
ELSE:
    └─ Skip face processing
    ↓
Revoke old token + Issue new token
    ↓
Display new token
```

---

## Face Recognition Backends

### Primary Backend: `face_recognition` Library

**GitHub**: https://github.com/ageitgey/face_recognition

```bash
pip install face_recognition  # Installs dlib + cmake dependencies
```

**Pros**:
- Battle-tested, production-ready
- Good accuracy (99.38% on LFW dataset)
- Active community
- Free and open-source

**Cons**:
- Requires dlib (heavy C++ library)
- Slow on CPU-only environments (~0.5-1s per face)

**Configuration**:
```python
FACE_RECOGNITION_CONFIG = {
    'backend': 'face_recognition_library',
    'model': 'hog',  # or 'cnn' for GPU
    'num_jitters': 1,  # Increase for accuracy (1, 10, 100)
    'embedding_model': 'facenet',
    'distance_threshold': 0.6,
    'liveness_confidence_threshold': 0.85
}
```

---

### Alternative Backend: DeepFace

**GitHub**: https://github.com/serengp/deepface

```bash
pip install deepface tensorflow  # Requires TensorFlow
```

**Pros**:
- Multiple model support (VGGFace, FaceNet, OpenFace, DeepID)
- Better anti-spoofing detection
- Facial attribute analysis (age, emotion, gender)
- GPU acceleration

**Cons**:
- Heavier dependencies (TensorFlow)
- Slower initialization
- Requires more memory

**Configuration**:
```python
FACE_RECOGNITION_CONFIG = {
    'backend': 'deepface',
    'model_name': 'Facenet',  # or 'VGGFace', 'FaceNet512'
    'distance_metric': 'cosine',
    'detector_backend': 'opencv',  # or 'mtcnn', 'ssd', 'dlib'
    'anti_spoofing': True,
    'liveness_confidence_threshold': 0.85,
    'distance_threshold': 0.4
}
```

---

### Fallback: AWS Rekognition

**For cloud deployment**:

```python
import boto3

def rekognition_face_detect(photo_blob):
    """
    Fallback to AWS Rekognition (paid service)
    """
    rekognition = boto3.client('rekognition')
    
    response = rekognition.detect_faces(
        Image={'Bytes': photo_blob},
        Attributes=['DEFAULT', 'ALL']
    )
    
    if response['FaceDetails']:
        face = response['FaceDetails'][0]
        return {
            'face_detected': True,
            'confidence': face['Confidence'],
            'attributes': face
        }
    else:
        return {'face_detected': False}
```

**Advantages**:
- No local dependencies (cloud-based)
- Highly accurate
- Built-in liveness detection

**Disadvantages**:
- Per-image cost ($0.0015 per face)
- Network latency
- Data transmitted to AWS

---

## Configuration & Deployment Scenarios

### Scenario 1: Face Recognition DISABLED (Default)

```bash
# .env
FACE_RECOGNITION_ENABLED=False
```

**System Behavior**:
- ✅ All 4 workflows work normally
- ✅ Live photo capture mandatory
- ✅ No ML library dependencies
- ✅ Minimal server requirements
- ❌ No face liveness or identity verification

**Use Case**: Simple deployment, minimal server resources

---

### Scenario 2: Face Recognition ENABLED (Local ML)

```bash
# .env
FACE_RECOGNITION_ENABLED=True
FACE_RECOGNITION_BACKEND=face_recognition_library
```

**Requirements**:
```bash
# Install dependencies
pip install face-recognition dlib cmake opencv-python

# System requirements
# RAM: 4GB minimum, 8GB recommended
# CPU: Multi-core processor
# Storage: 2GB for model files
```

**System Behavior**:
- ✅ All 4 workflows work
- ✅ Live photo capture mandatory
- ✅ Face liveness detection enabled
- ✅ Identity verification on login/token generation
- ⚠️ Slower processing (1-3s per photo)
- ⚠️ Higher server requirements

**Use Case**: Production on-premises deployment

---

### Scenario 3: Face Recognition via Cloud Service

```bash
# .env
FACE_RECOGNITION_ENABLED=True
FACE_RECOGNITION_BACKEND=aws_rekognition
AWS_REKOGNITION_REGION=us-east-1
```

**Requirements**:
- AWS account with Rekognition API enabled
- IAM credentials configured

**System Behavior**:
- ✅ All 4 workflows work
- ✅ Live photo capture mandatory
- ✅ High-accuracy face liveness + identity
- ⚠️ Per-image cost (~$0.0015)
- ⚠️ Network latency

**Use Case**: Cloud-native deployment, minimal ops

---

## Face Recognition Failure Handling

### When Face Recognition Service Fails

```python
def handle_face_recognition_failure(photo_blob, user_id, error):
    """
    Graceful degradation when face recognition unavailable
    """
    logger.error(f"Face recognition failed: {error}")
    
    # Attempt fallback
    try:
        if settings.FACE_RECOGNITION_BACKEND == 'face_recognition_library':
            # Try DeepFace fallback
            result = use_deepface_fallback(photo_blob)
            return result
    except Exception as fallback_error:
        logger.error(f"Fallback also failed: {fallback_error}")
    
    # If all face recognition fails:
    # - System continues with single-factor live photo verification
    # - Log incident for monitoring
    # - Alert ops team if persistent
    
    return {
        'face_recognition_available': False,
        'fallback_attempted': True,
        'single_factor_only': True,  # Live photo only
        'recommend_manual_review': True
    }
```

### Monitoring & Alerting

```python
# Prometheus metrics
face_recognition_successes = Counter(
    'face_recognition_successes_total',
    'Total successful face recognitions'
)
face_recognition_failures = Counter(
    'face_recognition_failures_total',
    'Total failed face recognitions',
    ['reason']  # 'no_face_detected', 'liveness_failed', etc.
)
face_recognition_latency = Histogram(
    'face_recognition_processing_seconds',
    'Face recognition processing latency'
)

# Alert rules (Prometheus/AlertManager)
alert: FaceRecognitionHighFailureRate
  expr: rate(face_recognition_failures_total[5m]) > 0.1
  for: 5m
  annotations:
    summary: "Face recognition failure rate > 10% for 5 minutes"
    action: "Check face_recognition service logs, consider disabling feature"
```

---

## Privacy & Compliance

### GDPR: Face Data is Biometric Data

**Implications**:
- Face embeddings classified as biometric personal data
- Requires explicit consent (Article 9)
- Cannot be shared with third parties
- User has right to deletion (Article 17)
- Requires privacy impact assessment (DPIA)

**Implementation**:
```python
class BiometricConsentForm(forms.Form):
    """
    Explicit consent for biometric face recognition
    """
    consent_face_recognition = forms.BooleanField(
        label="I consent to face recognition for identity verification",
        required=False,
        help_text="Optional. Can be changed in account settings."
    )
    consent_face_storage = forms.BooleanField(
        label="I consent to storing my face for future logins",
        required=False,
        help_text="Your face data will be encrypted and stored securely."
    )

# Database
user.face_recognition_consent = True
user.face_recognition_consent_date = timezone.now()
```

### Data Retention for Face Data

| Data Type | Retention | Purge Method |
|-----------|-----------|--------------|
| Live photo | 90 days | Auto-delete S3 + soft-delete DB |
| Face embedding | 60 days | Auto-delete from DB |
| Face match history | 180 days | Auto-delete audit logs |
| Liveness scores | 30 days | Auto-delete after retention |

---

## Performance Optimization

### Caching Strategy

```python
# Redis cache for embeddings
def get_user_face_embeddings_cached(user_id):
    """
    Cache face embeddings to avoid repeated DB queries
    """
    cache_key = f"face_embeddings:{user_id}"
    cached = cache.get(cache_key)
    
    if cached:
        return cached
    
    # Query DB if not cached
    embeddings = FaceRecognitionResult.objects.filter(
        security_photo__user_id=user_id,
        security_photo__workflow_event='REGISTRATION'
    ).order_by('-created_at')[:5]  # Last 5 enrollments
    
    result = [
        {
            'id': e.id,
            'embedding': e.face_embedding_vector,
            'confidence': e.primary_face_confidence
        }
        for e in embeddings
    ]
    
    # Cache for 24 hours
    cache.set(cache_key, result, timeout=86400)
    return result
```

### Batch Processing for Analysis

```python
# Celery task for async face recognition
@app.task(bind=True)
def process_face_recognition_async(self, photo_id, user_id):
    """
    Async face recognition processing to avoid blocking API
    """
    photo = SecurityPhoto.objects.get(id=photo_id)
    
    # Download photo from S3
    photo_blob = download_photo_from_s3(photo.photo_blob_s3_key)
    
    # Process face recognition
    result = perform_face_recognition(photo_blob, user_id)
    
    # Update database
    FaceRecognitionResult.objects.create(
        security_photo_id=photo_id,
        **result
    )
    
    # Send notification
    send_face_recognition_complete_notification(user_id, photo_id)
```

---

## Testing & Validation

### Unit Tests for Face Recognition

```python
def test_face_detection_single_face():
    """Test detection with exactly 1 face"""
    result = detect_face(test_photo_single_face)
    assert result['face_detected'] == True
    assert result['face_count'] == 1

def test_face_detection_no_face():
    """Test detection with no faces"""
    result = detect_face(test_photo_no_face)
    assert result['face_detected'] == False
    assert result['face_count'] == 0

def test_face_detection_multiple_faces():
    """Test detection with multiple faces"""
    result = detect_face(test_photo_multiple_faces)
    assert result['face_detected'] == False
    assert result['face_count'] > 1

def test_liveness_detection_live():
    """Test liveness detection with live person"""
    result = detect_liveness(test_photo_live_person)
    assert result['liveness_confidence'] > 0.85

def test_liveness_detection_photo():
    """Test liveness detection with printed photo (spoofing)"""
    result = detect_liveness(test_photo_printed)
    assert result['liveness_confidence'] < 0.70

def test_identity_matching():
    """Test face identity verification"""
    enrollment_embedding = generate_face_embedding(test_photo_person1)[0]
    captured_embedding = generate_face_embedding(test_photo_person1_new)[0]
    
    result = match_face_identity(captured_embedding, [enrollment_embedding])
    assert result['identity_confirmed'] == True
```

---

## Operations & Maintenance

### Monitoring Dashboard

```
Face Recognition Health
├─ Service Status: OPERATIONAL / DEGRADED / DOWN
├─ Response Time (p99): 850ms (target: <3s)
├─ Success Rate: 98.5% (target: >95%)
├─ Error Rate: 1.5% (alert if >5%)
├─ Liveness Detection:
│  ├─ True Positive Rate: 96%
│  ├─ False Positive Rate: 2%
│  └─ False Negative Rate: 2%
├─ Identity Matching:
│  ├─ True Positive Rate: 94%
│  ├─ False Positive Rate: 1%
│  └─ False Negative Rate: 5%
└─ Resource Usage:
   ├─ CPU: 45% average
   ├─ Memory: 2.1GB average
   └─ GPU (if available): 60% utilization
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-08-15  
**Face Recognition Architect**: [Your Name/Team]  
**Status**: Phase 0 - Design Complete

**KEY TAKEAWAYS**:
- Face recognition is OPTIONAL and can be completely disabled
- System functions normally if ML libraries unavailable
- Graceful degradation on service failures
- GDPR-compliant data handling for biometric data
- Multiple backend options (local, cloud, fallback)
- Production-ready monitoring and alerting
