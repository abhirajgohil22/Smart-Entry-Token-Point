"""Optional liveness verification wrapper for browser challenge flows."""

import io
import math
from typing import Iterable, List

from django.conf import settings
from PIL import Image

from apps.facerecognition.services.base import FaceRecognitionResult, FaceRecognitionStatus


class LivenessVerificationService:
    """Feature-flagged service for temporal liveness verification."""

    CHALLENGE_ACTIONS = [
        'Blink slowly',
        'Turn head slightly right',
        'Look left and right',
        'Nod once gently',
    ]

    @staticmethod
    def get_random_challenge():
        import random

        return random.choice(LivenessVerificationService.CHALLENGE_ACTIONS)

    @staticmethod
    def _frame_brightness(frame_bytes: bytes) -> float:
        try:
            image = Image.open(io.BytesIO(frame_bytes)).convert('L')
            pixels = list(image.getdata())
            if not pixels:
                return 0.0
            return sum(pixels) / len(pixels)
        except Exception:
            return 0.0

    @classmethod
    def evaluate_frames(cls, frames: Iterable[bytes], *, challenge=None) -> FaceRecognitionResult:
        """Evaluate a captured sequence of frames for motion-based liveness."""
        if not getattr(settings, 'LIVENESS_ENABLED', False):
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.SUCCESS,
                data={
                    'challenge_bypassed': True,
                    'challenge': challenge or 'Single frame verification',
                    'passed': True,
                },
            )

        frames = list(frames or [])
        if len(frames) < 3:
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.LIVENESS_CHECK_FAILED,
                data={'challenge_passed': False, 'reason': 'Not enough frames captured for liveness evaluation.'},
                error_message='Not enough frames captured for liveness evaluation.',
            )

        brightness_levels = [cls._frame_brightness(frame) for frame in frames]
        if not brightness_levels or all(value == brightness_levels[0] for value in brightness_levels):
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.LIVENESS_CHECK_FAILED,
                data={'challenge_passed': False, 'reason': 'No meaningful motion was detected.'},
                error_message='No meaningful motion was detected.',
            )

        # Use temporal brightness delta as a lightweight anti-replay signal.
        movement = sum(abs(brightness_levels[i] - brightness_levels[i - 1]) for i in range(1, len(brightness_levels))) / max(1, len(brightness_levels) - 1)
        if movement < 8.0:
            return FaceRecognitionResult(
                status=FaceRecognitionStatus.LIVENESS_CHECK_FAILED,
                data={'challenge_passed': False, 'reason': 'Temporal movement was insufficient for liveness validation.'},
                error_message='Temporal movement was insufficient for liveness validation.',
            )

        return FaceRecognitionResult(
            status=FaceRecognitionStatus.SUCCESS,
            data={
                'challenge_passed': True,
                'challenge': challenge or cls.get_random_challenge(),
                'movement_score': round(movement, 3),
            },
        )
