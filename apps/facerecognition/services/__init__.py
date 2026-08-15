"""
Face Recognition service factory and manager.

This module provides the service interface that should be used throughout the application
to access face recognition functionality. It implements the factory pattern to instantiate
the appropriate backend based on Django settings.

CRITICAL: The factory is lazy-loaded - it only creates the backend when first accessed,
not during Django startup.
"""

import logging
from typing import Optional

from django.conf import settings

from apps.facerecognition.backends import DisabledFaceRecognitionBackend, DlibFaceRecognitionBackend
from apps.facerecognition.services.base import (
    BaseFaceRecognitionBackend,
    FaceRecognitionResult,
    FaceRecognitionStatus,
)
from apps.facerecognition.services.liveness import LivenessVerificationService

logger = logging.getLogger(__name__)

__all__ = [
    'FaceRecognitionService',
    'FaceRecognitionServiceFactory',
    'get_face_recognition_service',
    'LivenessVerificationService',
]


class FaceRecognitionServiceFactory:
    """
    Factory for creating face recognition backend instances.

    This factory is responsible for:
    1. Selecting the appropriate backend based on Django settings
    2. Ensuring lazy loading (no imports at Django startup)
    3. Caching the backend instance
    4. Providing graceful degradation when libraries are unavailable
    """

    _instance: Optional[BaseFaceRecognitionBackend] = None

    @classmethod
    def get_backend(cls) -> BaseFaceRecognitionBackend:
        """
        Get or create the face recognition backend.

        Returns the appropriate backend based on FACE_RECOGNITION_ENABLED setting.
        If disabled or if the selected backend library is not available, returns
        the DisabledFaceRecognitionBackend which allows graceful degradation.

        Returns:
            BaseFaceRecognitionBackend instance
        """
        if cls._instance is not None:
            return cls._instance

        # Check if feature is enabled
        if not settings.FACE_RECOGNITION_ENABLED:
            logger.info("Face recognition disabled - using DisabledFaceRecognitionBackend")
            cls._instance = DisabledFaceRecognitionBackend()
            return cls._instance

        # Get the configured backend
        backend_name = getattr(settings, 'FACE_RECOGNITION_BACKEND', 'dlib')

        try:
            if backend_name.lower() == 'dlib':
                backend = DlibFaceRecognitionBackend()
                if backend.is_available():
                    logger.info("Using DlibFaceRecognitionBackend")
                    cls._instance = backend
                    return cls._instance
                else:
                    logger.warning(
                        "Dlib backend not available - falling back to DisabledFaceRecognitionBackend"
                    )
                    cls._instance = DisabledFaceRecognitionBackend()
                    return cls._instance
            else:
                logger.warning(f"Unknown backend: {backend_name} - using DisabledFaceRecognitionBackend")
                cls._instance = DisabledFaceRecognitionBackend()
                return cls._instance

        except Exception as e:
            logger.error(f"Error creating face recognition backend: {str(e)}")
            logger.warning("Falling back to DisabledFaceRecognitionBackend")
            cls._instance = DisabledFaceRecognitionBackend()
            return cls._instance

    @classmethod
    def reset(cls):
        """Reset the cached instance (useful for testing)"""
        cls._instance = None


class FaceRecognitionService:
    """
    Public service interface for face recognition operations.

    This is the recommended way to access face recognition functionality.
    It delegates to the appropriate backend selected by the factory.
    """

    def __init__(self):
        """Initialize the service with the configured backend"""
        self.backend = FaceRecognitionServiceFactory.get_backend()

    def detect_face(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """
        Detect face(s) in an image.

        Args:
            image_data: Image file content as bytes
            **kwargs: Additional parameters

        Returns:
            FaceRecognitionResult
        """
        return self.backend.detect_face(image_data, **kwargs)

    def get_liveness_score(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """
        Determine liveness score for an image.

        Args:
            image_data: Image file content as bytes
            **kwargs: Additional parameters

        Returns:
            FaceRecognitionResult with confidence score
        """
        return self.backend.get_liveness_score(image_data, **kwargs)

    def generate_face_embedding(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """
        Generate face embedding vector from an image.

        Args:
            image_data: Image file content as bytes
            **kwargs: Additional parameters

        Returns:
            FaceRecognitionResult with embedding vector
        """
        return self.backend.generate_face_embedding(image_data, **kwargs)

    def compare_faces(self, embedding1, embedding2, **kwargs) -> FaceRecognitionResult:
        """
        Compare two face embeddings.

        Args:
            embedding1: First face embedding vector
            embedding2: Second face embedding vector
            **kwargs: Additional parameters

        Returns:
            FaceRecognitionResult with match information
        """
        return self.backend.compare_faces(embedding1, embedding2, **kwargs)

    def verify_face_match(self, embedding1, embedding2, threshold=0.6, **kwargs) -> FaceRecognitionResult:
        """1:1 face verification using the default threshold of 0.6."""
        try:
            return self.backend.verify_face_match(
                embedding1,
                embedding2,
                threshold=threshold,
                **kwargs,
            )
        except Exception as exc:  # pragma: no cover - defensive guard for runtime failures
            logger.exception("Face verification raised an unexpected exception")
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.ERROR,
                error_message=f"Face verification failed: {exc}",
            )

    def verify_security_photo(self, security_photo, *, user=None, threshold=0.6, **kwargs) -> FaceRecognitionResult:
        """Verify a SecurityPhoto frame against the enrolled encoding for the user."""
        if not getattr(settings, 'FACE_RECOGNITION_ENABLED', False):
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.NOT_ENABLED,
                data={'match': False, 'threshold': threshold},
                error_message='Face recognition is disabled; live-photo verification is single-factor only.',
            )

        if security_photo is None:
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.INVALID_INPUT,
                error_message='A security photo is required for verification.',
            )

        target_user = user or getattr(security_photo, 'user', None)
        if target_user is None:
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.INVALID_INPUT,
                error_message='No user available to verify against the security photo.',
            )

        try:
            enrolled = getattr(target_user, 'face_encoding', None)
            if enrolled is None or not getattr(enrolled, 'encoding', None):
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.FAILED,
                    data={'match': False, 'threshold': threshold},
                    error_message='No enrolled face encoding exists for this user.',
                )

            image = getattr(security_photo, 'image', None)
            if image is None:
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.INVALID_INPUT,
                    error_message='Security photo image is missing.',
                )

            with image.open('rb') as fh:
                image_bytes = fh.read()

            if not image_bytes:
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.INVALID_INPUT,
                    error_message='Security photo is empty.',
                )

            embedding_result = self.generate_face_embedding(image_bytes, **kwargs)
            if not embedding_result.success:
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.FAILED,
                    data={'match': False, 'threshold': threshold},
                    error_message=embedding_result.error_message or 'Could not extract face embedding from the live security photo.',
                )

            verification = self.verify_face_match(
                embedding_result.data.get('embedding', []),
                enrolled.encoding,
                threshold=threshold,
                **kwargs,
            )

            if verification.status in (FaceRecognitionStatus.FAILED, FaceRecognitionStatus.FACE_MISMATCH):
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.FAILED,
                    data={
                        'match': False,
                        'threshold': threshold,
                        'confidence': verification.data.get('confidence', 0.0),
                        'match_distance': verification.data.get('match_distance'),
                    },
                    error_message=verification.error_message or 'Face verification did not match the enrolled encoding.',
                )

            if verification.status == FaceRecognitionStatus.ERROR:
                return FaceRecognitionResult(
                    status=FaceRecognitionStatus.ERROR,
                    data={'match': False, 'threshold': threshold},
                    error_message=verification.error_message or 'Face verification failed unexpectedly.',
                )

            return verification

        except Exception as exc:
            logger.exception('Security photo verification raised an unexpected exception')
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.ERROR,
                data={'match': False, 'threshold': threshold},
                error_message=f'Face verification failed unexpectedly: {exc}',
            )

    def is_available(self) -> bool:
        """Check if face recognition is available and ready to use"""
        return self.backend.is_available()

    def health_check(self) -> FaceRecognitionResult:
        """Verify the service is operational"""
        return self.backend.health_check()


# Convenience function for accessing the service
def get_face_recognition_service() -> FaceRecognitionService:
    """
    Get a face recognition service instance.

    This is a convenience function for code that prefers functional access
    over instantiating the service class.

    Returns:
        FaceRecognitionService instance
    """
    return FaceRecognitionService()
