"""
Authentication app for Smart Campus Token Management System.

Handles user registration, login, password management, and JWT token generation.
"""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authentication'
    verbose_name = 'Authentication'
