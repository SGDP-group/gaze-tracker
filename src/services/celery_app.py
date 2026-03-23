"""
Celery application configuration for asynchronous task processing.
"""

from celery import Celery
import os

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6380/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6380/0")

# Create Celery app
celery_app = Celery(
    "focus_tracker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["src.services.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Queue configuration for different worker types
    task_routes={
        'src.services.tasks.process_session_frames_async': {'queue': 'batch_processing'},
        'src.services.tasks.train_user_model_async': {'queue': 'ml_training'},
        'src.services.tasks.generate_recommendations_async': {'queue': 'ml_training'},
        'src.services.tasks.cleanup_old_tasks': {'queue': 'maintenance'},
    },
    task_default_queue='default',
    task_default_exchange='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',
    # Batch processing specific settings
    task_annotations={
        'src.services.tasks.process_session_frames_async': {
            'rate_limit': '10/m',  # Limit batch processing tasks
            'time_limit': 60 * 60,  # 1 hour for batch processing
            'soft_time_limit': 55 * 60,  # 55 minutes soft limit
        },
        'src.services.tasks.train_user_model_async': {
            'rate_limit': '5/m',  # Limit ML training tasks
            'time_limit': 45 * 60,  # 45 minutes for training
            'soft_time_limit': 40 * 60,  # 40 minutes soft limit
        }
    }
)
