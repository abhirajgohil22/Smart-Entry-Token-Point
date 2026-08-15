"""Campus token generation utilities."""

import base64
import json
import os
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from apps.facerecognition.services import LivenessVerificationService
from apps.notifications.services import NotificationService
from apps.security_photos.models import SecurityPhoto
from apps.security_photos.services import LivePhotoService

User = get_user_model()


class TokenGenerationService:
    """Builds and validates campus-entry tokens with mandatory live-photo capture."""

    @staticmethod
    def _build_payload(user, event_type, nonce, photo):
        return {
            'user_id': str(user.pk),
            'event_type': event_type,
            'nonce': nonce,
            'timestamp': timezone.now().isoformat(),
            'photo_name': getattr(photo, 'name', 'live-photo.jpg'),
        }

    @staticmethod
    def ensure_new_live_photo(user, live_photo, *, previous_security_photo_id=None):
        if live_photo is None:
            raise ValueError('A fresh live photo is required to regenerate a token.')

        if previous_security_photo_id:
            previous_photo = SecurityPhoto.objects.filter(user=user, pk=previous_security_photo_id).first()
            if previous_photo is not None:
                raise ValueError('A reused security photo cannot be used for token renewal.')

        live_photo.seek(0)
        incoming_bytes = live_photo.read()
        live_photo.seek(0)

        for previous_photo in SecurityPhoto.objects.filter(user=user).order_by('-captured_at'):
            if not previous_photo.image:
                continue
            try:
                with previous_photo.image.open('rb') as existing_file:
                    existing_bytes = existing_file.read()
                if existing_bytes == incoming_bytes:
                    raise ValueError('A stored or previously used security photo cannot be reused for token renewal.')
            except (FileNotFoundError, OSError):
                continue

        return True

    @staticmethod
    def validate_live_request(user, live_photo, *, event_type='TOKEN_GENERATION'):
        if user is None:
            raise ValueError('A valid student is required.')
        if not getattr(user, 'is_active', False):
            raise ValueError('Student account is inactive.')
        latest_otp = user.otps.order_by('-created_at').first() if hasattr(user, 'otps') else None
        if latest_otp is None or not getattr(latest_otp, 'is_verified', False):
            raise ValueError('Student email must be verified before token generation.')

        if live_photo is None:
            raise ValueError('A fresh live photo is required to generate a token.')
        LivePhotoService.validate(live_photo, field_name='live_photo', user=user)

        return True

    @staticmethod
    def generate_qr_code(payload):
        payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
        encoded = base64.urlsafe_b64encode(payload_json).decode('ascii')
        return encoded

    @staticmethod
    def generate_pdf_pass(user, payload, qr_code):
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle('Campus Entry Pass')
        pdf.setFillColor(colors.HexColor('#0b3d91'))
        pdf.setFont('Helvetica-Bold', 20)
        pdf.drawString(60, 730, 'Smart Campus Entry Pass')
        pdf.setFillColor(colors.black)
        pdf.setFont('Helvetica', 12)
        pdf.drawString(60, 690, f'Student: {user.get_full_name() or user.username}')
        pdf.drawString(60, 670, f'User ID: {user.pk}')
        pdf.drawString(60, 650, f'Event: {payload.get("event_type", "TOKEN_GENERATION")}')
        pdf.drawString(60, 630, f'Issued: {payload.get("timestamp", "")[:19]}')
        pdf.drawString(60, 610, 'QR Payload:')
        pdf.drawString(60, 590, qr_code[:90])
        pdf.drawString(60, 560, 'Valid for the next 60 minutes.')
        pdf.save()
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('ascii')

    @classmethod
    def generate_token(cls, user, live_photo, *, event_type='TOKEN_GENERATION'):
        cls.validate_live_request(user, live_photo, event_type=event_type)

        from apps.tokens.models import CampusToken
        from apps.security_photos.services import PhotoChallengeService

        challenge = PhotoChallengeService.generate_challenge(user.pk, event_type)
        payload = cls._build_payload(user, event_type, challenge['nonce'], live_photo)
        token_value = signing.dumps(payload, salt='campus-entry-token')

        existing = CampusToken.objects.filter(user=user, status='ACTIVE').first()
        if existing:
            raise ValueError('An active token already exists for this student.')

        SecurityPhoto.objects.create(
            user=user,
            event_type='TOKEN_GENERATION',
            image=live_photo,
            request_id=f'token-{user.pk}-{os.urandom(4).hex()}',
            nonce=challenge['nonce'],
            captured_at=timezone.now(),
            verification_status='PENDING',
            face_recognition_status='NOT_RUN',
        )

        if getattr(settings, 'LIVENESS_ENABLED', False):
            frames = [live_photo.read()]
            live_photo.seek(0)
            liveness = LivenessVerificationService().evaluate_frames(frames, challenge='Blink slowly')
            if liveness.status != liveness.status.SUCCESS:
                raise ValueError('Liveness verification failed; please retry with a fresh live capture.')

        expires_at = timezone.now() + timedelta(minutes=60)
        token_record = CampusToken.objects.create(
            user=user,
            token=token_value,
            payload=payload,
            expires_at=expires_at,
            status='ACTIVE',
        )

        qr_code = cls.generate_qr_code(payload)
        pdf_pass = cls.generate_pdf_pass(user, payload, qr_code)

        NotificationService.dispatch(
            user,
            'TOKEN_GENERATED',
            metadata={'token_id': str(token_record.pk), 'expires_at': expires_at.isoformat()},
            channel='EMAIL',
        )

        return {
            'token': token_value,
            'token_id': str(token_record.pk),
            'expires_at': expires_at.isoformat(),
            'payload': payload,
            'qr_code': qr_code,
            'pdf_pass': pdf_pass,
            'challenge': challenge,
        }

    @classmethod
    def regenerate_token(cls, user, token_id, live_photo, *, previous_security_photo_id=None):
        from apps.tokens.models import CampusToken
        from apps.security_photos.services import PhotoChallengeService

        token = CampusToken.objects.filter(pk=token_id, user=user).first()
        if token is None:
            raise ValueError('Token not found or does not belong to this user.')
        if token.status == 'ACTIVE' and token.is_valid():
            raise ValueError('Current token is still valid and cannot be renewed.')
        if token.status == 'REVOKED':
            raise ValueError('This token has already been revoked.')

        cls.validate_live_request(user, live_photo, event_type='TOKEN_REGENERATION')
        cls.ensure_new_live_photo(user, live_photo, previous_security_photo_id=previous_security_photo_id)

        challenge = PhotoChallengeService.generate_challenge(user.pk, 'TOKEN_REGENERATION')
        payload = cls._build_payload(user, 'TOKEN_REGENERATION', challenge['nonce'], live_photo)
        new_token_value = signing.dumps(payload, salt='campus-entry-token')

        token.status = 'REVOKED'
        token.save(update_fields=['status'])

        SecurityPhoto.objects.create(
            user=user,
            event_type='TOKEN_REGENERATION',
            image=live_photo,
            request_id=f'token-regenerate-{user.pk}-{os.urandom(4).hex()}',
            nonce=challenge['nonce'],
            captured_at=timezone.now(),
            verification_status='PENDING',
            face_recognition_status='NOT_RUN',
        )

        expires_at = timezone.now() + timedelta(minutes=60)
        new_token = CampusToken.objects.create(
            user=user,
            token=new_token_value,
            payload=payload,
            expires_at=expires_at,
            status='ACTIVE',
        )

        qr_code = cls.generate_qr_code(payload)
        pdf_pass = cls.generate_pdf_pass(user, payload, qr_code)

        NotificationService.dispatch(
            user,
            'TOKEN_REGENERATED',
            metadata={'token_id': str(new_token.pk), 'previous_token_id': str(token.pk), 'expires_at': expires_at.isoformat()},
            channel='EMAIL',
        )

        return {
            'token': new_token_value,
            'token_id': str(new_token.pk),
            'previous_token_id': str(token.pk),
            'expires_at': expires_at.isoformat(),
            'payload': payload,
            'qr_code': qr_code,
            'pdf_pass': pdf_pass,
            'challenge': challenge,
        }
