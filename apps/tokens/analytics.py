"""Analytics and reporting services for token and security metrics."""

from datetime import datetime, timedelta
from collections import defaultdict

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone

from apps.tokens.models import CampusToken
from apps.security_photos.models import SecurityPhoto


class TokenAnalyticsService:
    """Generate analytics for campus token issuance and status."""

    @staticmethod
    def get_daily_token_volume(start_date=None, end_date=None):
        """
        Get daily token generation volume.
        
        Returns: list of dicts with date, count, and status breakdown
        """
        if end_date is None:
            end_date = timezone.now()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        tokens = CampusToken.objects.filter(
            created_at__date__gte=start_date.date(),
            created_at__date__lte=end_date.date(),
        ).values('created_at__date').annotate(total=Count('id'))

        status_breakdown = CampusToken.objects.filter(
            created_at__date__gte=start_date.date(),
            created_at__date__lte=end_date.date(),
        ).values('created_at__date', 'status').annotate(count=Count('id'))

        # Organize by date
        daily_data = {}
        for entry in tokens:
            date_key = entry['created_at__date'].isoformat()
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'date': date_key,
                    'total': entry['total'],
                    'ACTIVE': 0,
                    'REVOKED': 0,
                    'EXPIRED': 0,
                }

        for entry in status_breakdown:
            date_key = entry['created_at__date'].isoformat()
            status = entry['status']
            daily_data[date_key][status] = entry['count']

        return sorted(daily_data.values(), key=lambda x: x['date'])

    @staticmethod
    def get_weekly_token_volume(start_date=None, end_date=None):
        """
        Get weekly token generation volume (ISO weeks).
        
        Returns: list of dicts with week, count, and status breakdown
        """
        if end_date is None:
            end_date = timezone.now()
        if start_date is None:
            start_date = end_date - timedelta(days=90)

        tokens = CampusToken.objects.filter(
            created_at__date__gte=start_date.date(),
            created_at__date__lte=end_date.date(),
        )

        weekly_data = defaultdict(lambda: {'total': 0, 'ACTIVE': 0, 'REVOKED': 0, 'EXPIRED': 0})

        for token in tokens:
            week_key = token.created_at.isocalendar()
            iso_week = f"{week_key.year}-W{week_key.week:02d}"
            weekly_data[iso_week]['total'] += 1
            weekly_data[iso_week][token.status] += 1

        return [
            {'week': week, **data}
            for week, data in sorted(weekly_data.items())
        ]

    @staticmethod
    def get_token_status_summary():
        """Get summary of all tokens by status."""
        return list(
            CampusToken.objects.values('status').annotate(count=Count('id')).order_by('status')
        )


class PhotoValidationAnalyticsService:
    """Generate analytics for security photo validation metrics."""

    @staticmethod
    def get_validation_success_rate(event_type=None, start_date=None, end_date=None):
        """
        Get photo validation success vs. rejection counts.
        
        Returns: dict with validated, rejected, pending counts and success rate
        """
        if end_date is None:
            end_date = timezone.now()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        query = SecurityPhoto.objects.filter(
            captured_at__gte=start_date,
            captured_at__lte=end_date,
        )

        if event_type:
            query = query.filter(event_type=event_type)

        verified_count = query.filter(verification_status='VALIDATED').count()
        rejected_count = query.filter(verification_status='REJECTED').count()
        pending_count = query.filter(verification_status='PENDING').count()
        processing_count = query.filter(verification_status='PROCESSING').count()
        total = query.count()

        success_rate = (verified_count / total * 100) if total > 0 else 0

        return {
            'validated': verified_count,
            'rejected': rejected_count,
            'pending': pending_count,
            'processing': processing_count,
            'total': total,
            'success_rate': round(success_rate, 2),
        }

    @staticmethod
    def get_validation_by_event_type(start_date=None, end_date=None):
        """
        Get validation breakdown by event type.
        
        Returns: list of dicts with event_type and validation stats
        """
        if end_date is None:
            end_date = timezone.now()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        event_types = [choice[0] for choice in SecurityPhoto.EVENT_TYPE_CHOICES]
        results = []

        for event_type in event_types:
            stats = PhotoValidationAnalyticsService.get_validation_success_rate(
                event_type=event_type,
                start_date=start_date,
                end_date=end_date,
            )
            results.append({
                'event_type': event_type,
                **stats,
            })

        return results

    @staticmethod
    def get_daily_validation_metrics(start_date=None, end_date=None):
        """
        Get daily breakdown of validation metrics.
        
        Returns: list of dicts with daily counts by status
        """
        if end_date is None:
            end_date = timezone.now()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        photos = SecurityPhoto.objects.filter(
            captured_at__date__gte=start_date.date(),
            captured_at__date__lte=end_date.date(),
        ).values('captured_at__date', 'verification_status').annotate(count=Count('id'))

        daily_data = {}
        for entry in photos:
            date_key = entry['captured_at__date'].isoformat()
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'date': date_key,
                    'VALIDATED': 0,
                    'REJECTED': 0,
                    'PENDING': 0,
                    'PROCESSING': 0,
                }

            status = entry['verification_status']
            daily_data[date_key][status] = entry['count']

        return sorted(daily_data.values(), key=lambda x: x['date'])


class BiometricSubsystemAnalyticsService:
    """Generate analytics for biometric (face recognition) subsystem performance."""

    @staticmethod
    def get_face_recognition_status():
        """
        Get face recognition system status.
        
        Returns: dict with enabled status and performance metrics
        """
        enabled = getattr(settings, 'FACE_RECOGNITION_ENABLED', False)
        liveness_enabled = getattr(settings, 'LIVENESS_ENABLED', False)

        return {
            'face_recognition_enabled': enabled,
            'liveness_enabled': liveness_enabled,
            'status': 'ENABLED' if enabled else 'DISABLED',
        }

    @staticmethod
    def get_face_recognition_performance(start_date=None, end_date=None):
        """
        Get face recognition performance metrics (success vs. failure).
        
        Returns: dict with success, failed, unavailable counts and rates
        """
        if end_date is None:
            end_date = timezone.now()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        query = SecurityPhoto.objects.filter(
            captured_at__gte=start_date,
            captured_at__lte=end_date,
        )

        success_count = query.filter(face_recognition_status='SUCCESS').count()
        failed_count = query.filter(face_recognition_status='FAILED').count()
        unavailable_count = query.filter(face_recognition_status='UNAVAILABLE').count()
        not_run_count = query.filter(face_recognition_status='NOT_RUN').count()
        total = query.count()

        success_rate = (success_count / (success_count + failed_count) * 100) if (success_count + failed_count) > 0 else 0

        return {
            'success': success_count,
            'failed': failed_count,
            'unavailable': unavailable_count,
            'not_run': not_run_count,
            'total': total,
            'success_rate': round(success_rate, 2),
        }

    @staticmethod
    def get_average_confidence_score(start_date=None, end_date=None):
        """
        Get average face confidence score for successful recognitions.
        
        Returns: dict with average confidence and confidence distribution
        """
        if end_date is None:
            end_date = timezone.now()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        photos = SecurityPhoto.objects.filter(
            captured_at__gte=start_date,
            captured_at__lte=end_date,
            face_recognition_status='SUCCESS',
            face_confidence__isnull=False,
        ).values_list('face_confidence', flat=True)

        if not photos:
            return {
                'average_confidence': 0,
                'min_confidence': 0,
                'max_confidence': 0,
                'sample_size': 0,
            }

        confidences = list(photos)
        average = sum(confidences) / len(confidences)

        return {
            'average_confidence': round(average, 4),
            'min_confidence': min(confidences),
            'max_confidence': max(confidences),
            'sample_size': len(confidences),
        }


class SystemHealthAnalyticsService:
    """Generate analytics for overall system health."""

    @staticmethod
    def get_system_health_summary():
        """
        Get comprehensive system health metrics.
        
        Returns: dict with token, photo, and biometric metrics
        """
        return {
            'generated_at': timezone.now().isoformat(),
            'tokens': TokenAnalyticsService.get_token_status_summary(),
            'validation': PhotoValidationAnalyticsService.get_validation_success_rate(),
            'biometric': BiometricSubsystemAnalyticsService.get_face_recognition_performance(),
            'biometric_status': BiometricSubsystemAnalyticsService.get_face_recognition_status(),
        }
