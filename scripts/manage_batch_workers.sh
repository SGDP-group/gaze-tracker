#!/bin/bash

# Management script for batch processing workers
# Usage: ./manage_batch_workers.sh [start|stop|restart|status|scale]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WORKER_NAME_PREFIX="batch_worker"
PID_DIR="$PROJECT_DIR/.celery_pids"
LOG_DIR="$PROJECT_DIR/logs"

# Default number of workers
DEFAULT_WORKERS=2
WORKERS=${WORKERS:-$DEFAULT_WORKERS}

# Create necessary directories
mkdir -p "$PID_DIR"
mkdir -p "$LOG_DIR"

# Function to get worker PID file path
get_pid_file() {
    echo "$PID_DIR/${WORKER_NAME_PREFIX}_$1.pid"
}

# Function to get worker log file path
get_log_file() {
    echo "$LOG_DIR/${WORKER_NAME_PREFIX}_$1.log"
}

# Function to check if worker is running
is_worker_running() {
    local worker_id=$1
    local pid_file=$(get_pid_file $worker_id)
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Function to start a single worker
start_worker() {
    local worker_id=$1
    local pid_file=$(get_pid_file $worker_id)
    local log_file=$(get_log_file $worker_id)
    
    if is_worker_running $worker_id; then
        echo "Worker $worker_id is already running"
        return 0
    fi
    
    echo "Starting worker instance $worker_id..."
    cd "$PROJECT_DIR"
    
    # Clear any old log file for this worker
    > "$log_file"
    
    # Start worker in background with PID tracking
    nohup uv run celery -A src.services.batch_worker worker \
        --loglevel=INFO \
        --queues=batch_processing \
        --concurrency=1 \
        --hostname="${WORKER_NAME_PREFIX}_${worker_id}" \
        --logfile="$log_file" \
        --pidfile="$pid_file" \
        --detach > "$log_file.startup" 2>&1
    
    # Wait a moment and check if worker started
    sleep 3
    
    # Check startup log for errors
    if [ -f "$log_file.startup" ]; then
        echo "Startup output for worker $worker_id:"
        cat "$log_file.startup"
        rm -f "$log_file.startup"
    fi
    
    if is_worker_running $worker_id; then
        echo "Worker $worker_id started successfully"
        return 0
    else
        echo "Failed to start worker $worker_id"
        if [ -f "$log_file" ]; then
            echo "Error log for worker $worker_id:"
            tail -20 "$log_file"
        fi
        return 1
    fi
}

# Function to stop a single worker
stop_worker() {
    local worker_id=$1
    local pid_file=$(get_pid_file $worker_id)
    
    if ! is_worker_running $worker_id; then
        echo "Worker $worker_id is not running"
        return 0
    fi
    
    local pid=$(cat "$pid_file")
    echo "Stopping worker instance $worker_id (PID: $pid)..."
    
    # Send SIGTERM
    kill -TERM $pid 2>/dev/null || true
    
    # Wait for graceful shutdown
    local count=0
    while [ $count -lt 10 ] && is_worker_running $worker_id; do
        sleep 1
        count=$((count + 1))
    done
    
    # Force kill if still running
    if is_worker_running $worker_id; then
        echo "Force killing worker $worker_id..."
        kill -KILL $pid 2>/dev/null || true
        sleep 1
    fi
    
    # Clean up PID file
    rm -f "$pid_file"
    echo "Worker $worker_id stopped"
}

# Check Redis connection
check_redis() {
    if redis-cli -p 6380 ping > /dev/null 2>&1; then
        echo "✓ Redis server is running on port 6380"
        return 0
    else
        echo "✗ Redis server is not running on port 6380"
        echo "  Please start Redis with: redis-server --port 6380 --daemonize yes"
        return 1
    fi
}

case "$1" in
    start)
        echo "Starting $WORKERS batch processing workers..."
        
        # Check Redis connection
        if ! check_redis; then
            echo "Cannot start workers without Redis. Please start Redis first."
            exit 1
        fi
        
        started_workers=0
        for i in $(seq 1 $WORKERS); do
            if start_worker $i; then
                ((started_workers++))
            fi
        done
        
        echo "Started $started_workers/$WORKERS workers"
        if [ $started_workers -gt 0 ]; then
            echo "Worker status:"
            $0 status
        fi
        ;;
    
    stop)
        echo "Stopping all batch processing workers..."
        stopped_workers=0
        for i in $(seq 1 $WORKERS); do
            if is_worker_running $i; then
                stop_worker $i
                ((stopped_workers++))
            fi
        done
        
        echo "Stopped $stopped_workers workers"
        ;;
    
    restart)
        echo "Restarting batch processing workers..."
        $0 stop
        sleep 2
        $0 start
        ;;
    
    status)
        echo "Batch processing worker status:"
        echo "================================"
        
        active_workers=0
        for i in $(seq 1 $WORKERS); do
            if is_worker_running $i; then
                pid=$(cat $(get_pid_file $i))
                echo "Worker $i: ✓ Active (PID: $pid)"
                ((active_workers++))
            else
                echo "Worker $i: ✗ Inactive"
            fi
        done
        
        echo ""
        echo "Active workers: $active_workers/$WORKERS"
        
        # Check Celery stats if workers are active
        if [ $active_workers -gt 0 ]; then
            echo ""
            echo "Celery queue status:"
            cd "$PROJECT_DIR"
            python3 -c "
from src.services.celery_app import celery_app
import json

try:
    inspect = celery_app.control.inspect()
    stats = inspect.stats()
    if stats:
        for worker, worker_stats in stats.items():
            if 'batch_worker' in str(worker):
                pool_info = worker_stats.get('pool', {})
                concurrency = pool_info.get('max-concurrency', 'unknown')
                processes = pool_info.get('processes', [])
                print(f'{worker}: {concurrency} processes, {len(processes)} active')
    else:
        print('No active workers found')
except Exception as e:
    print(f'Error getting stats: {e}')
" 2>/dev/null || echo "Could not fetch Celery stats"
        fi
        ;;
    
    scale)
        if [ -z "$2" ]; then
            echo "Usage: $0 scale <number_of_workers>"
            exit 1
        fi
        
        NEW_WORKERS=$2
        echo "Scaling workers from $WORKERS to $NEW_WORKERS..."
        
        # Stop current workers
        $0 stop
        
        # Update worker count
        WORKERS=$NEW_WORKERS
        export WORKERS
        
        # Start new workers
        $0 start
        ;;
    
    logs)
        if [ -n "$2" ] && [ "$2" -eq "$2" ] 2>/dev/null; then
            # Show specific worker log
            log_file=$(get_log_file $2)
            if [ -f "$log_file" ]; then
                echo "Showing logs for worker $2 (Ctrl+C to exit):"
                tail -f "$log_file"
            else
                echo "Log file for worker $2 not found"
            fi
        else
            # Show all worker logs
            echo "Showing all batch worker logs (Ctrl+C to exit):"
            tail -f "$LOG_DIR"/*.log 2>/dev/null || echo "No log files found"
        fi
        ;;
    
    clean)
        echo "Cleaning up stale PID files and old logs..."
        # Clean up stale PID files
        for pid_file in "$PID_DIR"/*.pid; do
            if [ -f "$pid_file" ]; then
                pid=$(cat "$pid_file")
                if ! ps -p $pid > /dev/null 2>&1; then
                    echo "Removing stale PID file: $(basename "$pid_file")"
                    rm -f "$pid_file"
                fi
            fi
        done
        
        # Clean up old log files (keep last 5)
        find "$LOG_DIR" -name "*.log" -type f | sort -r | tail -n +6 | xargs rm -f 2>/dev/null || true
        echo "Cleanup completed"
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|status|scale <n>|logs [worker_id]|clean}"
        echo ""
        echo "Commands:"
        echo "  start           - Start batch processing workers"
        echo "  stop            - Stop all batch processing workers"
        echo "  restart         - Restart all batch processing workers"
        echo "  status          - Show worker status"
        echo "  scale <n>       - Scale to n workers"
        echo "  logs [n]        - Show logs (all workers or specific worker n)"
        echo "  clean           - Clean up stale PID files and old logs"
        echo ""
        echo "Environment variables:"
        echo "  WORKERS         - Number of workers to start (default: $DEFAULT_WORKERS)"
        echo "  REDIS_HOST      - Redis host (default: localhost)"
        echo "  REDIS_PORT      - Redis port (default: 6380)"
        echo "  REDIS_DB        - Redis database (default: 0)"
        exit 1
        ;;
esac
