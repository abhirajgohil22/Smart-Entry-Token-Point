"""Token models for transient campus-entry approval."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class CampusToken(models.Model):
    """Short-lived student access token for campus entry."""

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('REVOKED', 'Revoked'),
        ('EXPIRED', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campus_tokens')
    token = models.CharField(max_length=255, unique=True)
    payload = models.JSONField(default=dict)
    issued_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issued_at']

    def is_valid(self):
        return self.status == 'ACTIVE' and timezone.now() < self.expires_at

    def __str__(self):
        return f'{self.user} - {self.token}'
