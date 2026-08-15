"""Models for the security photo capture workflow."""

import uuid

from django.conf import settings
from django.db import models


class SecurityPhoto(models.Model):
    """Mandatory photo capture event for authentication and token workflows."""

    EVENT_TYPE_CHOICES = [
        ('REGISTRATION', 'Registration'),
        ('LOGIN', 'Login'),
        ('TOKEN_GENERATION', 'Token Generation'),
        ('TOKEN_REGENERATION', 'Token Regeneration'),
    ]

    VERIFICATION_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('VALIDATED', 'Validated'),
        ('REJECTED', 'Rejected'),
        ('PROCESSING', 'Processing'),
    ]

    FACE_RECOGNITION_STATUS_CHOICES = [
        ('NOT_RUN', 'Not Run'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('UNAVAILABLE', 'Unavailable'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='security_photos',
    )
    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES)
    image = models.ImageField(upload_to='security_photos/%Y/%m/%d/')
    request_id = models.CharField(max_length=128, unique=True, db_index=True, blank=True, null=True)
    nonce = models.CharField(max_length=128, unique=True, blank=True, null=True)
    captured_at = models.DateTimeField()
    verification_status = models.CharField(
        max_length=32,
        choices=VERIFICATION_STATUS_CHOICES,
        default='PENDING',
    )
    face_recognition_status = models.CharField(
        max_length=32,
        choices=FACE_RECOGNITION_STATUS_CHOICES,
        default='NOT_RUN',
    )
    face_confidence = models.FloatField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    retention_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'security_photo'
        indexes = [
            models.Index(fields=['user'], name='idx_security_photo_user'),
            models.Index(fields=['event_type'], name='idx_security_photo_event'),
            models.Index(fields=['captured_at'], name='idx_security_photo_captured'),
            models.Index(fields=['verification_status'], name='idx_photo_verif_status'),
        ]
        ordering = ['-captured_at']

    def __str__(self):
        return f'{self.user} / {self.event_type} / {self.captured_at}'


class ProfilePhoto(models.Model):
    """User profile picture stored separately from security event capture records."""

    class Meta:
        db_table = 'profile_photo'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile_photo',
    )
    image = models.ImageField(upload_to='profile_photos/%Y/%m/%d/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} profile photo'
