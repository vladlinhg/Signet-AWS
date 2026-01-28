#!/bin/sh

# Check if we should run migrations
# In a real CI/CD pipeline you might want to control this, but for this setup it ensures parity.
echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Auto-importing initial users..."
python manage.py import_erp_data --users-only

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Exec the container's main process (what's set as CMD in the Dockerfile)
exec "$@"
# tail -f /dev/null
