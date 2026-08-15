"""API views for analytics and report generation."""

from datetime import timedelta

from django.http import FileResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tokens.analytics import (
    TokenAnalyticsService,
    PhotoValidationAnalyticsService,
    BiometricSubsystemAnalyticsService,
    SystemHealthAnalyticsService,
)
from apps.tokens.exports import ExcelReportGenerator, PDFReportGenerator


class AnalyticsBaseView(APIView):
    """Base view for analytics endpoints with date range handling."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_date_range(self):
        """Extract and validate date range from query parameters."""
        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')
        days_str = self.request.query_params.get('days')
        days = None
        
        if days_str:
            try:
                days = int(days_str)
            except (ValueError, TypeError):
                return None, None, {'error': 'days parameter must be an integer'}

        end_date = timezone.now()
        
        if start_date_str and end_date_str:
            try:
                from datetime import datetime
                end_date = datetime.fromisoformat(end_date_str)
                start_date = datetime.fromisoformat(start_date_str)
            except ValueError:
                return None, None, {'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'}
        elif days:
            start_date = end_date - timedelta(days=days)
        else:
            start_date = end_date - timedelta(days=30)

        return start_date, end_date, None


class TokenAnalyticsAPIView(AnalyticsBaseView):
    """Token generation and status analytics."""

    def get(self, request):
        start_date, end_date, error = self._get_date_range()
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        daily_volume = TokenAnalyticsService.get_daily_token_volume(start_date, end_date)
        weekly_volume = TokenAnalyticsService.get_weekly_token_volume(start_date, end_date)
        status_summary = TokenAnalyticsService.get_token_status_summary()

        return Response({
            'daily_volume': daily_volume,
            'weekly_volume': weekly_volume,
            'status_summary': status_summary,
        })


class PhotoValidationAnalyticsAPIView(AnalyticsBaseView):
    """Security photo validation analytics."""

    def get(self, request):
        start_date, end_date, error = self._get_date_range()
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        overall = PhotoValidationAnalyticsService.get_validation_success_rate(start_date, end_date)
        by_event_type = PhotoValidationAnalyticsService.get_validation_by_event_type(start_date, end_date)
        daily_metrics = PhotoValidationAnalyticsService.get_daily_validation_metrics(start_date, end_date)

        return Response({
            'overall': overall,
            'by_event_type': by_event_type,
            'daily_metrics': daily_metrics,
        })


class BiometricAnalyticsAPIView(AnalyticsBaseView):
    """Biometric subsystem performance analytics."""

    def get(self, request):
        start_date, end_date, error = self._get_date_range()
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        status_info = BiometricSubsystemAnalyticsService.get_face_recognition_status()
        performance = BiometricSubsystemAnalyticsService.get_face_recognition_performance(start_date, end_date)
        confidence = BiometricSubsystemAnalyticsService.get_average_confidence_score(start_date, end_date)

        return Response({
            'status': status_info,
            'performance': performance,
            'confidence_scores': confidence,
        })


class SystemHealthAnalyticsAPIView(AnalyticsBaseView):
    """Overall system health and metrics."""

    def get(self, request):
        health = SystemHealthAnalyticsService.get_system_health_summary()
        return Response(health)


class ExcelReportAPIView(AnalyticsBaseView):
    """Generate and download Excel report."""

    def get(self, request):
        start_date, end_date, error = self._get_date_range()
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        try:
            generator = ExcelReportGenerator()
            excel_file = generator.generate_full_report(start_date, end_date)

            filename = f"campus_token_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            return FileResponse(
                excel_file,
                as_attachment=True,
                filename=filename,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate Excel report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PDFReportAPIView(AnalyticsBaseView):
    """Generate and download PDF report."""

    def get(self, request):
        start_date, end_date, error = self._get_date_range()
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        try:
            generator = PDFReportGenerator()
            pdf_file = generator.generate_full_report(start_date, end_date)

            filename = f"campus_token_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return FileResponse(
                pdf_file,
                as_attachment=True,
                filename=filename,
                content_type='application/pdf',
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate PDF report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
