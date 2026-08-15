"""
Health check views for monitoring system status
"""

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db import connections
from django.db.utils import OperationalError
import logging

logger = logging.getLogger(__name__)


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
