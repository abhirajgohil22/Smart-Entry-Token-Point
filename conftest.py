"""
Pytest configuration and fixtures

This module provides common fixtures and configuration for all tests.
"""

import os

import django
import pytest
from django.conf import settings

# Configure Django settings before running tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()


@pytest.fixture(scope='session')
def django_db_setup():
    """Configure the in-memory test database for Django's normal migration flow."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ATOMIC_REQUESTS': False,
        'OPTIONS': {},
        'TEST': {'NAME': ':memory:'},
    }


@pytest.fixture
def client():
    """Provide Django test client"""
    from django.test import Client
    return Client()


@pytest.fixture
def api_client():
    """Provide DRF API test client"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_user(db):
    """Create an authenticated test user"""
    from django.contrib.auth.models import User
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123'
    )
    return user


@pytest.fixture
def authenticated_api_client(api_client, authenticated_user):
    """Provide authenticated API test client"""
    api_client.force_authenticate(user=authenticated_user)
    return api_client
