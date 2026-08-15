"""Security-photo validation and challenge management services."""

import os
import secrets
from datetime import datetime, timedelta

from django.core.cache import cache
from django.core import signing
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from apps.notifications.services import NotificationService
from apps.security_photos.models import ProfilePhoto, SecurityPhoto


class LivePhotoService:
    """Validate captured live photos before they are accepted by the backend."""

    MAX_FILE_SIZE = 5 * 1024 * 1024
    MAX_DIMENSION = 4096
    MIN_DIMENSION = 32
    ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png'}

    @staticmethod
    def _read_image_bytes(image):
        if image is None or not hasattr(image, 'read'):
            return None

        try:
            current_position = image.tell()
        except (AttributeError, OSError):
            current_position = None

        try:
            image.seek(0)
            payload = image.read()
            if current_position is not None:
                image.seek(current_position)
            else:
                image.seek(0)
            return payload
        except (AttributeError, OSError, ValueError):
            return None

    @staticmethod
    def _matches_existing_upload(image, user=None):
        payload = LivePhotoService._read_image_bytes(image)
        if not payload:
            return False

        queryset = SecurityPhoto.objects.none()
        if user is not None:
            queryset = SecurityPhoto.objects.filter(user=user)

        for existing in queryset.select_related('user').order_by('-captured_at'):
            if not existing.image:
                continue
            try:
                with existing.image.open('rb') as file_obj:
                    if file_obj.read() == payload:
                        return True
            except (FileNotFoundError, OSError, ValueError):
                continue

        if user is not None:
            profile_photo = ProfilePhoto.objects.filter(user=user).first()
            if profile_photo and profile_photo.image:
                try:
                    with profile_photo.image.open('rb') as file_obj:
                        if file_obj.read() == payload:
                            return True
                except (FileNotFoundError, OSError, ValueError):
                    pass

        return False

    @staticmethod
    def validate(image, *, field_name='live_photo', user=None):
        if image is None:
            raise serializers.ValidationError(f'{field_name} is required.')

        if not hasattr(image, 'read'):
            raise serializers.ValidationError(f'{field_name} is invalid.')

        try:
            image.seek(0, os.SEEK_END)
            size = image.tell()
            image.seek(0)
        except (AttributeError, OSError):
            raise serializers.ValidationError(f'{field_name} is invalid.')

        if size == 0 or size > LivePhotoService.MAX_FILE_SIZE:
            raise serializers.ValidationError('Live photo must be between 1 byte and 5 MB.')

        content_type = (getattr(image, 'content_type', '') or '').lower()
        if content_type and content_type not in LivePhotoService.ALLOWED_CONTENT_TYPES:
            raise serializers.ValidationError('Only PNG and JPEG images are allowed.')

        try:
            with Image.open(image) as img:
                img.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise serializers.ValidationError('Live photo is not a valid image.')

        try:
            image.seek(0)
            with Image.open(image) as img:
                width, height = img.size
        except (UnidentifiedImageError, OSError, ValueError):
            raise serializers.ValidationError('Live photo is not a valid image.')

        if width < LivePhotoService.MIN_DIMENSION or height < LivePhotoService.MIN_DIMENSION:
            raise serializers.ValidationError('Live photo dimensions are too small.')

        if width > LivePhotoService.MAX_DIMENSION or height > LivePhotoService.MAX_DIMENSION:
            raise serializers.ValidationError('Live photo dimensions are too large.')

        if user is not None and LivePhotoService._matches_existing_upload(image, user=user):
            raise serializers.ValidationError('A reused photo or profile avatar cannot satisfy the live-photo requirement.')

        return image


class PhotoChallengeService:
    """Generate and validate one-time live-photo challenge tokens."""

    CHALLENGE_SALT = 'security-photo-challenge'
    CHALLENGE_TTL_SECONDS = 60

    @staticmethod
    def _nonce_cache_key(nonce):
        return f'security_photo_nonce:{nonce}'

    @classmethod
    def generate_challenge(cls, user_id, event_type):
        if user_id in (None, ''):
            raise ValueError('A user_id is required to generate a live-photo challenge.')
        if event_type in (None, ''):
            raise ValueError('An event_type is required to generate a live-photo challenge.')

        nonce = secrets.token_urlsafe(24)
        timestamp = timezone.now().isoformat()
        payload = {
            'user_id': str(user_id),
            'event_type': str(event_type),
            'nonce': nonce,
            'timestamp': timestamp,
        }
        token = signing.dumps(payload, salt=cls.CHALLENGE_SALT)
        cache.set(cls._nonce_cache_key(nonce), 'fresh', timeout=cls.CHALLENGE_TTL_SECONDS)

        return {
            'user_id': str(user_id),
            'event_type': str(event_type),
            'nonce': nonce,
            'photo_verification_token': token,
            'timestamp': timestamp,
            'expires_in': cls.CHALLENGE_TTL_SECONDS,
        }

    @classmethod
    def validate_challenge(cls, token, *, nonce, user_id, event_type):
        if not token:
            raise ValueError('A live-photo challenge token is required.')

        try:
            payload = signing.loads(token, salt=cls.CHALLENGE_SALT, max_age=cls.CHALLENGE_TTL_SECONDS)
        except signing.SignatureExpired as exc:
            raise ValueError('Photo challenge token has expired.') from exc
        except signing.BadSignature as exc:
            raise ValueError('Invalid photo challenge token.') from exc

        expected_keys = {'user_id', 'event_type', 'nonce', 'timestamp'}
        if set(payload.keys()) != expected_keys:
            raise ValueError('Photo challenge token is bound to an invalid payload.')

        if payload.get('user_id') != str(user_id):
            raise ValueError('Photo challenge token does not match the provided user.')
        if payload.get('event_type') != str(event_type):
            raise ValueError('Photo challenge token does not match the provided event type.')
        if payload.get('nonce') != nonce:
            raise ValueError('Photo challenge token nonce mismatch.')

        try:
            timestamp = datetime.fromisoformat(payload.get('timestamp'))
        except (TypeError, ValueError) as exc:
            raise ValueError('Photo challenge token timestamp is invalid.') from exc

        if timezone.is_naive(timestamp):
            timestamp = timezone.make_aware(timestamp, timezone=timezone.utc)

        if timezone.now() - timestamp > timedelta(seconds=cls.CHALLENGE_TTL_SECONDS):
            raise ValueError('Photo challenge token has expired.')

        cache_key = cls._nonce_cache_key(nonce)
        if cache.get(cache_key) == 'used':
            raise ValueError('Photo challenge nonce has already been used.')
        if cache.get(cache_key) is None:
            raise ValueError('Photo challenge nonce is invalid or expired.')

        cache.set(cache_key, 'used', timeout=cls.CHALLENGE_TTL_SECONDS)
        return True


class SecurityPhotoAlertService:
    """Issue safe alerts for rejected security photos without exposing biometric data."""

    @staticmethod
    def reject_photo(user, reason, *, event_type='SECURITY_PHOTO_REJECTION', metadata=None):
        if user is None:
            return None

        safe_metadata = {'reason': reason}
        if metadata:
            safe_metadata.update({
                key: value
                for key, value in metadata.items()
                if key not in {'face_encoding', 'embedding', 'image', 'raw_image', 'photo'}
            })

        return NotificationService.dispatch(
            user,
            event_type,
            metadata=safe_metadata,
            channel='EMAIL',
        )
