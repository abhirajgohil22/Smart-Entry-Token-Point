import imghdr
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from rest_framework import serializers

from apps.authentication.models import EmailOTP
from apps.facerecognition.services import FaceRecognitionService
from apps.security_photos.models import SecurityPhoto

User = get_user_model()


class LivePhotoService:
    """Shared validation and normalization for mandatory live-photo capture."""

    @staticmethod
    def validate(image, *, field_name='live_photo'):
        if image is None:
            raise serializers.ValidationError(f'{field_name} is required.')

        if not hasattr(image, 'read'):
            raise serializers.ValidationError(f'{field_name} is invalid.')

        image.seek(0, os.SEEK_END)
        size = image.tell()
        image.seek(0)

        if size == 0 or size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Live photo must be between 1 byte and 5 MB.')

        content_type = getattr(image, 'content_type', '') or ''
        allowed_mimes = {'image/jpeg', 'image/png'}
        if content_type and content_type not in allowed_mimes:
            raise serializers.ValidationError('Only PNG and JPEG images are allowed.')

        if hasattr(image, 'read'):
            chunk = image.read(2048)
            image.seek(0)
            detected = imghdr.what(None, h=chunk)
            if detected not in {'jpeg', 'png'}:
                raise serializers.ValidationError('Live photo is not a valid image.')

        return image


class RegistrationSerializer(serializers.Serializer):
    student_id = serializers.CharField(max_length=32)
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    live_photo = serializers.ImageField(required=True, write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_live_photo(self, value):
        return LivePhotoService.validate(value, field_name='live_photo')

    def create(self, validated_data):
        live_photo = validated_data.pop('live_photo')
        email = validated_data['email']
        user = User.objects.create_user(
            username=validated_data['student_id'],
            email=email,
            password=validated_data['password'],
            first_name=validated_data['full_name'].split()[0],
            last_name=' '.join(validated_data['full_name'].split()[1:]) or 'Student',
        )

        SecurityPhoto.objects.create(
            user=user,
            event_type='REGISTRATION',
            image=live_photo,
            request_id=f'reg-{user.pk}-{os.urandom(4).hex()}',
            nonce=f'nonce-{user.pk}-{os.urandom(6).hex()}',
            captured_at=__import__('django.utils.timezone').utils.timezone.now(),
            verification_status='PENDING',
            face_recognition_status='NOT_RUN',
            ip_address='127.0.0.1',
            user_agent='registration-server',
        )

        otp = EmailOTP.create_for_user(user, purpose='REGISTRATION')
        send_mail(
            subject='Your Smart Campus OTP',
            message=f'Your registration verification code is: {otp.code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        if settings.FACE_RECOGNITION_ENABLED:
            service = FaceRecognitionService()
            result = service.generate_face_embedding(live_photo.read())
            if result and getattr(result, 'success', False):
                embedding = result.data.get('embedding') or result.data.get('face_embedding') or []
                if embedding:
                    from apps.facerecognition.models import UserFaceEncoding

                    UserFaceEncoding.objects.update_or_create(
                        user=user,
                        defaults={'encoding': embedding, 'model_name': 'facenet', 'confidence': result.data.get('confidence')},
                    )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    live_photo = serializers.ImageField(required=True, write_only=True)

    def validate_email(self, value):
        return value.lower()

    def validate_live_photo(self, value):
        return LivePhotoService.validate(value, field_name='live_photo')

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = User.objects.filter(email__iexact=email).first()

        if user is None or not user.check_password(password):
            raise serializers.ValidationError('Invalid email or password.')

        if not user.is_active:
            raise serializers.ValidationError({'email': 'This account is inactive.'})

        latest_otp = EmailOTP.objects.filter(user=user).order_by('-created_at').first()
        if latest_otp is None or not latest_otp.is_verified:
            raise serializers.ValidationError({'email': 'Email must be verified before login.'})

        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        return validated_data['user']
