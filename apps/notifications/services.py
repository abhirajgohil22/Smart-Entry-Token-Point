"""Safe notification dispatchers for security and token lifecycle events."""

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.notifications.models import NotificationLog


class NotificationService:
    """Dispatch privacy-safe notifications to email and dashboard log storage."""

    EVENT_TEMPLATES = {
        'EMAIL_VERIFICATION': {
            'subject': 'Verify your Smart Campus account',
            'message': 'Use the verification code to complete your account setup and keep your campus access secure.',
        },
        'LOGIN_NEW_IP': {
            'subject': 'New sign-in detected',
            'message': 'We detected a sign-in from a new device or IP address. If this was not you, contact support immediately.',
        },
        'TOKEN_GENERATED': {
            'subject': 'Campus token generated',
            'message': 'Your campus access token has been generated successfully. Please keep your device and access record secure.',
        },
        'TOKEN_REGENERATED': {
            'subject': 'Campus token renewed',
            'message': 'Your campus access token has been renewed and the previous token has been invalidated.',
        },
        'TOKEN_EXPIRING': {
            'subject': 'Campus token expiring soon',
            'message': 'Your campus access token is nearing expiry. Please renew it before it expires to avoid access interruption.',
        },
        'SECURITY_PHOTO_REJECTION': {
            'subject': 'Security photo rejected',
            'message': 'A security photo request was rejected. No biometric data or facial images were stored with the alert.',
        },
    }

    @classmethod
    def _normalize_metadata(cls, metadata=None):
        safe = metadata or {}
        if not isinstance(safe, dict):
            safe = {'value': safe}
        return {
            key: value
            for key, value in safe.items()
            if key not in {'face_encoding', 'embedding', 'image', 'photo', 'raw_image'}
        }

    @classmethod
    def dispatch(cls, user, event_type, *, metadata=None, channel='BOTH', email_only=False):
        if user is None or getattr(user, 'email', None) in (None, ''):
            return None

        event_type = str(event_type).upper()
        template = cls.EVENT_TEMPLATES.get(event_type, {
            'subject': 'Campus security alert',
            'message': 'A campus security alert was triggered for your account.',
        })

        safe_metadata = cls._normalize_metadata(metadata)
        subject = template['subject']
        message = template['message']

        if 'OTP' in event_type or 'VERIFICATION' in event_type:
            code = safe_metadata.get('otp_code')
            if code:
                message = f'Your verification code is {code}. Please enter it to complete your account verification.'
        elif event_type == 'TOKEN_GENERATED' and safe_metadata.get('token_id'):
            message = f'Your campus access token has been generated successfully. Token ID: {safe_metadata["token_id"]}'
        elif event_type == 'TOKEN_REGENERATED' and safe_metadata.get('token_id'):
            message = f'Your campus access token has been renewed successfully. New token ID: {safe_metadata["token_id"]}'
        elif event_type == 'TOKEN_EXPIRING' and safe_metadata.get('expires_in_minutes'):
            message = f'Your campus access token expires in {safe_metadata["expires_in_minutes"]} minutes. Please renew it before expiry.'

        log = NotificationLog.objects.create(
            user=user,
            event_type=event_type,
            channel=channel if not email_only else 'EMAIL',
            status='QUEUED',
            subject=subject,
            message=message,
            metadata=safe_metadata,
        )

        if channel in ('EMAIL', 'BOTH'):
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                log.status = 'SENT'
                log.sent_at = timezone.now()
                log.save(update_fields=['status', 'sent_at'])
            except Exception as exc:  # pragma: no cover - network/email failures
                log.status = 'FAILED'
                log.error_message = str(exc)
                log.save(update_fields=['status', 'error_message'])

        if channel == 'SYSTEM':
            log.status = 'SENT'
            log.sent_at = timezone.now()
            log.save(update_fields=['status', 'sent_at'])

        return log
