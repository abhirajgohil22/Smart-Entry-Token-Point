"""Views for live-photo challenge generation, validation, and admin audit trails."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.security_photos.models import SecurityPhoto
from apps.security_photos.services import PhotoChallengeService
from apps.tokens.models import CampusToken
from apps.notifications.models import NotificationLog


class PhotoChallengeAPIView(APIView):
    """Issue a short-lived one-time nonce and signed photo token."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id') or request.query_params.get('user_id')
        event_type = request.data.get('event_type') or request.query_params.get('event_type')

        if not user_id or not event_type:
            return Response(
                {'error': 'Both user_id and event_type are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            challenge = PhotoChallengeService.generate_challenge(user_id, event_type)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(challenge, status=status.HTTP_200_OK)


class AdminAuditTrailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Admin dashboard for monitoring security events and campus gate activity."""

    template_name = 'admin/audit_trail.html'
    login_url = '/admin/login/'

    def test_func(self):
        """Restrict to staff/superuser only."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Recent security events (last 30 days)
        recent_events = SecurityPhoto.objects.select_related('user').order_by('-captured_at')[:100]

        # Token activity
        active_tokens = CampusToken.objects.filter(status='ACTIVE').count()
        revoked_tokens = CampusToken.objects.filter(status='REVOKED').count()
        expired_tokens = CampusToken.objects.filter(status='EXPIRED').count()

        # Recent notifications
        recent_notifications = NotificationLog.objects.select_related('user').order_by('-created_at')[:50]

        # Event type summary
        event_summary = {}
        for event_type, label in SecurityPhoto.EVENT_TYPE_CHOICES:
            count = SecurityPhoto.objects.filter(event_type=event_type).count()
            event_summary[label] = count

        # Verification status summary
        verification_summary = {}
        for status_type, label in SecurityPhoto.VERIFICATION_STATUS_CHOICES:
            count = SecurityPhoto.objects.filter(verification_status=status_type).count()
            verification_summary[label] = count

        context.update({
            'recent_events': recent_events,
            'active_tokens': active_tokens,
            'revoked_tokens': revoked_tokens,
            'expired_tokens': expired_tokens,
            'recent_notifications': recent_notifications,
            'event_summary': event_summary,
            'verification_summary': verification_summary,
        })

        return context

