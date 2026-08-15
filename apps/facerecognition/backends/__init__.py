"""
Face Recognition backends module.

This module contains concrete implementations of face recognition backends.
Each backend is imported ONLY when needed, never at Django startup.
"""

from .dlib_backend import DisabledFaceRecognitionBackend, DlibFaceRecognitionBackend

__all__ = [
    'DisabledFaceRecognitionBackend',
    'DlibFaceRecognitionBackend',
]
