"""Tokens app URL configuration."""

from django.urls import path

from apps.tokens.views import GenerateTokenAPIView, RegenerateTokenAPIView
from apps.tokens.views_analytics import (
    TokenAnalyticsAPIView,
    PhotoValidationAnalyticsAPIView,
    BiometricAnalyticsAPIView,
    SystemHealthAnalyticsAPIView,
    ExcelReportAPIView,
    PDFReportAPIView,
)

app_name = 'tokens'

urlpatterns = [
    # Token operations
    path('generate/', GenerateTokenAPIView.as_view(), name='generate-token'),
    path('regenerate/', RegenerateTokenAPIView.as_view(), name='regenerate-token'),
    
    # Analytics endpoints
    path('analytics/tokens/', TokenAnalyticsAPIView.as_view(), name='analytics-tokens'),
    path('analytics/photos/', PhotoValidationAnalyticsAPIView.as_view(), name='analytics-photos'),
    path('analytics/biometric/', BiometricAnalyticsAPIView.as_view(), name='analytics-biometric'),
    path('analytics/health/', SystemHealthAnalyticsAPIView.as_view(), name='analytics-health'),
    
    # Report exports
    path('reports/excel/', ExcelReportAPIView.as_view(), name='report-excel'),
    path('reports/pdf/', PDFReportAPIView.as_view(), name='report-pdf'),
]
