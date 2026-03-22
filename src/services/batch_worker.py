"""
Worker configuration for batch processing tasks.
"""

import os
from celery import Celery

# Environment-specific configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6380")
REDIS_DB = os.getenv("REDIS_DB", "0")

# Celery configuration for batch processing workers
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Create Celery app for batch processing
celery_app = Celery(
    "batch_processor",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["src.services.tasks"]
)

# Batch processing worker specific configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    
    # Batch processing specific limits
    task_time_limit=60 * 60,  # 1 hour for batch processing
    task_soft_time_limit=55 * 60,  # 55 minutes soft limit
    
    # Worker configuration for batch processing
    worker_prefetch_multiplier=1,  # Process one task at a time for resource-intensive work
    worker_max_tasks_per_child=5,  # Restart worker after 5 tasks to free memory
    worker_disable_rate_limits=False,  # Allow rate limiting
    
    # Optimizations for batch processing
    task_acks_late=True,  # Acknowledge after task completion
    worker_reject_unknown_tasks=True,  # Reject unknown tasks
    worker_send_task_events=True,  # Send task events for monitoring
    
    # Queue configuration
    task_routes={
        'src.services.tasks.process_session_frames_async': {'queue': 'batch_processing'},
    },
    task_default_queue='batch_processing',
    task_default_exchange='batch_processing',
    task_default_exchange_type='direct',
    task_default_routing_key='batch_processing',
    
    # Concurrency settings
    worker_concurrency=1,  # Single thread per worker for batch processing
    worker_pool='solo',  # Use solo pool for batch processing
    
    # Resource management
    task_annotations={
        'src.services.tasks.process_session_frames_async': {
            'rate_limit': '10/m',  # Max 10 batch processing tasks per minute
        }
    }
)

if __name__ == '__main__':
    celery_app.start()
