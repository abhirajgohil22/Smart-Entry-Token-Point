"""
Health check views for monitoring system status
"""

import logging

from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpResponse, JsonResponse
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class LandingPageView(TemplateView):
    """Public landing page for the Smart Entry Token Point platform."""

    template_name = 'landing.html'


def api_home(request):
    """Simple API landing page that points clients to the supported endpoints."""
    accept_header = request.headers.get('Accept', '')
    wants_html = 'text/html' in accept_header.lower() or request.GET.get('format') == 'html'

    if wants_html:
        html = """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <title>Smart Campus Token Management System</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                a { color: #0b57d0; }
                .card { max-width: 720px; padding: 24px; border: 1px solid #ddd; border-radius: 12px; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Smart Campus Token Management System</h1>
                <p>The API is running and ready to accept authenticated requests.</p>
                <ul>
                    <li><a href="/health/check/">Health Check</a></li>
                    <li><a href="/api/v1/auth/register/">Register</a></li>
                    <li><a href="/api/auth/login/">Login</a></li>
                    <li><a href="/api/v1/tokens/generate/">Generate Token</a></li>
                    <li><a href="/api/docs/">API Documentation</a></li>
                </ul>
                <p>Use the API endpoints above or access the JSON contract via the REST API routes.</p>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html, content_type='text/html')

    return JsonResponse(
        {
            'name': 'Smart Campus Token Management System',
            'status': 'online',
            'message': 'API is running. Use the auth, token, and health endpoints documented below.',
            'endpoints': {
                'health_check': '/health/check/',
                'register': '/api/v1/auth/register/',
                'login': '/api/auth/login/',
                'token_generation': '/api/v1/tokens/generate/',
                'api_docs': '/api/docs/',
            },
        },
        status=200,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint that verifies the system is operational.
    Checks database connectivity and returns status information.
    """
    try:
        # Test database connection
        db_connection = connections['default']
        db_connection.ensure_connection()

        return Response(
            {
                'status': 'healthy',
                'database': 'connected',
                'message': 'Smart Campus Token Management System is operational',
            },
            status=status.HTTP_200_OK
        )
    except OperationalError as e:
        logger.error(f"Health check failed - database unavailable: {str(e)}")
        return Response(
            {
                'status': 'unhealthy',
                'database': 'disconnected',
                'message': 'Database connection failed',
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return Response(
            {
                'status': 'error',
                'message': str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
