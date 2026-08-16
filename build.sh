#!/bin/bash
set -e

# Install dependencies
pip install -r requirements-prod.txt

# Collect static files
python manage.py collectstatic --noinput --clear

# Run migrations (optional - comment out if using Neon dashboard)
# python manage.py migrate --noinput

echo "✅ Vercel build completed successfully!"
