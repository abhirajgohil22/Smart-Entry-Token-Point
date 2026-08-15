"""Notification logs for security and token lifecycle alerts."""

from django.conf import settings
from django.db import models


class NotificationLog(models.Model):
    """Database record for email and system notices."""

    EVENT_TYPE_CHOICES = [
        ('EMAIL_VERIFICATION', 'Email Verification'),
        ('LOGIN_NEW_IP', 'Login from New IP'),
        ('TOKEN_GENERATED', 'Token Generated'),
        ('TOKEN_REGENERATED', 'Token Regenerated'),
        ('TOKEN_EXPIRING', 'Token Expiring'),
        ('SECURITY_PHOTO_REJECTION', 'Security Photo Rejection'),
    ]

    CHANNEL_CHOICES = [
        ('EMAIL', 'Email'),
        ('SYSTEM', 'System'),
        ('BOTH', 'Email + System'),
    ]

    STATUS_CHOICES = [
        ('QUEUED', 'Queued'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_logs')
    event_type = models.CharField(max_length=40, choices=EVENT_TYPE_CHOICES)
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default='BOTH')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='QUEUED')
    subject = models.CharField(max_length=255)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} / {self.event_type} / {self.status}'
