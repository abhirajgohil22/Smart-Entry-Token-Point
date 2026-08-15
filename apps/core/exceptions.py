"""
Exception handlers for the Smart Campus Token Management System
"""

import logging
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses
    and logs exceptions for monitoring.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Log the exception
    logger.exception(f"Exception in {context['view'].__class__.__name__}: {str(exc)}")

    # Add custom response data
    if response is None:
        # For unhandled exceptions, return a generic error response
        response = Response(
            {
                'error': 'An unexpected error occurred',
                'error_code': 'INTERNAL_SERVER_ERROR',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    else:
        # Ensure consistent error response format
        if isinstance(response.data, dict) and 'detail' in response.data:
            # Rest framework's default format
            detail = response.data['detail']
            response.data = {
                'error': str(detail),
                'error_code': get_error_code(exc),
            }

    return response


def get_error_code(exc):
    """
    Extract or generate error code from exception
    """
    if hasattr(exc, 'error_code'):
        return exc.error_code
    elif hasattr(exc, 'status_code'):
        return f'HTTP_{exc.status_code}'
    else:
        return 'UNKNOWN_ERROR'
