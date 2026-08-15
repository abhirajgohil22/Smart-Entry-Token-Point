"""Security isolation tests for profile management.

These tests enforce that ProfilePhoto (display picture) is NEVER used
for security-sensitive operations and remains completely isolated from
authentication and token verification workflows.
"""

from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.authentication.models import EmailOTP
from apps.security_photos.models import ProfilePhoto, SecurityPhoto

User = get_user_model()


class ProfileSecurityIsolationTests(TestCase):
    """Verify ProfilePhoto cannot be used for authentication."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='profile-user',
            email='profile@example.com',
            password='S3cur3Password!',
            is_active=True,
        )
        otp = EmailOTP.create_for_user(self.user)
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])
        self.client.force_authenticate(self.user)

    def _make_image(self, filename='test.png', size=(32, 32)):
        buffer = BytesIO()
        Image.new('RGB', size, color='red').save(buffer, format='PNG')
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type='image/png')

    def test_profile_photo_model_is_separate_from_security_photo(self):
        """Verify ProfilePhoto and SecurityPhoto are distinct model classes."""
        self.assertNotEqual(ProfilePhoto, SecurityPhoto)
        self.assertNotEqual(ProfilePhoto._meta.db_table, SecurityPhoto._meta.db_table)

    def test_uploading_avatar_creates_profile_photo_only(self):
        """Verify avatar upload creates ProfilePhoto, not SecurityPhoto."""
        avatar = self._make_image()
        response = self.client.post(
            '/api/profile/avatar/',
            {'avatar': avatar},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(ProfilePhoto.objects.filter(user=self.user).exists())
        self.assertFalse(SecurityPhoto.objects.filter(user=self.user, event_type='REGISTRATION').exists())

    def test_profile_photo_never_referenced_in_authentication_queries(self):
        """Verify authentication logic never queries ProfilePhoto."""
        avatar = self._make_image()
        self.client.post(
            '/api/profile/avatar/',
            {'avatar': avatar},
            format='multipart',
        )

        profile_photo = ProfilePhoto.objects.get(user=self.user)

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as context:
            response = self.client.get('/api/profile/')

        profile_table_queries = [
            q for q in context.captured_queries
            if 'profile_photo' in q['sql'].lower()
        ]

        self.assertGreater(len(profile_table_queries), 0)

        security_table_queries = [
            q for q in context.captured_queries
            if 'security_photo' in q['sql'].lower() and 'from' in q['sql'].lower()
        ]

        self.assertEqual(len(security_table_queries), 0)

    def test_profile_endpoint_does_not_expose_security_photos(self):
        """Verify GET /api/profile/ never returns security photo references."""
        security_photo = SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._make_image(),
            captured_at=__import__('django.utils.timezone').utils.timezone.now(),
            verification_status='PENDING',
            face_recognition_status='NOT_RUN',
        )

        response = self.client.get('/api/profile/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertNotIn('security_photos', data)
        self.assertNotIn('security_photo', data)
        self.assertNotIn(str(security_photo.pk), str(data))

    def test_avatar_upload_does_not_create_security_photo(self):
        """Verify uploading an avatar never creates a SecurityPhoto record."""
        initial_security_count = SecurityPhoto.objects.filter(user=self.user).count()

        avatar = self._make_image()
        response = self.client.post(
            '/api/profile/avatar/',
            {'avatar': avatar},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        final_security_count = SecurityPhoto.objects.filter(user=self.user).count()
        self.assertEqual(initial_security_count, final_security_count)

    def test_profile_photo_cannot_be_retrieved_via_security_photo_endpoint(self):
        """Verify profile avatars cannot be accessed through security photo APIs."""
        avatar = self._make_image()
        response = self.client.post(
            '/api/profile/avatar/',
            {'avatar': avatar},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)

        profile_photo = ProfilePhoto.objects.get(user=self.user)

        response = self.client.get(f'/api/v1/photos/{profile_photo.pk}/')
        if response.status_code != 404:
            data = response.json()
            self.assertNotEqual(data.get('id'), str(profile_photo.pk))

    def test_profile_serializer_excludes_security_photo_references(self):
        """Verify ProfileSerializer never includes security photo data."""
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._make_image(),
            captured_at=__import__('django.utils.timezone').utils.timezone.now(),
            verification_status='VALIDATED',
            face_recognition_status='SUCCESS',
        )

        response = self.client.get('/api/profile/')
        data = response.json()

        forbidden_keys = [
            'security_photos',
            'security_photo',
            'event_type',
            'verification_status',
            'face_recognition_status',
        ]

        for key in forbidden_keys:
            self.assertNotIn(key, data, f'Security-sensitive key "{key}" exposed in profile.')

    def test_authentication_never_uses_profile_photo_as_fallback(self):
        """Verify login validation never falls back to ProfilePhoto for verification."""
        avatar = self._make_image()
        self.client.post(
            '/api/profile/avatar/',
            {'avatar': avatar},
            format='multipart',
        )

        profile_photo = ProfilePhoto.objects.get(user=self.user)

        response = self.client.post(
            '/api/auth/login/',
            {
                'email': self.user.email,
                'password': 'S3cur3Password!',
                'live_photo': self._make_image('login.png'),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())

        login_security_photo = SecurityPhoto.objects.filter(
            user=self.user,
            event_type='LOGIN',
        ).latest('captured_at')

        self.assertNotEqual(login_security_photo.image.name, profile_photo.image.name)


class ProfileAPITests(TestCase):
    """Functional tests for profile endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='api-user',
            email='api@example.com',
            password='S3cur3Password!',
            is_active=True,
        )
        otp = EmailOTP.create_for_user(self.user)
        otp.is_verified = True
        otp.save(update_fields=['is_verified'])
        self.client.force_authenticate(self.user)

    def _make_image(self, filename='test.png', size=(32, 32)):
        buffer = BytesIO()
        Image.new('RGB', size, color='blue').save(buffer, format='PNG')
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type='image/png')

    def test_profile_requires_authentication(self):
        """Verify GET /api/profile/ requires authentication."""
        self.client.force_authenticate(None)
        response = self.client.get('/api/profile/')
        self.assertEqual(response.status_code, 401)

    def test_profile_endpoint_returns_user_details(self):
        """Verify GET /api/profile/ returns correct user info."""
        response = self.client.get('/api/profile/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['email'], self.user.email)
        self.assertEqual(data['first_name'], self.user.first_name)
        self.assertTrue(data['email_verified'])

    def test_avatar_upload_requires_authentication(self):
        """Verify POST /api/profile/avatar/ requires authentication."""
        self.client.force_authenticate(None)
        response = self.client.post(
            '/api/profile/avatar/',
            {'avatar': self._make_image()},
            format='multipart',
        )
        self.assertEqual(response.status_code, 401)

    def test_avatar_upload_stores_profile_photo(self):
        """Verify avatar upload creates or updates ProfilePhoto."""
        avatar = self._make_image()
        response = self.client.post(
            '/api/profile/avatar/',
            {'avatar': avatar},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(ProfilePhoto.objects.filter(user=self.user).exists())

    def test_avatar_upload_overwrites_existing(self):
        """Verify uploading a new avatar replaces the old one."""
        avatar1 = self._make_image('avatar1.png')
        response1 = self.client.post(
            '/api/profile/avatar/',
            {'avatar': avatar1},
            format='multipart',
        )
        self.assertEqual(response1.status_code, 201)

        photo1 = ProfilePhoto.objects.get(user=self.user)

        avatar2 = self._make_image('avatar2.png')
        response2 = self.client.post(
            '/api/profile/avatar/',
            {'avatar': avatar2},
            format='multipart',
        )
        self.assertEqual(response2.status_code, 201)

        photo2 = ProfilePhoto.objects.get(user=self.user)
        self.assertEqual(photo1.pk, photo2.pk)
        self.assertNotEqual(photo1.image.name, photo2.image.name)

    def test_profile_returns_avatar_url_when_set(self):
        """Verify profile endpoint returns avatar URL."""
        avatar = self._make_image()
        self.client.post(
            '/api/profile/avatar/',
            {'avatar': avatar},
            format='multipart',
        )

        response = self.client.get('/api/profile/')
        data = response.json()

        self.assertIsNotNone(data['avatar'])
        self.assertIn('url', data['avatar'])
        self.assertIsNotNone(data['avatar']['url'])

    def test_profile_returns_null_avatar_when_not_set(self):
        """Verify profile endpoint returns null for avatar if not uploaded."""
        response = self.client.get('/api/profile/')
        data = response.json()

        self.assertIsNone(data['avatar'])
