#!/bin/bash

# Startup script for batch processing Celery worker
# This script starts a dedicated worker for processing focus tracking batch tasks

set -e

# Environment variables
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6380}
REDIS_DB=${REDIS_DB:-0}
WORKER_NAME=${WORKER_NAME:-batch_worker_$(hostname)}
WORKER_CONCURRENCY=${WORKER_CONCURRENCY:-1}
LOG_LEVEL=${LOG_LEVEL:-INFO}
LOG_FILE=${LOG_FILE:-~/gaze_tracker/logs/batch_worker.log}

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

echo "Starting batch processing Celery worker..."
echo "Redis: $REDIS_HOST:$REDIS_PORT/$REDIS_DB"
echo "Worker Name: $WORKER_NAME"
echo "Concurrency: $WORKER_CONCURRENCY"
echo "Log Level: $LOG_LEVEL"
echo "Log File: $LOG_FILE"

# Start the Celery worker
cd /home/lahirud/gaze_tracker

exec uv run celery -A src.services.batch_worker worker \
    --loglevel=$LOG_LEVEL \
    --queues=batch_processing \
    --concurrency=$WORKER_CONCURRENCY \
    --hostname=$WORKER_NAME \
    --logfile=$LOG_FILE \
    --pidfile=/var/run/gaze_tracker/batch_worker.pid \
    --without-gossip \
    --without-mingle \
    --without-heartbeat
