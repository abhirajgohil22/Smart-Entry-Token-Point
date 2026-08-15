"""
Face Recognition service module.

This module provides the service boundary for face recognition functionality.
It implements the strategy pattern to allow graceful degradation when the feature
is disabled or libraries are unavailable.

IMPORTANT: This module should be imported ONLY when accessing face recognition services,
not during Django startup.
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class FaceRecognitionStatus(Enum):
    """Status enumeration for face recognition operations"""
    SUCCESS = "success"
    NOT_ENABLED = "not_enabled"
    LIBRARY_NOT_AVAILABLE = "library_not_available"
    INVALID_INPUT = "invalid_input"
    NO_FACE_DETECTED = "no_face_detected"
    MULTIPLE_FACES_DETECTED = "multiple_faces_detected"
    LIVENESS_CHECK_FAILED = "liveness_check_failed"
    FACE_MISMATCH = "face_mismatch"
    FAILED = "failed"
    ERROR = "error"
    PROCESSING_ERROR = "processing_error"


class FaceRecognitionResult:
    """Result object for face recognition operations"""

    def __init__(
        self,
        status: FaceRecognitionStatus,
        data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        self.status = status
        self.data = data or {}
        self.error_message = error_message
        self.success = status == FaceRecognitionStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'status': self.status.value,
            'success': self.success,
            'data': self.data,
            'error_message': self.error_message,
        }

    def __repr__(self):
        return f"FaceRecognitionResult(status={self.status.value}, success={self.success})"


class BaseFaceRecognitionBackend:
    """
    Abstract base class for face recognition backends.

    This interface defines the contract for all face recognition implementations.
    Concrete implementations must override all methods.
    """

    def __init__(self):
        """Initialize the backend"""
        self.name = self.__class__.__name__

    def detect_face(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """
        Detect face(s) in an image.

        Args:
            image_data: Image file content as bytes
            **kwargs: Additional parameters (e.g., confidence threshold)

        Returns:
            FaceRecognitionResult with detection data
        """
        raise NotImplementedError(f"{self.name} does not implement detect_face")

    def get_liveness_score(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """
        Determine if the image is a live face or a spoofing attempt.

        Args:
            image_data: Image file content as bytes
            **kwargs: Additional parameters (e.g., algorithm choice)

        Returns:
            FaceRecognitionResult with liveness confidence score (0.0-1.0)
        """
        raise NotImplementedError(f"{self.name} does not implement get_liveness_score")

    def generate_face_embedding(self, image_data: bytes, **kwargs) -> FaceRecognitionResult:
        """
        Generate a face embedding vector from an image.

        Args:
            image_data: Image file content as bytes
            **kwargs: Additional parameters

        Returns:
            FaceRecognitionResult with 512-D face embedding vector
        """
        raise NotImplementedError(f"{self.name} does not implement generate_face_embedding")

    def compare_faces(
        self, embedding1: List[float], embedding2: List[float], **kwargs
    ) -> FaceRecognitionResult:
        """
        Compare two face embeddings to determine if they are the same person.

        Args:
            embedding1: First face embedding vector
            embedding2: Second face embedding vector
            **kwargs: Additional parameters (e.g., distance threshold)

        Returns:
            FaceRecognitionResult with match confidence
        """
        raise NotImplementedError(f"{self.name} does not implement compare_faces")

    def verify_face_match(
        self, embedding1: List[float], embedding2: List[float], **kwargs
    ) -> FaceRecognitionResult:
        """High-level 1:1 verification wrapper with default threshold of 0.6."""
        threshold = kwargs.get('threshold', kwargs.get('distance_threshold', 0.6))
        compare_kwargs = dict(kwargs)
        compare_kwargs.pop('threshold', None)
        compare_kwargs.pop('distance_threshold', None)
        return self.compare_faces(embedding1, embedding2, threshold=threshold, **compare_kwargs)

    def is_available(self) -> bool:
        """Check if the backend is available and ready to use"""
        raise NotImplementedError(f"{self.name} does not implement is_available")

    def health_check(self) -> FaceRecognitionResult:
        """
        Verify the backend is operational and all dependencies are available.

        Returns:
            FaceRecognitionResult indicating backend health status
        """
        raise NotImplementedError(f"{self.name} does not implement health_check")
