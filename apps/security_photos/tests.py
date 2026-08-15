from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.facerecognition.models import UserFaceEncoding
from apps.security_photos.models import ProfilePhoto, SecurityPhoto


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
