#!/bin/bash
set -e

# Install dependencies
pip install -r requirements-prod.txt

# Collect static files - use SQLite as fallback to avoid database connection
# This allows the build to succeed even if DATABASE_URL isn't accessible
export DATABASE_URL="sqlite:///db.sqlite3"
python manage.py collectstatic --noinput --clear

echo "✅ Vercel build completed successfully!"
