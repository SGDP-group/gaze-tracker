"""
Celery tasks for asynchronous model training and processing.
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from celery import current_task

from src.services.celery_app import celery_app
from src.services.ml_service import PersonalizedMLService
from src.database.database import SessionLocal
from src.database.models import UserModel, TrainingTask


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
