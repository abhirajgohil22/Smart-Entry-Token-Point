"""
Face Recognition service implementations.

This module contains concrete implementations of face recognition backends.
Each backend is designed to fail gracefully when libraries are unavailable.
"""

import logging
from typing import List, Optional

from apps.facerecognition.services.base import (
    BaseFaceRecognitionBackend,
    FaceRecognitionResult,
    FaceRecognitionStatus,
)

logger = logging.getLogger(__name__)


class DisabledFaceRecognitionBackend(BaseFaceRecognitionBackend):
    """
    Stub backend when face recognition is disabled.

    This backend always returns NOT_ENABLED status, allowing the system
    to operate with single-factor photo verification.
    """

    def __init__(self):
        super().__init__()
        self.name = "DisabledFaceRecognitionBackend"

    def detect_face(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """Face detection disabled"""
        return FaceRecognitionResult(
            status=FaceRecognitionStatus.NOT_ENABLED,
            error_message="Face recognition feature is disabled",
        )

    def get_liveness_score(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """Liveness detection disabled"""
        return FaceRecognitionResult(
            status=FaceRecognitionStatus.NOT_ENABLED,
            error_message="Face recognition feature is disabled",
        )

    def generate_face_embedding(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """Face embedding generation disabled"""
        return FaceRecognitionResult(
            status=FaceRecognitionStatus.NOT_ENABLED,
            error_message="Face recognition feature is disabled",
        )

    def compare_faces(
        self, embedding1: List[float], embedding2: List[float], **kwargs
    ) -> FaceRecognitionResult:
        """Face comparison disabled"""
        return FaceRecognitionResult(
            status=FaceRecognitionStatus.NOT_ENABLED,
            error_message="Face recognition feature is disabled",
        )

    def is_available(self) -> bool:
        """This backend is always available (as a no-op)"""
        return True

    def health_check(self) -> FaceRecognitionResult:
        """Health check for disabled backend"""
        return FaceRecognitionResult(
            status=FaceRecognitionStatus.NOT_ENABLED,
            data={'backend': 'disabled', 'available': True},
        )


class DlibFaceRecognitionBackend(BaseFaceRecognitionBackend):
    """
    Face recognition backend using the dlib-based face_recognition library.

    This backend implements graceful degradation: if the face_recognition
    library is not installed, all methods return LIBRARY_NOT_AVAILABLE.

    CRITICAL: All imports of face_recognition happen INSIDE method calls ONLY,
    never at module or class initialization time.
    """

    def __init__(self):
        super().__init__()
        self.name = "DlibFaceRecognitionBackend"
        self._library_available = None

    def _check_library_availability(self) -> bool:
        """
        Check if face_recognition library is available.
        Caches the result to avoid repeated import attempts.
        """
        if self._library_available is not None:
            return self._library_available

        try:
            import face_recognition  # Import ONLY when needed
            self._library_available = True
            logger.info("face_recognition library is available")
            return True
        except ImportError:
            self._library_available = False
            logger.warning(
                "face_recognition library not available. Install with: "
                "pip install face-recognition dlib"
            )
            return False

    def detect_face(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """
        Detect face(s) in an image using dlib.

        Returns:
            FaceRecognitionResult with face locations or error status
        """
        if not self._check_library_availability():
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.LIBRARY_NOT_AVAILABLE,
                error_message="face_recognition library not installed",
            )

        try:
            import face_recognition  # Dynamic import inside method
            from PIL import Image
            import io

            # Load image from bytes
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
            image_array = [list(row) for row in image]

            # Detect faces
            face_locations = face_recognition.face_locations(image_array, model='hog')

            if len(face_locations) == 0:
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.NO_FACE_DETECTED,
                    error_message="No face detected in image",
                )
            elif len(face_locations) > 1:
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.MULTIPLE_FACES_DETECTED,
                    error_message=f"Multiple faces detected ({len(face_locations)}), expected 1",
                )

            return FaceRecognitionResult(
                status=FaceRecognitionStatus.SUCCESS,
                data={
                    'face_count': len(face_locations),
                    'face_locations': face_locations[0],  # Return first face
                    'face_area_percentage': self._calculate_face_area(face_locations[0], image.size),
                },
            )

        except Exception as e:
            logger.error(f"Face detection error: {str(e)}")
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.PROCESSING_ERROR,
                error_message=f"Face detection failed: {str(e)}",
            )

    def get_liveness_score(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """
        Determine liveness score for an image (whether it's a real face or spoofing attempt).

        This is a placeholder implementation that returns a mock confidence score.
        A production implementation would use anti-spoofing algorithms.

        Returns:
            FaceRecognitionResult with liveness_confidence (0.0-1.0)
        """
        if not self._check_library_availability():
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.LIBRARY_NOT_AVAILABLE,
                error_message="face_recognition library not installed",
            )

        try:
            # TODO: Implement actual liveness detection using:
            # - Frequency domain analysis (FFT)
            # - Texture analysis (LBP)
            # - Motion detection (optical flow)
            # - Eye reflection analysis
            # - Micro-expression detection

            # For now, return a high confidence score
            # In production, this would use anti-spoofing ML models
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.SUCCESS,
                data={
                    'liveness_confidence': 0.95,  # Placeholder
                    'is_live': True,
                    'spoof_risk': 'low',
                },
            )

        except Exception as e:
            logger.error(f"Liveness detection error: {str(e)}")
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.PROCESSING_ERROR,
                error_message=f"Liveness detection failed: {str(e)}",
            )

    def generate_face_embedding(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """
        Generate a 512-dimensional face embedding vector from an image.

        Returns:
            FaceRecognitionResult with face_embedding vector
        """
        if not self._check_library_availability():
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.LIBRARY_NOT_AVAILABLE,
                error_message="face_recognition library not installed",
            )

        try:
            import face_recognition  # Dynamic import inside method
            from PIL import Image
            import io

            # Load image from bytes
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
            image_array = [list(row) for row in image]

            # Detect faces first
            face_locations = face_recognition.face_locations(image_array, model='hog')

            if len(face_locations) == 0:
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.NO_FACE_DETECTED,
                    error_message="No face detected in image",
                )
            elif len(face_locations) > 1:
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.MULTIPLE_FACES_DETECTED,
                    error_message=f"Multiple faces detected ({len(face_locations)}), expected 1",
                )

            # Generate embedding for the first face
            face_encodings = face_recognition.face_encodings(image_array, face_locations)

            if not face_encodings:
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.PROCESSING_ERROR,
                    error_message="Could not generate face embedding",
                )

            embedding = face_encodings[0]

            return FaceRecognitionResult(
                status=FaceRecognitionStatus.SUCCESS,
                data={
                    'embedding': embedding.tolist(),  # Convert numpy array to list
                    'embedding_dimension': len(embedding),
                },
            )

        except Exception as e:
            logger.error(f"Face embedding generation error: {str(e)}")
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.PROCESSING_ERROR,
                error_message=f"Face embedding generation failed: {str(e)}",
            )

    def compare_faces(
        self, embedding1: List[float], embedding2: List[float], **kwargs
    ) -> FaceRecognitionResult:
        """
        Compare two face embeddings using Euclidean distance.

        Args:
            embedding1: First face embedding vector
            embedding2: Second face embedding vector
            **kwargs: Can include 'distance_threshold' (default: 0.6)

        Returns:
            FaceRecognitionResult with match_distance and is_match
        """
        if not self._check_library_availability():
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.LIBRARY_NOT_AVAILABLE,
                error_message="face_recognition library not installed",
            )

        try:
            import face_recognition  # Dynamic import inside method
            import numpy as np

            # Convert to numpy arrays
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)

            # Calculate Euclidean distance
            distance = np.linalg.norm(emb1 - emb2)

            # Get threshold from kwargs or use default
            distance_threshold = kwargs.get('distance_threshold', 0.6)

            is_match = distance <= distance_threshold

            return FaceRecognitionResult(
                status=FaceRecognitionStatus.SUCCESS,
                data={
                    'match_distance': float(distance),
                    'distance_threshold': distance_threshold,
                    'is_match': is_match,
                    'confidence': max(0.0, 1.0 - (distance / distance_threshold)),
                },
            )

        except Exception as e:
            logger.error(f"Face comparison error: {str(e)}")
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.PROCESSING_ERROR,
                error_message=f"Face comparison failed: {str(e)}",
            )

    def is_available(self) -> bool:
        """Check if the dlib backend is available"""
        return self._check_library_availability()

    def health_check(self) -> FaceRecognitionResult:
        """Verify the backend is operational"""
        if self._check_library_availability():
            try:
                import face_recognition  # Verify import works
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.SUCCESS,
                    data={
                        'backend': 'dlib',
                        'available': True,
                        'version': 'unknown',  # face_recognition doesn't expose version
                    },
                )
            except Exception as e:
                logger.error(f"Backend health check failed: {str(e)}")
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.PROCESSING_ERROR,
                    error_message=f"Backend health check failed: {str(e)}",
                )
        else:
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.LIBRARY_NOT_AVAILABLE,
                error_message="face_recognition library not installed",
            )

    @staticmethod
    def _calculate_face_area(face_location: tuple, image_size: tuple) -> float:
        """Calculate the percentage of image area covered by the face"""
        top, right, bottom, left = face_location
        face_area = (right - left) * (bottom - top)
        image_area = image_size[0] * image_size[1]
        return (face_area / image_area) * 100 if image_area > 0 else 0
