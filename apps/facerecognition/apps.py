"""
Face Recognition app for Smart Campus Token Management System.

This app provides optional face recognition capabilities with complete graceful degradation
when the feature is disabled or when required libraries are not installed.

CRITICAL: This app is designed with strict service boundaries to ensure:
1. NO imports of face_recognition, dlib, or cv2 happen at Django startup
2. All biometric libraries are imported ONLY inside method calls
3. The system operates normally when FACE_RECOGNITION_ENABLED=False
4. Feature can be disabled/enabled via environment configuration
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class FacerecognitionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.facerecognition'
    verbose_name = 'Face Recognition'

    def ready(self):
        """
        App initialization - does NOT import face recognition libraries.
        This method only sets up the app without loading optional dependencies.
        """
        from django.conf import settings

        # Log feature status at startup
        if settings.FACE_RECOGNITION_ENABLED:
            logger.info(
                f"Face recognition feature ENABLED using backend: {settings.FACE_RECOGNITION_BACKEND}"
            )
            if settings.LIVENESS_ENABLED:
                logger.info("Liveness detection ENABLED")
        else:
            logger.info("Face recognition feature DISABLED - system will operate normally")
            logger.info("Live photo verification will be single-factor")
