"""Tests for analytics and reporting functionality."""

from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APITestCase

from apps.tokens.models import CampusToken
from apps.security_photos.models import SecurityPhoto
from apps.tokens.analytics import (
    TokenAnalyticsService,
    PhotoValidationAnalyticsService,
    BiometricSubsystemAnalyticsService,
    SystemHealthAnalyticsService,
)
from apps.tokens.exports import ExcelReportGenerator, PDFReportGenerator

User = get_user_model()


class TokenAnalyticsServiceTests(TestCase):
    """Tests for token analytics service."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='analytics-user',
            email='analytics@example.com',
            password='S3cur3Password!',
        )

    def test_get_daily_token_volume(self):
        """Test daily token volume calculation."""
        # Create tokens for different days
        today = timezone.now()
        yesterday = today - timedelta(days=1)

        CampusToken.objects.create(
            user=self.user,
            token='token1-daily',
            expires_at=today + timedelta(hours=1),
            status='ACTIVE',
            created_at=today,
        )
        CampusToken.objects.create(
            user=self.user,
            token='token2-daily',
            expires_at=today + timedelta(hours=1),
            status='ACTIVE',
            created_at=today,
        )
        CampusToken.objects.create(
            user=self.user,
            token='token3-daily',
            expires_at=yesterday + timedelta(hours=1),
            status='REVOKED',
            created_at=yesterday,
        )

        daily_volume = TokenAnalyticsService.get_daily_token_volume(today - timedelta(days=2), today + timedelta(days=1))
        
        self.assertGreater(len(daily_volume), 0)
        today_data = [d for d in daily_volume if d['date'] == today.date().isoformat()]
        self.assertEqual(len(today_data), 1)
        self.assertGreaterEqual(today_data[0]['total'], 2)
        self.assertGreaterEqual(today_data[0]['ACTIVE'], 2)

    def test_get_weekly_token_volume(self):
        """Test weekly token volume calculation."""
        CampusToken.objects.create(
            user=self.user,
            token='token-weekly-1',
            expires_at=timezone.now() + timedelta(hours=1),
            status='ACTIVE',
        )

        weekly_volume = TokenAnalyticsService.get_weekly_token_volume()
        
        self.assertGreater(len(weekly_volume), 0)
        self.assertEqual(weekly_volume[-1]['total'], 1)

    def test_get_token_status_summary(self):
        """Test token status summary."""
        CampusToken.objects.create(
            user=self.user,
            token='active-token',
            expires_at=timezone.now() + timedelta(hours=1),
            status='ACTIVE',
        )
        CampusToken.objects.create(
            user=self.user,
            token='revoked-token',
            expires_at=timezone.now() + timedelta(hours=1),
            status='REVOKED',
        )

        summary = TokenAnalyticsService.get_token_status_summary()
        
        status_dict = {s['status']: s['count'] for s in summary}
        self.assertEqual(status_dict['ACTIVE'], 1)
        self.assertEqual(status_dict['REVOKED'], 1)


class PhotoValidationAnalyticsServiceTests(TestCase):
    """Tests for photo validation analytics service."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='photo-user',
            email='photo@example.com',
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

    def test_get_validation_success_rate(self):
        """Test validation success rate calculation."""
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='req-1',
            nonce='nonce-1',
            captured_at=timezone.now(),
            verification_status='VALIDATED',
        )
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='req-2',
            nonce='nonce-2',
            captured_at=timezone.now(),
            verification_status='REJECTED',
        )

        result = PhotoValidationAnalyticsService.get_validation_success_rate()
        
        self.assertEqual(result['validated'], 1)
        self.assertEqual(result['rejected'], 1)
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['success_rate'], 50.0)

    def test_get_validation_by_event_type(self):
        """Test validation breakdown by event type."""
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='REGISTRATION',
            image=self._create_test_image(),
            request_id='reg-1',
            nonce='nonce-reg-1',
            captured_at=timezone.now(),
            verification_status='VALIDATED',
        )
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='login-1',
            nonce='nonce-login-1',
            captured_at=timezone.now(),
            verification_status='REJECTED',
        )

        result = PhotoValidationAnalyticsService.get_validation_by_event_type()
        
        registration_stats = [r for r in result if r['event_type'] == 'REGISTRATION'][0]
        login_stats = [r for r in result if r['event_type'] == 'LOGIN'][0]

        self.assertEqual(registration_stats['validated'], 1)
        self.assertEqual(login_stats['rejected'], 1)

    def test_get_daily_validation_metrics(self):
        """Test daily validation metrics."""
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='daily-1',
            nonce='nonce-daily-1',
            captured_at=timezone.now(),
            verification_status='VALIDATED',
        )

        result = PhotoValidationAnalyticsService.get_daily_validation_metrics()
        
        self.assertGreater(len(result), 0)
        today_data = [d for d in result if d['date'] == timezone.now().date().isoformat()]
        self.assertEqual(len(today_data), 1)
        self.assertEqual(today_data[0]['VALIDATED'], 1)


class BiometricAnalyticsServiceTests(TestCase):
    """Tests for biometric analytics service."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='bio-user',
            email='bio@example.com',
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

    def test_get_face_recognition_status(self):
        """Test face recognition status."""
        status = BiometricSubsystemAnalyticsService.get_face_recognition_status()
        
        self.assertIn('face_recognition_enabled', status)
        self.assertIn('liveness_enabled', status)
        self.assertIn('status', status)
        self.assertIn(status['status'], ['ENABLED', 'DISABLED'])

    def test_get_face_recognition_performance(self):
        """Test face recognition performance metrics."""
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='bio-1',
            nonce='nonce-bio-1',
            captured_at=timezone.now(),
            verification_status='VALIDATED',
            face_recognition_status='SUCCESS',
            face_confidence=0.95,
        )
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='bio-2',
            nonce='nonce-bio-2',
            captured_at=timezone.now(),
            verification_status='REJECTED',
            face_recognition_status='FAILED',
        )

        result = BiometricSubsystemAnalyticsService.get_face_recognition_performance()
        
        self.assertEqual(result['success'], 1)
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['total'], 2)
        self.assertGreater(result['success_rate'], 0)

    def test_get_average_confidence_score(self):
        """Test average confidence score calculation."""
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='conf-1',
            nonce='nonce-conf-1',
            captured_at=timezone.now(),
            verification_status='VALIDATED',
            face_recognition_status='SUCCESS',
            face_confidence=0.95,
        )
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='LOGIN',
            image=self._create_test_image(),
            request_id='conf-2',
            nonce='nonce-conf-2',
            captured_at=timezone.now(),
            verification_status='VALIDATED',
            face_recognition_status='SUCCESS',
            face_confidence=0.85,
        )

        result = BiometricSubsystemAnalyticsService.get_average_confidence_score()
        
        self.assertEqual(result['sample_size'], 2)
        self.assertAlmostEqual(result['average_confidence'], 0.9, places=1)
        self.assertEqual(result['min_confidence'], 0.85)
        self.assertEqual(result['max_confidence'], 0.95)


class SystemHealthAnalyticsServiceTests(TestCase):
    """Tests for system health analytics service."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='health-user',
            email='health@example.com',
            password='S3cur3Password!',
        )

    def test_get_system_health_summary(self):
        """Test system health summary contains all metrics."""
        summary = SystemHealthAnalyticsService.get_system_health_summary()
        
        self.assertIn('generated_at', summary)
        self.assertIn('tokens', summary)
        self.assertIn('validation', summary)
        self.assertIn('biometric', summary)
        self.assertIn('biometric_status', summary)


class ExcelReportGeneratorTests(TestCase):
    """Tests for Excel report generation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='excel-user',
            email='excel@example.com',
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

    def test_generate_full_report(self):
        """Test Excel report generation."""
        # Create some test data
        CampusToken.objects.create(
            user=self.user,
            token='excel-token',
            expires_at=timezone.now() + timedelta(hours=1),
            status='ACTIVE',
        )
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='TOKEN_GENERATION',
            image=self._create_test_image(),
            request_id='excel-photo',
            nonce='nonce-excel',
            captured_at=timezone.now(),
            verification_status='VALIDATED',
            face_recognition_status='SUCCESS',
        )

        generator = ExcelReportGenerator()
        excel_file = generator.generate_full_report()
        
        # Verify it's a valid BytesIO object
        self.assertIsInstance(excel_file, BytesIO)
        self.assertGreater(excel_file.getbuffer().nbytes, 0)


class PDFReportGeneratorTests(TestCase):
    """Tests for PDF report generation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='pdf-user',
            email='pdf@example.com',
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

    def test_generate_full_report(self):
        """Test PDF report generation."""
        # Create some test data
        CampusToken.objects.create(
            user=self.user,
            token='pdf-token',
            expires_at=timezone.now() + timedelta(hours=1),
            status='ACTIVE',
        )
        SecurityPhoto.objects.create(
            user=self.user,
            event_type='TOKEN_GENERATION',
            image=self._create_test_image(),
            request_id='pdf-photo',
            nonce='nonce-pdf',
            captured_at=timezone.now(),
            verification_status='VALIDATED',
            face_recognition_status='SUCCESS',
        )

        generator = PDFReportGenerator()
        pdf_file = generator.generate_full_report()
        
        # Verify it's a valid BytesIO object
        self.assertIsInstance(pdf_file, BytesIO)
        self.assertGreater(pdf_file.getbuffer().nbytes, 0)
        
        # Verify it starts with PDF magic bytes
        pdf_file.seek(0)
        self.assertEqual(pdf_file.read(4), b'%PDF')


class AnalyticsAPIViewTests(APITestCase):
    """Tests for analytics API views."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='api-user',
            email='api@example.com',
            password='S3cur3Password!',
        )
        self.client.force_authenticate(user=self.user)

    def test_token_analytics_endpoint(self):
        """Test token analytics API endpoint."""
        response = self.client.get('/api/v1/tokens/analytics/tokens/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('daily_volume', response.data)
        self.assertIn('weekly_volume', response.data)
        self.assertIn('status_summary', response.data)

    def test_photo_validation_endpoint(self):
        """Test photo validation analytics endpoint."""
        response = self.client.get('/api/v1/tokens/analytics/photos/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('overall', response.data)
        self.assertIn('by_event_type', response.data)
        self.assertIn('daily_metrics', response.data)

    def test_biometric_analytics_endpoint(self):
        """Test biometric analytics endpoint."""
        response = self.client.get('/api/v1/tokens/analytics/biometric/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)
        self.assertIn('performance', response.data)
        self.assertIn('confidence_scores', response.data)

    def test_system_health_endpoint(self):
        """Test system health analytics endpoint."""
        response = self.client.get('/api/v1/tokens/analytics/health/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('generated_at', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('validation', response.data)

    def test_excel_report_endpoint(self):
        """Test Excel report export endpoint."""
        response = self.client.get('/api/v1/tokens/reports/excel/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_pdf_report_endpoint(self):
        """Test PDF report export endpoint."""
        response = self.client.get('/api/v1/tokens/reports/pdf/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/pdf')

    def test_invalid_date_range(self):
        """Test handling of invalid date ranges."""
        response = self.client.get('/api/v1/tokens/analytics/tokens/?start_date=invalid&end_date=2026-08-15')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
