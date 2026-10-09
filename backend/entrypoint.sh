#!/bin/sh

echo "Waiting for database to be ready..."

echo "Applying database migrations..."
python3 backend/manage.py migrate

echo "Purging accounts left unconfirmed for over seven days..."
python3 backend/manage.py purge_unconfirmed_users

echo "Populating initial preferences data if needed..."
python3 backend/manage.py populate_preferences

echo "Populating fake hairdressers if needed..."
python3 backend/manage.py populate_hairdressers

echo "Starting Django server..."
exec python3 backend/manage.py runserver 0.0.0.0:8000 