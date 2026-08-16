"""
WSGI config for Smart Campus Token Management System.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import sqlite3

from django.conf import settings
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')


def should_initialize_sqlite_db(db_path: str | None = None) -> bool:
    """Return True when a SQLite runtime database exists but has no Django tables."""
    if not db_path or db_path == ':memory:':
        return False

    if not os.path.exists(db_path):
        return True

    try:
        conn = sqlite3.connect(db_path)
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='auth_user'"
        ).fetchone()
        conn.close()
        return result is None
    except Exception:
        return True


def is_serverless_runtime() -> bool:
    """Return True when the app is running in a constrained serverless runtime."""
    return bool(
        os.environ.get('VERCEL')
        or os.environ.get('VERCEL_ENV')
        or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
    )


def initialize_sqlite_runtime() -> None:
    """Ensure a serverless SQLite database has the Django schema before requests arrive."""
    if not is_serverless_runtime():
        return

    db_config = getattr(settings, 'DATABASES', {}).get('default', {})
    if db_config.get('ENGINE') != 'django.db.backends.sqlite3':
        return

    db_path = db_config.get('NAME')
    if not should_initialize_sqlite_db(db_path):
        return

    call_command('migrate', interactive=False, run_syncdb=True, verbosity=0)


application = get_wsgi_application()
if is_serverless_runtime():
    initialize_sqlite_runtime()

# Vercel's Python serverless runtime looks for a callable named `app`.
# Keep both names available to support Django's standard WSGI interface
# and the serverless deployment contract.
app = application
