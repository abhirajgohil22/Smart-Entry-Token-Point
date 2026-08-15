"""
Security Photos app for Smart Campus Token Management System.

Handles live photo capture, storage, and management.
"""

from django.apps import AppConfig


class SecurityPhotosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.security_photos'
    verbose_name = 'Security Photos'
