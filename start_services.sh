#!/bin/bash

# Kill any process that is using port 8000
echo "Checking for and stopping any process on port 8000..."
fuser -k 8000/tcp

# Start Django development server
echo "Starting Django development server..."
python manage.py runserver 0.0.0.0:8000 &

# Start Celery worker
echo "Starting Celery worker..."
celery -A whisk_project worker -l info -Q image_generation
