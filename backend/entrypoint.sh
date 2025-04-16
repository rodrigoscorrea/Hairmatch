#!/bin/sh

echo "Waiting for database to be ready..."

echo "Applying database migrations..."
python3 backend/manage.py migrate


echo "Starting Django server..."
exec python3 backend/manage.py runserver 0.0.0.0:8000 