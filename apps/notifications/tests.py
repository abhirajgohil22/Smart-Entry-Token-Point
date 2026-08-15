from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.notifications.services import NotificationService

User = get_user_model()


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notify-user',
            email='notify@example.com',
            password='S3cur3Password!',
            is_active=True,
        )

    @patch('apps.notifications.services.send_mail')
    def test_dispatch_email_notification_is_logged_and_safe(self, mock_send_mail):
        log = NotificationService.dispatch(
            self.user,
            'TOKEN_GENERATED',
            metadata={'token_id': 'abc-123', 'face_encoding': [1, 2, 3], 'image': 'hidden'},
        )

        self.assertEqual(log.status, 'SENT')
        self.assertIn('token', log.message.lower())
        self.assertNotIn('face_encoding', str(log.metadata))
        self.assertNotIn('image', str(log.metadata))
        mock_send_mail.assert_called_once()

    @patch('apps.notifications.services.send_mail')
    def test_dispatch_rejection_event_omits_biometric_payloads(self, mock_send_mail):
        log = NotificationService.dispatch(
            self.user,
            'SECURITY_PHOTO_REJECTION',
            metadata={'reason': 'reused-photo', 'embedding': [0.2, 0.3], 'photo_id': '123'},
        )

        self.assertEqual(log.status, 'SENT')
        self.assertIn('rejected', log.message.lower())
        self.assertNotIn('embedding', str(log.metadata))
        self.assertNotIn('raw_image', str(log.metadata))
        mock_send_mail.assert_called_once()
