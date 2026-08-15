"""Tests for admin functionality and photo cleanup management command."""

from datetime import timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.notifications.models import NotificationLog
from apps.security_photos.models import SecurityPhoto

User = get_user_model()


class PhotoCleanupCommandTests(TestCase):
    """Tests for the cleanup_old_photos management command."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='test-cleanup',
            email='cleanup@example.com',
            password='S3cur3Password!',
            is_staff=True,
        )

    def _create_test_image(self):
        """Create a minimal valid test image file."""
        img = SimpleUploadedFile(
            name='test.jpg',
            content=b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 100 + b'\xff\xd9',
            content_type='image/jpeg',
        )
        return img

    def test_cleanup_deletes_old_photos(self):
        """Test that old security photos are deleted."""
        old_date = timezone.now() - timedelta(days=40)
        photo = SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='old-photo-1',
            nonce='old-nonce-1',
            captured_at=old_date,
            verification_status='VALIDATED',
            ip_address='192.168.1.1',
        )

        self.assertEqual(SecurityPhoto.objects.count(), 1)
        call_command('cleanup_old_photos', '--days=30')
        self.assertEqual(SecurityPhoto.objects.count(), 0)

    def test_cleanup_preserves_retention_held_photos(self):
        """Test that photos with retention holds are not deleted."""
        old_date = timezone.now() - timedelta(days=40)
        future_date = timezone.now() + timedelta(days=30)

        photo = SecurityPhoto.objects.create(
            user=self.user,
            event_type='TOKEN_GENERATION',
            image=self._create_test_image(),
            request_id='retained-photo-1',
            nonce='retained-nonce-1',
            captured_at=old_date,
            verification_status='VALIDATED',
            ip_address='192.168.1.1',
            retention_until=future_date,  # Admin hold
        )

        self.assertEqual(SecurityPhoto.objects.count(), 1)
        call_command('cleanup_old_photos', '--days=30')
        self.assertEqual(SecurityPhoto.objects.count(), 1)
        self.assertTrue(SecurityPhoto.objects.filter(pk=photo.pk).exists())

    def test_cleanup_preserves_recent_photos(self):
        """Test that recent photos are not deleted."""
        recent_date = timezone.now() - timedelta(days=10)

        photo = SecurityPhoto.objects.create(
            user=self.user,
            event_type='REGISTRATION',
            image=self._create_test_image(),
            request_id='recent-photo-1',
            nonce='recent-nonce-1',
            captured_at=recent_date,
            verification_status='VALIDATED',
            ip_address='192.168.1.1',
        )

        self.assertEqual(SecurityPhoto.objects.count(), 1)
        call_command('cleanup_old_photos', '--days=30')
        self.assertEqual(SecurityPhoto.objects.count(), 1)

    def test_cleanup_dry_run_does_not_delete(self):
        """Test that --dry-run flag does not actually delete photos."""
        old_date = timezone.now() - timedelta(days=40)

        photo = SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='dryrun-photo-1',
            nonce='dryrun-nonce-1',
            captured_at=old_date,
            verification_status='VALIDATED',
            ip_address='192.168.1.1',
        )

        self.assertEqual(SecurityPhoto.objects.count(), 1)
        call_command('cleanup_old_photos', '--days=30', '--dry-run')
        self.assertEqual(SecurityPhoto.objects.count(), 1)

    def test_cleanup_with_custom_days(self):
        """Test cleanup with custom retention period."""
        old_date = timezone.now() - timedelta(days=20)

        photo = SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='custom-days-photo-1',
            nonce='custom-days-nonce-1',
            captured_at=old_date,
            verification_status='VALIDATED',
            ip_address='192.168.1.1',
        )

        self.assertEqual(SecurityPhoto.objects.count(), 1)
        call_command('cleanup_old_photos', '--days=10')
        self.assertEqual(SecurityPhoto.objects.count(), 0)


class SecurityPhotoAdminTests(TestCase):
    """Tests for SecurityPhoto admin customizations."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='AdminPass123!',
        )
        self.regular_user = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='S3cur3Password!',
        )

    def _create_test_image(self):
        """Create a minimal valid test image file."""
        img = SimpleUploadedFile(
            name='test.jpg',
            content=b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 100 + b'\xff\xd9',
            content_type='image/jpeg',
        )
        return img

    def test_security_photo_admin_read_only_fields(self):
        """Test that sensitive fields are read-only in admin."""
        from apps.security_photos.admin import SecurityPhotoAdmin

        admin_instance = SecurityPhotoAdmin(SecurityPhoto, MagicMock())
        readonly = admin_instance.readonly_fields

        expected_readonly = [
            'id', 'user', 'event_type', 'image', 'request_id', 'nonce',
            'captured_at', 'face_recognition_status', 'face_confidence',
            'ip_address', 'user_agent', 'created_at', 'retention_until', 'image_preview'
        ]

        for field in expected_readonly:
            self.assertIn(field, readonly, f'Field {field} should be read-only')

    def test_security_photo_admin_no_add_permission(self):
        """Test that admins cannot manually add security photos."""
        from apps.security_photos.admin import SecurityPhotoAdmin

        admin_instance = SecurityPhotoAdmin(SecurityPhoto, MagicMock())
        mock_request = MagicMock()
        mock_request.user.is_superuser = True

        can_add = admin_instance.has_add_permission(mock_request)
        self.assertFalse(can_add, 'Should not allow manual creation of security photos')

    def test_notification_log_admin_has_no_add_permission(self):
        """Test that admins cannot manually add notification records."""
        from apps.notifications.admin import NotificationLogAdmin

        admin_instance = NotificationLogAdmin(NotificationLog, MagicMock())
        mock_request = MagicMock()
        mock_request.user.is_superuser = True

        can_add = admin_instance.has_add_permission(mock_request)
        self.assertFalse(can_add, 'Should not allow manual creation of notifications')
