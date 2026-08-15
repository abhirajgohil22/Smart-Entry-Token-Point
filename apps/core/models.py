"""
Models for Core app
"""

from django.db import models
from django.contrib.auth.models import User


class BaseModel(models.Model):
    """
    Abstract base model for all models in the system.
    Provides common timestamp fields for audit tracking.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
