"""Models for optional face-recognition data and enrollment."""

import uuid

from django.conf import settings
from django.db import models


class UserFaceEncoding(models.Model):
    """Enrollment encoding stored separately from security event records."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='face_encoding',
    )
    encoding = models.JSONField(default=list, help_text='Face embedding vector in model space.')
    model_name = models.CharField(max_length=128, default='facenet')
    confidence = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user'], name='idx_user_face_user'),
            models.Index(fields=['updated_at'], name='idx_user_face_updated'),
        ]

    def __str__(self):
        return f'{self.user} face encoding'
