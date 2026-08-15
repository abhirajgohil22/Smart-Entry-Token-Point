from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.authentication.models import EmailOTP
from apps.security_photos.models import SecurityPhoto
from apps.tokens.models import CampusToken

User = get_user_model()


class CampusTokenGenerationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='token-user',
            email='token@example.com',
            password='S3cur3Password!',
            is_active=True,
        )
        self.otp = EmailOTP.create_for_user(self.user)
        self.otp.is_verified = True
        self.otp.save(update_fields=['is_verified'])

    def _make_live_photo(self, filename='live-photo.png', size=(64, 64)):
        buffer = BytesIO()
        Image.new('RGB', size, color='blue').save(buffer, format='PNG')
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type='image/png')

    def test_generate_token_requires_live_photo(self):
        response = self.client.post('/api/v1/tokens/generate/', {'user_id': str(self.user.pk)}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('live_photo', response.data)

    def test_generate_token_rejects_unverified_email(self):
        self.otp.is_verified = False
        self.otp.save(update_fields=['is_verified'])

        response = self.client.post(
            '/api/v1/tokens/generate/',
            {'user_id': str(self.user.pk), 'live_photo': self._make_live_photo()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_generate_token_rejects_existing_active_token(self):
        CampusToken.objects.create(
            user=self.user,
            token='existing-token',
            payload='{}',
            expires_at='2099-01-01T00:00:00Z',
            status='ACTIVE',
        )

        response = self.client.post(
            '/api/v1/tokens/generate/',
            {'user_id': str(self.user.pk), 'live_photo': self._make_live_photo()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('active token', response.data['error'].lower())

    @override_settings(FACE_RECOGNITION_ENABLED=False)
    def test_generate_token_success_returns_qr_and_pdf(self):
        response = self.client.post(
            '/api/v1/tokens/generate/',
            {'user_id': str(self.user.pk), 'live_photo': self._make_live_photo()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)
        self.assertIn('qr_code', response.data)
        self.assertIn('pdf_pass', response.data)
        self.assertTrue(CampusToken.objects.filter(user=self.user, status='ACTIVE').exists())

    def test_regenerate_token_rejects_recycled_security_photo_id(self):
        expired_token = CampusToken.objects.create(
            user=self.user,
            token='expired-token',
            payload={'event_type': 'TOKEN_GENERATION'},
            expires_at=timezone.now() - timezone.timedelta(minutes=5),
            status='EXPIRED',
        )
        old_photo = SecurityPhoto.objects.create(
            user=self.user,
            event_type='TOKEN_GENERATION',
            image=self._make_live_photo(filename='old-pass.png', size=(64, 64)),
            request_id='req-old-token',
            nonce='old-nonce',
            captured_at=timezone.now(),
            verification_status='VALIDATED',
            face_recognition_status='SUCCESS',
        )

        response = self.client.post(
            '/api/tokens/regenerate/',
            {
                'token_id': str(expired_token.pk),
                'previous_security_photo_id': str(old_photo.pk),
                'live_photo': self._make_live_photo(filename='reused.png', size=(64, 64)),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('reused', response.data['error'].lower())

    def test_regenerate_token_issues_new_pass_and_revokes_previous_one(self):
        expired_token = CampusToken.objects.create(
            user=self.user,
            token='expired-token-2',
            payload={'event_type': 'TOKEN_GENERATION'},
            expires_at=timezone.now() - timezone.timedelta(minutes=5),
            status='EXPIRED',
        )

        response = self.client.post(
            '/api/tokens/regenerate/',
            {
                'token_id': str(expired_token.pk),
                'live_photo': self._make_live_photo(filename='renewal.png', size=(64, 64)),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)
        expired_token.refresh_from_db()
        self.assertEqual(expired_token.status, 'REVOKED')
        self.assertTrue(CampusToken.objects.filter(user=self.user, status='ACTIVE').exists())
