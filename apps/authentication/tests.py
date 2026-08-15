from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.authentication.models import EmailOTP

User = get_user_model()


class RegistrationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.base_payload = {
            'student_id': 'STU-2026-001',
            'full_name': 'Alice Student',
            'email': 'alice@example.com',
            'password': 'S3cur3Password!'
        }

    def _make_live_photo(self, filename='live-photo.png', size=(32, 32)):
        buffer = BytesIO()
        Image.new('RGB', size, color='white').save(buffer, format='PNG')
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type='image/png')

    def test_registration_requires_live_photo(self):
        payload = self.base_payload.copy()
        response = self.client.post('/api/v1/auth/register/', payload, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('live_photo', response.data)

    def test_registration_rejects_invalid_file_type(self):
        payload = self.base_payload.copy()
        payload['live_photo'] = SimpleUploadedFile(
            'bad.txt',
            b'not an image',
            content_type='text/plain',
        )

        response = self.client.post('/api/v1/auth/register/', payload, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('live_photo', response.data)

    def test_registration_rejects_duplicate_email(self):
        User.objects.create_user(
            username='existing-user',
            email='alice@example.com',
            password='S3cur3Password!'
        )

        payload = self.base_payload.copy()
        payload['live_photo'] = self._make_live_photo()

        response = self.client.post('/api/v1/auth/register/', payload, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    @override_settings(FACE_RECOGNITION_ENABLED=False)
    def test_registration_skips_face_encoding_when_disabled(self):
        payload = self.base_payload.copy()
        payload['live_photo'] = self._make_live_photo()

        response = self.client.post('/api/v1/auth/register/', payload, format='multipart')

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='alice@example.com')
        self.assertFalse(hasattr(user, 'face_encoding'))
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(FACE_RECOGNITION_ENABLED=True)
    @patch('apps.authentication.serializers.FaceRecognitionService')
    def test_registration_extracts_face_encoding_when_enabled(self, mock_service_factory):
        mock_service = mock_service_factory.return_value
        mock_service.generate_face_embedding.return_value = SimpleNamespace(
            success=True,
            data={'embedding': [0.1, 0.2, 0.3]},
        )

        payload = self.base_payload.copy()
        payload['live_photo'] = self._make_live_photo()

        response = self.client.post('/api/v1/auth/register/', payload, format='multipart')

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='alice@example.com')
        self.assertIsNotNone(user.face_encoding)
        self.assertEqual(len(mail.outbox), 1)

    def test_login_requires_live_photo(self):
        user = User.objects.create_user(
            username='login-user',
            email='login@example.com',
            password='S3cur3Password!',
            is_active=True,
        )
        otp = EmailOTP.create_for_user(user)
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])

        payload = {
            'email': 'login@example.com',
            'password': 'S3cur3Password!',
        }

        response = self.client.post('/api/auth/login/', payload, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('live_photo', response.data)

    def test_login_rejects_invalid_credentials(self):
        user = User.objects.create_user(
            username='login-user-2',
            email='login2@example.com',
            password='S3cur3Password!',
            is_active=True,
        )
        otp = EmailOTP.create_for_user(user)
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])

        payload = {
            'email': 'login2@example.com',
            'password': 'wrong-password',
            'live_photo': self._make_live_photo(),
        }

        response = self.client.post('/api/auth/login/', payload, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('non_field_errors', response.data)

    def test_login_rejects_unverified_email(self):
        user = User.objects.create_user(
            username='unverified-user',
            email='unverified@example.com',
            password='S3cur3Password!',
            is_active=True,
        )
        otp = EmailOTP.create_for_user(user)
        otp.is_verified = False
        otp.save(update_fields=['is_verified'])

        payload = {
            'email': 'unverified@example.com',
            'password': 'S3cur3Password!',
            'live_photo': self._make_live_photo(),
        }

        response = self.client.post('/api/auth/login/', payload, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_login_success_returns_jwt_tokens(self):
        user = User.objects.create_user(
            username='verified-user',
            email='verified@example.com',
            password='S3cur3Password!',
            is_active=True,
        )
        otp = EmailOTP.create_for_user(user)
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])

        payload = {
            'email': 'verified@example.com',
            'password': 'S3cur3Password!',
            'live_photo': self._make_live_photo(),
        }

        response = self.client.post('/api/auth/login/', payload, format='multipart')

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['email'], 'verified@example.com')

    def test_login_is_rate_limited(self):
        user = User.objects.create_user(
            username='rate-limited-user',
            email='rate@example.com',
            password='S3cur3Password!',
            is_active=True,
        )
        otp = EmailOTP.create_for_user(user)
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])

        with self.settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, 'DEFAULT_THROTTLE_RATES': {'login': '2/min'}}):
            for index in range(3):
                payload = {
                    'email': 'rate@example.com',
                    'password': 'wrong-password' if index < 2 else 'S3cur3Password!',
                    'live_photo': self._make_live_photo(),
                }
                response = self.client.post('/api/auth/login/', payload, format='multipart')
                if index < 2:
                    self.assertIn(response.status_code, [400])
                else:
                    self.assertEqual(response.status_code, 429)

