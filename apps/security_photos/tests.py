from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework import serializers
from rest_framework.test import APIClient

from apps.authentication.models import EmailOTP

from apps.facerecognition.models import UserFaceEncoding
from apps.security_photos.models import ProfilePhoto, SecurityPhoto
from apps.security_photos.services import LivePhotoService, PhotoChallengeService


class SecurityPhotoModelTests(TestCase):
    def test_security_photo_model_has_event_tracking_fields(self):
        field_names = {field.name for field in SecurityPhoto._meta.get_fields()}

        self.assertIn('user', field_names)
        self.assertIn('event_type', field_names)
        self.assertIn('image', field_names)
        self.assertIn('request_id', field_names)
        self.assertIn('nonce', field_names)
        self.assertIn('captured_at', field_names)
        self.assertIn('verification_status', field_names)
        self.assertIn('face_recognition_status', field_names)
        self.assertIn('face_confidence', field_names)
        self.assertIn('ip_address', field_names)
        self.assertIn('user_agent', field_names)
        self.assertIn('retention_until', field_names)

    def test_security_photo_has_indexes_for_event_tracking(self):
        index_names = {index.name for index in SecurityPhoto._meta.indexes}

        self.assertIn('idx_security_photo_user', index_names)
        self.assertIn('idx_security_photo_event', index_names)
        self.assertIn('idx_security_photo_captured', index_names)
        self.assertIn('idx_photo_verif_status', index_names)

    def test_profile_photo_is_separate_model_from_security_photo(self):
        profile_fields = {field.name for field in ProfilePhoto._meta.get_fields()}

        self.assertIn('image', profile_fields)
        self.assertNotIn('request_id', profile_fields)
        self.assertNotIn('event_type', profile_fields)
        self.assertNotIn('captured_at', profile_fields)
        self.assertNotIn('verification_status', profile_fields)

    def test_user_face_encoding_is_separate_from_security_photo(self):
        user_face_fields = {field.name for field in UserFaceEncoding._meta.get_fields()}

        self.assertIn('encoding', user_face_fields)
        self.assertIn('user', user_face_fields)
        self.assertNotIn('event_type', user_face_fields)


class SecurityPhotoReadinessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='alice',
            email='alice@example.com',
            password='S3cur3Passw0rd!'
        )

    def test_security_photo_can_be_created_with_required_fields(self):
        photo = SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image='security_photos/test.jpg',
            request_id='req-123',
            nonce='nonce-123',
            captured_at='2026-08-15T12:00:00Z',
            verification_status='PENDING',
            face_recognition_status='NOT_RUN',
            ip_address='127.0.0.1',
            user_agent='pytest-agent',
        )

        self.assertEqual(photo.user, self.user)
        self.assertEqual(photo.event_type, 'LOGIN')


class LivePhotoServiceTests(TestCase):
    def test_valid_jpeg_is_accepted(self):
        image = Image.new('RGB', (120, 120), color='blue')
        buffer = BytesIO()
        image.save(buffer, format='JPEG')
        uploaded = SimpleUploadedFile('photo.jpg', buffer.getvalue(), content_type='image/jpeg')

        validated = LivePhotoService.validate(uploaded)

        self.assertEqual(validated.name, 'photo.jpg')

    def test_invalid_mime_type_is_rejected(self):
        uploaded = SimpleUploadedFile('photo.txt', b'not an image', content_type='text/plain')

        with self.assertRaises(serializers.ValidationError):
            LivePhotoService.validate(uploaded)

    def test_large_image_is_rejected(self):
        image = Image.new('RGB', (6000, 6000), color='blue')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        uploaded = SimpleUploadedFile('large.png', buffer.getvalue(), content_type='image/png')

        with self.assertRaises(serializers.ValidationError):
            LivePhotoService.validate(uploaded)


class SecurityPhotoChallengeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='bob',
            email='bob@example.com',
            password='S3cur3Passw0rd!'
        )

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'phase7-tests'}})
    def test_challenge_endpoint_generates_nonce_and_photo_verification_token(self):
        response = self.client.post('/api/security/challenge/', {'user_id': str(self.user.pk), 'event_type': 'LOGIN'}, format='json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('nonce', data)
        self.assertIn('photo_verification_token', data)
        self.assertEqual(data['user_id'], str(self.user.pk))
        self.assertEqual(data['event_type'], 'LOGIN')
        self.assertLessEqual(data['expires_in'], 60)

        self.assertTrue(PhotoChallengeService.validate_challenge(
            data['photo_verification_token'],
            nonce=data['nonce'],
            user_id=str(self.user.pk),
            event_type='LOGIN',
        ))

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'phase7-tests'}})
    def test_nonce_is_single_use_and_replay_is_rejected(self):
        challenge = PhotoChallengeService.generate_challenge(self.user.pk, 'LOGIN')

        self.assertTrue(PhotoChallengeService.validate_challenge(
            challenge['photo_verification_token'],
            nonce=challenge['nonce'],
            user_id=str(self.user.pk),
            event_type='LOGIN',
        ))

        with self.assertRaises(ValueError):
            PhotoChallengeService.validate_challenge(
                challenge['photo_verification_token'],
                nonce=challenge['nonce'],
                user_id=str(self.user.pk),
                event_type='LOGIN',
            )

    def test_expired_photo_challenge_token_is_rejected(self):
        expired_time = (timezone.now() - timedelta(seconds=120)).isoformat()
        payload = {
            'user_id': str(self.user.pk),
            'event_type': 'LOGIN',
            'nonce': 'expired-nonce',
            'timestamp': expired_time,
        }
        token = signing.dumps(payload, salt='security-photo-challenge')

        with self.assertRaises(ValueError):
            PhotoChallengeService.validate_challenge(
                token,
                nonce='expired-nonce',
                user_id=str(self.user.pk),
                event_type='LOGIN',
            )


class SecurityVerificationChecklistTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='security-audit-user',
            email='security-audit@example.com',
            password='S3cur3Passw0rd!',
            is_active=True,
        )
        otp = EmailOTP.create_for_user(self.user)
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])
        self.client.force_authenticate(self.user)

    def _make_live_photo(self, filename='live-photo.png', size=(64, 64), color=(10, 20, 30)):
        buffer = BytesIO()
        Image.new('RGB', size, color=color).save(buffer, format='PNG')
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type='image/png')

    def test_registration_requires_fresh_live_photo(self):
        payload = {
            'student_id': 'STU-SEC-001',
            'full_name': 'Security Audit User',
            'email': 'new-security-user@example.com',
            'password': 'S3cur3Passw0rd!',
        }

        response = self.client.post('/api/v1/auth/register/', payload, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('live_photo', response.data)

    def test_login_requires_fresh_live_photo(self):
        response = self.client.post(
            '/api/auth/login/',
            {'email': self.user.email, 'password': 'S3cur3Passw0rd!'},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('live_photo', response.data)

    def test_token_generation_requires_fresh_live_photo(self):
        response = self.client.post(
            '/api/v1/tokens/generate/',
            {'user_id': str(self.user.pk)},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('live_photo', response.data)

    def test_token_regeneration_requires_fresh_live_photo(self):
        token = self.user.campus_tokens.create(
            token='expired-audit-token',
            payload={'event_type': 'TOKEN_GENERATION'},
            expires_at=timezone.now() - timezone.timedelta(minutes=10),
            status='EXPIRED',
        )

        response = self.client.post(
            '/api/v1/tokens/regenerate/',
            {'token_id': str(token.pk)},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('live_photo', response.data)

    def test_nonce_replay_is_rejected(self):
        challenge = PhotoChallengeService.generate_challenge(self.user.pk, 'LOGIN')

        self.assertTrue(PhotoChallengeService.validate_challenge(
            challenge['photo_verification_token'],
            nonce=challenge['nonce'],
            user_id=str(self.user.pk),
            event_type='LOGIN',
        ))

        with self.assertRaises(ValueError):
            PhotoChallengeService.validate_challenge(
                challenge['photo_verification_token'],
                nonce=challenge['nonce'],
                user_id=str(self.user.pk),
                event_type='LOGIN',
            )

    def test_profile_avatar_cannot_satisfy_live_photo_requirement(self):
        avatar = self._make_live_photo(filename='avatar.png', color=(200, 10, 10))
        profile_upload = self.client.post('/api/profile/avatar/', {'avatar': avatar}, format='multipart')
        self.assertEqual(profile_upload.status_code, 201)

        avatar_bytes = avatar.read()
        avatar.seek(0)
        login_avatar = SimpleUploadedFile('avatar-login.png', avatar_bytes, content_type='image/png')

        auth_client = APIClient()
        auth_client.force_authenticate(self.user)
        response = auth_client.post(
            '/api/auth/login/',
            {
                'email': self.user.email,
                'password': 'S3cur3Passw0rd!',
                'live_photo': login_avatar,
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('live_photo', response.data)

    def test_gallery_image_file_is_rejected_by_live_photo_validator(self):
        invalid_file = SimpleUploadedFile('gallery-upload.jpg', b'not-a-real-image', content_type='image/jpeg')

        response = self.client.post(
            '/api/v1/auth/register/',
            {
                'student_id': 'STU-SEC-002',
                'full_name': 'Gallery Rejected',
                'email': 'gallery-rejected@example.com',
                'password': 'S3cur3Passw0rd!',
                'live_photo': invalid_file,
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('live_photo', response.data)

    @override_settings(FACE_RECOGNITION_ENABLED=False)
    def test_system_operates_normally_when_face_recognition_disabled(self):
        payload = {
            'student_id': 'STU-FR-OFF',
            'full_name': 'Face Recognition Off',
            'email': 'fr-off@example.com',
            'password': 'S3cur3Passw0rd!',
            'live_photo': self._make_live_photo(filename='fr-off.png', color=(10, 20, 30)),
        }

        response = self.client.post('/api/v1/auth/register/', payload, format='multipart')
        self.assertEqual(response.status_code, 201)

        user = get_user_model().objects.get(email='fr-off@example.com')
        otp = EmailOTP.objects.filter(user=user).latest('created_at')
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])

        login_response = self.client.post(
            '/api/auth/login/',
            {'email': 'fr-off@example.com', 'password': 'S3cur3Passw0rd!', 'live_photo': self._make_live_photo(filename='login-fr-off.png', color=(40, 60, 80))},
            format='multipart',
        )
        self.assertEqual(login_response.status_code, 200)

        token_response = self.client.post(
            '/api/v1/tokens/generate/',
            {'user_id': str(user.pk), 'live_photo': self._make_live_photo(filename='token-fr-off.png', color=(70, 90, 110))},
            format='multipart',
        )
        self.assertEqual(token_response.status_code, 200)

        expired_token = user.campus_tokens.filter(status='ACTIVE').first()
        expired_token.status = 'EXPIRED'
        expired_token.expires_at = timezone.now() - timezone.timedelta(minutes=5)
        expired_token.save(update_fields=['status', 'expires_at'])

        regenerate_response = self.client.post(
            '/api/v1/tokens/regenerate/',
            {'token_id': str(expired_token.pk), 'live_photo': self._make_live_photo(filename='regen-fr-off.png', color=(110, 130, 150))},
            format='multipart',
        )
        self.assertEqual(regenerate_response.status_code, 200)

    @override_settings(FACE_RECOGNITION_ENABLED=False)
    def test_all_four_flows_complete_when_face_matching_is_skipped(self):
        registration = self.client.post(
            '/api/v1/auth/register/',
            {
                'student_id': 'STU-NO-FACE',
                'full_name': 'Face Matching Skipped',
                'email': 'no-face@example.com',
                'password': 'S3cur3Passw0rd!',
                'live_photo': self._make_live_photo(filename='reg-no-face.png', color=(5, 15, 25)),
            },
            format='multipart',
        )
        self.assertEqual(registration.status_code, 201)

        verified_user = get_user_model().objects.get(email='no-face@example.com')
        otp = EmailOTP.objects.filter(user=verified_user).latest('created_at')
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])

        login = self.client.post(
            '/api/auth/login/',
            {'email': verified_user.email, 'password': 'S3cur3Passw0rd!', 'live_photo': self._make_live_photo(filename='login-no-face.png', color=(25, 35, 45))},
            format='multipart',
        )
        self.assertEqual(login.status_code, 200)

        token_generate = self.client.post(
            '/api/v1/tokens/generate/',
            {'user_id': str(verified_user.pk), 'live_photo': self._make_live_photo(filename='token-no-face.png', color=(45, 55, 65))},
            format='multipart',
        )
        self.assertEqual(token_generate.status_code, 200)

        token = verified_user.campus_tokens.filter(status='ACTIVE').first()
        token.status = 'EXPIRED'
        token.expires_at = timezone.now() - timezone.timedelta(minutes=5)
        token.save(update_fields=['status', 'expires_at'])

        token_regen = self.client.post(
            '/api/v1/tokens/regenerate/',
            {'token_id': str(token.pk), 'live_photo': self._make_live_photo(filename='regen-no-face.png', color=(65, 75, 85))},
            format='multipart',
        )
        self.assertEqual(token_regen.status_code, 200)
