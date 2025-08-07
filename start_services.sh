#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Colors for better log readability
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to cleanup background processes on script exit
cleanup() {
    echo -e "${RED}Cleaning up processes...${NC}"
    pkill -f "runserver"
    pkill -f "celery worker"
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Set up trap to catch script termination
trap cleanup SIGINT SIGTERM

# Check if Redis is running
echo -e "${BLUE}Checking Redis server...${NC}"
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Redis server is not running. Starting Redis..."
    redis-server &
    sleep 2
fi

# Kill any process that is using port 8000
echo "Checking for and stopping any process on port 8000..."
fuser -k 8000/tcp 2>/dev/null || true

# Start Django development server
echo -e "${BLUE}Starting Django development server...${NC}"
python manage.py runserver 0.0.0.0:8000 > logs/django.log 2>&1 &

# Start Celery worker with its own log file
echo -e "${BLUE}Starting Celery worker...${NC}"
celery -A whisk_project worker -l info -Q image_generation > logs/celery.log 2>&1 &

# Function to monitor logs
monitor_logs() {
    tail -f logs/django.log logs/celery.log &
    TAIL_PID=$!
    trap "kill $TAIL_PID" EXIT
}

# Start log monitoring
monitor_logs

# Keep script running and wait for Ctrl+C
echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${BLUE}Logs are being saved to:${NC}"
echo -e "  - Django logs: ${GREEN}logs/django.log${NC}"
echo -e "  - Celery logs: ${GREEN}logs/celery.log${NC}"
echo -e "${BLUE}Press Ctrl+C to stop all services.${NC}"
wait
