"""
Celery tasks for asynchronous operations.

This module defines various Celery tasks for:
- ML model training and recommendations
- Batch processing of focus tracking sessions
- Data cleanup and maintenance operations
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from celery import Celery
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from src.database.database import SessionLocal
from src.database.models import UserSession, User
from src.services.ml_service import PersonalizedMLService
from src.services.batch_service import BatchFocusProcessor
from src.config import config
from src.services.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def train_user_model_async(self, user_id: str, force_retrain: bool = False) -> Dict[str, Any]:
    """
    Asynchronous task for training personalized user models.
    
    Args:
        user_id: User identifier
        force_retrain: Whether to force retraining even if model exists
    
    Returns:
        Training result with status and metrics
    """
    task_id = self.request.id
    
    # Update task status
    self.update_state(
        state='PROGRESS',
        meta={'status': 'Starting training...', 'progress': 0}
    )
    
    db = SessionLocal()
    ml_service = PersonalizedMLService()
    
    try:
        # Check if training is already in progress
        existing_task = db.query(TrainingTask).filter(
            TrainingTask.user_id == user_id,
            TrainingTask.status.in_(['PENDING', 'PROGRESS'])
        ).first()
        
        if existing_task and not force_retrain:
            return {
                'status': 'SKIPPED',
                'message': 'Training already in progress',
                'task_id': existing_task.task_id
            }
        
        # Create training task record
        training_task = TrainingTask(
            task_id=task_id,
            user_id=user_id,
            status='PROGRESS',
            started_at=datetime.utcnow()
        )
        db.add(training_task)
        db.commit()
        
        # Update progress - data preparation
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Preparing training data...', 'progress': 20}
        )
        
        # Check if we have enough data
        from src.database.models import UserSession, UserFeedback
        
        sessions_with_feedback = db.query(UserSession).join(UserFeedback).filter(
            UserSession.user_id == user_id,
            UserFeedback.productivity_rating.isnot(None)
        ).count()
        
        if sessions_with_feedback < 3:
            # Update task as completed with warning
            training_task.status = 'COMPLETED'
            training_task.completed_at = datetime.utcnow()
            training_task.result = json.dumps({
                'status': 'INSUFFICIENT_DATA',
                'message': f'Need at least 3 sessions with feedback, found {sessions_with_feedback}',
                'sessions_count': sessions_with_feedback
            })
            training_task.error_message = None
            db.commit()
            
            return {
                'status': 'INSUFFICIENT_DATA',
                'message': f'Need at least 3 sessions with feedback, found {sessions_with_feedback}',
                'sessions_count': sessions_with_feedback,
                'task_id': task_id
            }
        
        # Update progress - training model
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Training model...', 'progress': 50}
        )
        
        # Train the model
        training_result = ml_service.train_personalized_model(db, user_id, force_retrain)
        
        # Update progress - finalizing
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Finalizing model...', 'progress': 80}
        )
        
        # Update training task record
        training_task.status = 'COMPLETED'
        training_task.completed_at = datetime.utcnow()
        training_task.result = json.dumps(training_result)
        training_task.error_message = None
        db.commit()
        
        # Final progress update
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Training completed successfully',
                'progress': 100,
                'result': training_result
            }
        )
        
        return {
            'status': 'SUCCESS',
            'message': 'Model training completed successfully',
            'task_id': task_id,
            'result': training_result
        }
        
    except Exception as e:
        # Handle training errors
        error_message = str(e)
        
        # Update training task with error
        if 'training_task' in locals():
            training_task.status = 'FAILED'
            training_task.completed_at = datetime.utcnow()
            training_task.error_message = error_message
            db.commit()
        
        # Update Celery task state
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Training failed',
                'error': error_message,
                'progress': 0
            }
        )
        
        return {
            'status': 'FAILED',
            'message': 'Model training failed',
            'error': error_message,
            'task_id': task_id
        }
        
    finally:
        db.close()


@celery_app.task(bind=True)
def generate_recommendations_async(self, user_id: str) -> Dict[str, Any]:
    """
    Asynchronous task for generating personalized recommendations.
    
    Args:
        user_id: User identifier
    
    Returns:
        Recommendation generation result
    """
    task_id = self.request.id
    
    # Update task status
    self.update_state(
        state='PROGRESS',
        meta={'status': 'Analyzing session patterns...', 'progress': 25}
    )
    
    db = SessionLocal()
    ml_service = PersonalizedMLService()
    
    try:
        # Generate recommendations
        recommendations = ml_service.generate_focus_recommendations(db, user_id)
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Saving recommendations...', 'progress': 75}
        )
        
        # Update task status
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Recommendations generated successfully',
                'progress': 100,
                'recommendations_count': len(recommendations)
            }
        )
        
        return {
            'status': 'SUCCESS',
            'message': 'Recommendations generated successfully',
            'task_id': task_id,
            'recommendations_count': len(recommendations),
            'recommendations': recommendations
        }
        
    except Exception as e:
        error_message = str(e)
        
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Recommendation generation failed',
                'error': error_message,
                'progress': 0
            }
        )
        
        return {
            'status': 'FAILED',
            'message': 'Recommendation generation failed',
            'error': error_message,
            'task_id': task_id
        }
        
    finally:
        db.close()


@celery_app.task
def cleanup_old_tasks():
    """
    Periodic task to clean up old completed training tasks.
    """
    db = SessionLocal()
    
    try:
        # Delete tasks older than 7 days
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        deleted_count = db.query(TrainingTask).filter(
            TrainingTask.created_at < cutoff_date,
            TrainingTask.status.in_(['COMPLETED', 'FAILED'])
        ).delete()
        
        db.commit()
        
        return {
            'status': 'SUCCESS',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        return {
            'status': 'FAILED',
            'error': str(e)
        }
        
    finally:
        db.close()


@celery_app.task(bind=True, queue='batch_processing')
def process_session_frames_async(
    self, 
    user_id: str, 
    session_id: str,
    frames_directory: str,
    session_start: str,
    ground_frame_calibrated: bool = False,
    reference_angle: Optional[float] = None
) -> Dict[str, Any]:
    """
    Asynchronous task for batch processing all frames in a session directory.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        frames_directory: Directory path containing session frames
        session_start: Session start time (ISO string)
        ground_frame_calibrated: Whether ground frame was calibrated
        reference_angle: Reference angle from ground frame calibration
    
    Returns:
        Batch processing result with session analytics
    """
    task_id = self.request.id
    
    # Update task status
    self.update_state(
        state='PROGRESS',
        meta={'status': 'Starting batch processing...', 'progress': 0}
    )
    
    # Resource monitoring
    import psutil
    import threading
    
    def monitor_resources():
        """Monitor system resources during batch processing."""
        while True:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')
            
            resource_info = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_info.percent,
                'memory_available_gb': memory_info.available / (1024**3),
                'disk_free_gb': disk_info.free / (1024**3)
            }
            
            try:
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'status': 'Processing frames...',
                        'progress': 'processing',
                        'resources': resource_info
                    }
                )
            except:
                break  # Task may have completed
            
            threading.Event().wait(10)  # Update every 10 seconds
    
    # Start resource monitoring in background
    monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
    monitor_thread.start()
    
    db = SessionLocal()
    
    try:
        # Parse session start time
        session_start_dt = datetime.fromisoformat(session_start)
        
        # Update progress - initializing
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Initializing batch processor...', 'progress': 5}
        )
        
        # Get frame count for progress estimation
        import os
        from pathlib import Path
        
        frames_dir = Path(frames_directory)
        frame_count = (
            sum(1 for p in frames_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.png', '.jpg', '.jpeg'})
            if frames_dir.exists()
            else 0
        )
        
        if frame_count == 0:
            return {
                'status': 'FAILED',
                'message': f'No frames found in directory: {frames_directory}',
                'task_id': task_id,
                'user_id': user_id,
                'session_id': session_id
            }
        
        # Update progress - starting processing
        self.update_state(
            state='PROGRESS',
            meta={'status': f'Processing {frame_count} frames...', 'progress': 10}
        )
        
        # Initialize batch processor
        batch_processor = BatchFocusProcessor()
        
        # Process all frames using batch processor
        session_result = batch_processor.process_session_frames(
            user_id=user_id,
            session_id=session_id,
            frames_directory=frames_directory,
            session_start=session_start_dt,
            ground_frame_calibrated=ground_frame_calibrated,
            reference_angle=reference_angle
        )
        
        # Update progress - storing results
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Storing session results...', 'progress': 90}
        )
        
        # Store session in database
        try:
            import uuid
            
            db_session = UserSession(
                user_id=user_id,
                session_id=session_id,
                start_time=session_start_dt,
                end_time=datetime.fromisoformat(session_result["session_end"]),
                duration_seconds=session_result.get("session_duration_seconds", 0.0),
                total_frames=session_result["total_frames"],
                focused_frames=session_result["focused_frames"],
                distracted_frames=session_result["distracted_frames"],
                away_frames=session_result["away_frames"],
                focus_score=session_result["focus_score"],
                baseline_angle=session_result["baseline_angle"],
                raw_session_data=json.dumps(session_result)
            )
            db.add(db_session)
            db.commit()
            
            logger.info(f"Stored batch processed session {session_id} in database")
            
        except Exception as e:
            logger.error(f"Failed to store session in database: {e}")
            # Don't fail the task, but log the error
        
        # Final progress update
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Batch processing completed successfully',
                'progress': 100,
                'result': session_result
            }
        )
        
        return {
            'status': 'SUCCESS',
            'message': 'Session frames processed successfully',
            'task_id': task_id,
            'user_id': user_id,
            'session_id': session_id,
            'result': session_result
        }
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Batch processing task failed: {error_message}")
        
        # Update Celery task state
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Batch processing failed',
                'error': error_message,
                'progress': 0
            }
        )
        
        return {
            'status': 'FAILED',
            'message': 'Batch processing failed',
            'error': error_message,
            'task_id': task_id,
            'user_id': user_id,
            'session_id': session_id
        }
        
    finally:
        db.close()


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a Celery task.
    
    Args:
        task_id: Celery task identifier
    
    Returns:
        Task status and metadata
    """
    from celery.result import AsyncResult
    
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        'task_id': task_id,
        'status': task_result.status,
        'result': None,
        'error': None,
        'progress': 0,
        'date_done': None
    }
    
    if task_result.ready():
        if task_result.successful():
            response['result'] = task_result.get()
        else:
            response['error'] = str(task_result.info)
    elif task_result.status == 'PROGRESS':
        response.update(task_result.info)
    
    if task_result.date_done:
        response['date_done'] = task_result.date_done.isoformat()
    
    return response


def get_user_training_history(user_id: str, limit: int = 10) -> list:
    """
    Get training task history for a user.
    
    Args:
        user_id: User identifier
        limit: Maximum number of tasks to return
    
    Returns:
        List of training task records
    """
    db = SessionLocal()
    
    try:
        tasks = db.query(TrainingTask).filter(
            TrainingTask.user_id == user_id
        ).order_by(TrainingTask.created_at.desc()).limit(limit).all()
        
        return [
            {
                'task_id': task.task_id,
                'status': task.status,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'error_message': task.error_message,
                'result': json.loads(task.result) if task.result else None
            }
            for task in tasks
        ]
        
    finally:
        db.close()
