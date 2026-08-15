"""Security Photos app URL configuration."""

from django.urls import path

from apps.security_photos.views import AdminAuditTrailView, PhotoChallengeAPIView

app_name = 'security_photos'

urlpatterns = [
    path('challenge/', PhotoChallengeAPIView.as_view(), name='challenge'),
    path('admin/audit-trail/', AdminAuditTrailView.as_view(), name='admin_audit_trail'),
]
