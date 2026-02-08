"""
FastAPI routes for the Focus Management System API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from src.database.database import get_db
from src.database.models import User, UserSession, UserFeedback, UserModel
from src.models.schemas import (
    UserCreate, UserResponse, SessionCreate, SessionResponse,
    FeedbackCreate, FeedbackResponse, ModelInfo, TrainingRequest,
    TrainingResponse, RecommendationResponse, SessionStatistics,
    HealthResponse, TrainingTaskCreate, TrainingTaskResponse,
    TrainingStatusResponse, TrainingHistoryResponse, AsyncTrainingResponse
)
from src.api.dependencies import get_current_user
from src.services.auth import create_user, get_user_by_id
from src.services.ml_service import PersonalizedMLService
from src.services.tasks import train_user_model_async, get_task_status, get_user_training_history

# Initialize services
ml_service = PersonalizedMLService()

# Create router
router = APIRouter()


@router.post("/users", response_model=UserResponse)
def create_new_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user with API key."""
    # Check if user already exists
    existing_user = get_user_by_id(db, user.user_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    
    # Create new user
    db_user = create_user(db, user.user_id)
    return db_user


@router.get("/users/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.post("/sessions", response_model=SessionResponse)
def create_session(
    session: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new focus session."""
    # Verify user ID matches authenticated user
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID mismatch"
        )
    
    # Check if session already exists
    existing_session = db.query(UserSession).filter(
        UserSession.session_id == session.session_id
    ).first()
    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already exists"
        )
    
    # Create session
    db_session = UserSession(**session.dict())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    # Generate personalized prediction if user has enough data
    if db_session.angle_variance is not None:
        session_features = {
            'angle_variance': db_session.angle_variance,
            'stability_score': db_session.stability_score or 0,
            'presence_ratio': db_session.presence_ratio or 0,
            'context_switches': db_session.context_switches or 0
        }
        
        try:
            prediction, confidence = ml_service.predict_session_productivity(
                db, session.user_id, session_features
            )
            db_session.personalized_prediction = prediction
            db_session.personalized_confidence = confidence
            db.commit()
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error generating personalized prediction: {e}")
    
    return db_session


@router.get("/sessions", response_model=List[SessionResponse])
def get_user_sessions(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's sessions with pagination."""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.user_id
    ).order_by(UserSession.created_at.desc()).offset(offset).limit(limit).all()
    
    return sessions


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific session details."""
    session = db.query(UserSession).filter(
        UserSession.session_id == session_id,
        UserSession.user_id == current_user.user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return session


@router.post("/feedback", response_model=FeedbackResponse)
def create_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback for a session."""
    # Verify user ID
    if feedback.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID mismatch"
        )
    
    # Verify session exists and belongs to user
    session = db.query(UserSession).filter(
        UserSession.session_id == feedback.session_id,
        UserSession.user_id == current_user.user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if feedback already exists
    existing_feedback = db.query(UserFeedback).filter(
        UserFeedback.session_id == feedback.session_id
    ).first()
    
    if existing_feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback already exists for this session"
        )
    
    # Create feedback
    db_feedback = UserFeedback(**feedback.dict())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    
    return db_feedback


@router.get("/models", response_model=List[ModelInfo])
def get_user_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's ML models."""
    models = db.query(UserModel).filter(
        UserModel.user_id == current_user.user_id
    ).order_by(UserModel.model_version.desc()).all()
    
    return models


@router.post("/models/train", response_model=TrainingResponse)
def train_user_model(
    training_request: TrainingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Train personalized model for user."""
    # Verify user ID
    if training_request.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID mismatch"
        )
    
    try:
        result = ml_service.train_personalized_model(
            db, training_request.user_id, training_request.force_retrain
        )
        
        return TrainingResponse(
            user_id=training_request.user_id,
            model_version=result["model_version"],
            training_sessions_count=result["training_sessions_count"],
            training_accuracy=result["training_accuracy"],
            validation_accuracy=result.get("validation_accuracy"),
            feature_importance=result["feature_importance"],
            training_time_seconds=result["training_time_seconds"],
            message=result["message"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training failed: {str(e)}"
        )


@router.get("/recommendations", response_model=List[RecommendationResponse])
def get_focus_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get personalized focus recommendations."""
    try:
        recommendations = ml_service.generate_focus_recommendations(db, current_user.user_id)
        
        # Convert database models to response models
        response_recommendations = []
        for rec in recommendations:
            response_recommendations.append(RecommendationResponse(**rec))
        
        return response_recommendations
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.get("/statistics", response_model=SessionStatistics)
def get_user_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's session statistics."""
    try:
        stats = ml_service.get_user_statistics(db, current_user.user_id)
        return SessionStatistics(**stats)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.post("/models/train/async", response_model=AsyncTrainingResponse)
def train_user_model_async_endpoint(
    training_request: TrainingTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start asynchronous model training for user."""
    # Verify user ID
    if training_request.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID mismatch"
        )
    
    try:
        # Submit async training task
        task = train_user_model_async.delay(
            user_id=training_request.user_id,
            force_retrain=training_request.force_retrain
        )
        
        return AsyncTrainingResponse(
            task_id=task.id,
            status="PENDING",
            message="Model training task submitted successfully",
            user_id=training_request.user_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit training task: {str(e)}"
        )


@router.get("/models/train/status/{task_id}", response_model=TrainingStatusResponse)
def get_training_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of a training task."""
    try:
        task_status = get_task_status(task_id)
        
        # Verify task belongs to current user (additional security)
        if task_status.get('result') and 'user_id' in task_status['result']:
            if task_status['result']['user_id'] != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this task"
                )
        
        return TrainingStatusResponse(**task_status)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get("/models/train/history", response_model=List[TrainingHistoryResponse])
def get_user_training_history_endpoint(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's training task history."""
    try:
        history = get_user_training_history(current_user.user_id, limit)
        
        return [TrainingHistoryResponse(**task) for task in history]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get training history: {str(e)}"
        )


@router.get("/models/train/tasks", response_model=List[TrainingTaskResponse])
def get_user_training_tasks(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's training tasks from database."""
    try:
        from src.database.models import TrainingTask
        
        tasks = db.query(TrainingTask).filter(
            TrainingTask.user_id == current_user.user_id
        ).order_by(TrainingTask.created_at.desc()).limit(limit).all()
        
        return tasks
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get training tasks: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """API health check."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_connected = True
    except:
        db_connected = False
    
    # Get basic stats
    total_users = db.query(User).count() if db_connected else 0
    total_sessions = db.query(UserSession).count() if db_connected else 0
    
    return HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        database_connected=db_connected,
        total_users=total_users,
        total_sessions=total_sessions,
        timestamp=datetime.utcnow()
    )
