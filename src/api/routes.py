"""
FastAPI routes for the Focus Management System API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from collections import defaultdict
import json
import logging

logger = logging.getLogger(__name__)

# Import configuration
from src.config import config

from src.database.database import get_db
from src.database.models import User, UserSession, UserFeedback, UserModel
from src.models.schemas import (
    UserCreate, UserResponse, SessionCreate, SessionResponse,
    FeedbackCreate, FeedbackResponse, ModelInfo, RecommendationResponse,
    TrainingRequest, TrainingResponse, TrainingTaskCreate, TrainingTaskResponse, 
    TrainingStatusResponse, AsyncTrainingResponse, SessionStatistics, TrainingHistoryResponse,
    HealthResponse as MainHealthResponse
)
from src.models.focus_schemas import (
    FrameRequest, FocusResponse, SessionStartRequest, SessionResponse as FocusSessionResponse,
    SessionData, ActiveUsersResponse, ErrorResponse, HealthResponse,
    GroundFrameRequest, GroundFrameResponse, BatchProcessRequest, BatchProcessResponse
)
from src.api.dependencies import get_current_user
from src.services.auth import create_user, get_user_by_id
from src.services.ml_service import PersonalizedMLService
from src.services.tasks import train_user_model_async, get_task_status, get_user_training_history, process_session_frames_async
from src.services.focus_service import focus_tracker
from src.services.image_stream_server import image_stream_server

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


@router.get("/health", response_model=MainHealthResponse)
def health_check(db: Session = Depends(get_db)):
    """API health check."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_connected = True
    except Exception:
        db_connected = False
    
    # Get basic stats
    total_users = db.query(User).count() if db_connected else 0
    total_sessions = db.query(UserSession).count() if db_connected else 0
    
    return MainHealthResponse(
        status="healthy" if db_connected else "unhealthy",
        database_connected=db_connected,
        total_users=total_users,
        total_sessions=total_sessions,
        timestamp=datetime.now()
    )


# ==================== Focus Tracking Endpoints ====================

@router.post("/focus/analyze", response_model=FocusResponse)
def analyze_focus_frame(frame_request: FrameRequest):
    """
    Analyze a frame for focus tracking.
    
    Args:
        frame_request: Frame data and user information
        
    Returns:
        Focus analysis results
    """
    try:
        import base64
        import io
        
        # Decode base64 frame data
        frame_data = base64.b64decode(frame_request.frame_data.split(',')[1])
        image_shape = (frame_request.image_height, frame_request.image_width)
        
        # Extract face metrics
        face_metrics = focus_tracker.extract_face_metrics(frame_data, image_shape)
        
        # Update user session
        focus_result = focus_tracker.update_user_session(frame_request.user_id, face_metrics)
        
        # Convert face metrics to response format if available
        face_metrics_response = None
        if face_metrics:
            face_metrics_response = {
                "centroid": {"x": face_metrics["centroid"][0], "y": face_metrics["centroid"][1]},
                "angle": face_metrics["angle"],
                "magnitude": face_metrics["magnitude"],
                "eye_gap": face_metrics["eye_gap"],
                "confidence": face_metrics["confidence"],
                "timestamp": face_metrics["timestamp"]
            }
        
        return FocusResponse(
            user_id=focus_result["user_id"],
            current_state=focus_result["current_state"],
            focus_score=focus_result["focus_score"],
            baseline_angle=focus_result["baseline_angle"],
            average_fps=focus_result.get("average_fps", 30.0),
            face_metrics=face_metrics_response,
            session_stats=focus_result["session_stats"],
            timestamp=datetime.fromisoformat(focus_result["timestamp"])
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Frame analysis failed: {str(e)}"
        )


@router.post("/focus/session/start", response_model=FocusSessionResponse)
def start_focus_session(session_request: SessionStartRequest):
    """
    Start a new focus tracking session for a user.
    
    Args:
        session_request: Session start request
        
    Returns:
        Session start response
    """
    try:
        import uuid
        
        # Initialize user session if not already active
        if session_request.user_id not in focus_tracker.user_sessions:
            focus_tracker.user_sessions[session_request.user_id] = {
                "user_id": session_request.user_id,
                "baseline_angle": 0.0,
                "focus_buffer": [],
                "session_start": datetime.now().isoformat(),
                "total_frames": 0,
                "focused_frames": 0,
                "distracted_frames": 0,
                "away_frames": 0,
                "current_state": "AWAY",
                "distraction_start": None,
                "last_update": datetime.now().isoformat()
            }
        
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        return FocusSessionResponse(
            user_id=session_request.user_id,
            session_id=session_id,
            session_start=datetime.now(),
            status="active",
            message=f"Focus tracking session started for user {session_request.user_id}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {str(e)}"
        )


@router.post("/focus/session/end", response_model=BatchProcessResponse)
def end_focus_session(batch_request: BatchProcessRequest, db: Session = Depends(get_db)):
    """
    End a focus tracking session and trigger batch processing of all frames.
    
    Args:
        batch_request: Batch processing request with session details
        db: Database session
        
    Returns:
        Batch processing task response
    """
    try:
        # Submit batch processing task
        task = process_session_frames_async.delay(
            user_id=batch_request.user_id,
            session_id=batch_request.session_id,
            frames_directory=batch_request.frames_directory,
            session_start=batch_request.session_start.isoformat(),
            ground_frame_calibrated=False,  # Will be auto-calibrated
            reference_angle=None  # Will be auto-calibrated
        )
        
        # Estimate frame count for response
        import os
        from pathlib import Path
        frames_dir = Path(batch_request.frames_directory)
        estimated_frames = len(list(frames_dir.glob('*.png'))) if frames_dir.exists() else None
        
        return BatchProcessResponse(
            task_id=task.id,
            status="PENDING",
            message=f"Batch processing task submitted for session {batch_request.session_id}",
            user_id=batch_request.user_id,
            session_id=batch_request.session_id,
            estimated_frames=estimated_frames,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit batch processing task: {str(e)}"
        )


@router.get("/focus/session/{session_id}/result", response_model=SessionData)
def get_batch_processing_result(session_id: str, db: Session = Depends(get_db)):
    """
    Get the result of batch processing for a completed session.
    
    Args:
        session_id: Session identifier
        db: Database session
        
    Returns:
        Complete session data with comprehensive analytics
    """
    try:
        # Get session from database
        from src.database.models import UserSession
        session = db.query(UserSession).filter(
            UserSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        # Parse raw session data
        session_data = json.loads(session.raw_session_data) if session.raw_session_data else {}
        
        # Convert comprehensive analytics to response format
        comprehensive_analytics = None
        if session_data.get("comprehensive_analytics"):
            try:
                analytics_dict = session_data["comprehensive_analytics"]
                comprehensive_analytics = {
                    "deep_work_metrics": analytics_dict.get("deep_work_metrics", {}),
                    "distraction_analytics": analytics_dict.get("distraction_analytics", {}),
                    "biological_trends": analytics_dict.get("biological_trends", {}),
                    "gamification_stats": analytics_dict.get("gamification_stats", {}),
                    "insights": analytics_dict.get("insights", [])
                }
            except Exception as e:
                logger.error(f"Error formatting comprehensive analytics: {e}")
        
        return SessionData(
            user_id=session.user_id,
            session_start=session.start_time,
            session_end=session.end_time,
            total_frames=session.total_frames,
            focused_frames=session.focused_frames,
            distracted_frames=session.distracted_frames,
            away_frames=session.away_frames,
            focus_score=session.focus_score,
            baseline_angle=session.baseline_angle,
            average_fps=session_data.get("average_fps", 30.0),
            productivity_level=session_data.get("productivity_level", "MODERATELY_PRODUCTIVE"),
            session_duration_seconds=session.duration_seconds,
            ground_frame_calibrated=session_data.get("ground_frame_calibrated", False),
            reference_angle=session_data.get("reference_angle"),
            gaze_consistency_score=session_data.get("gaze_consistency_score"),
            average_gaze_deviation=session_data.get("average_gaze_deviation"),
            comprehensive_analytics=comprehensive_analytics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session result: {str(e)}"
        )


@router.get("/focus/session/{user_id}", response_model=SessionData)
def get_session_data(user_id: str, db: Session = Depends(get_db)):
    """
    Get current session data for a user with comprehensive analytics.
    
    Args:
        user_id: User identifier
        db: Database session for historical data
        
    Returns:
        Current session data with comprehensive analytics
    """
    try:
        # Get historical sessions for enhanced analytics
        historical_sessions = []
        try:
            from src.database.models import UserSession
            sessions = db.query(UserSession).filter(
                UserSession.user_id == user_id
            ).order_by(UserSession.start_time.desc()).limit(50).all()
            
            for session in sessions:
                historical_sessions.append({
                    "session_start": session.start_time.isoformat(),
                    "session_end": session.end_time.isoformat(),
                    "total_frames": session.total_frames,
                    "focused_frames": session.focused_frames,
                    "distracted_frames": session.distracted_frames,
                    "away_frames": session.away_frames,
                    "focus_score": session.focus_score,
                    "session_duration_seconds": session.duration_seconds,
                    "completed": True
                })
        except Exception as e:
            logger.warning(f"Could not fetch historical sessions: {e}")
        
        # Get peer comparison data (limited to recent users)
        all_users_data = []
        try:
            from src.database.models import UserSession as DBUserSession, User as DBUser
            # Get recent sessions from multiple users for peer comparison
            recent_sessions = db.query(DBUserSession).join(DBUser).order_by(DBUserSession.created_at.desc()).limit(500).all()
            
            users_sessions = defaultdict(list)
            for session in recent_sessions:
                users_sessions[session.user_id].append({
                    "session_start": session.start_time.isoformat(),
                    "focus_score": session.focus_score,
                    "total_frames": session.total_frames,
                    "focused_frames": session.focused_frames,
                    "session_duration_seconds": session.duration_seconds
                })
            
            for user_id, sessions in users_sessions.items():
                if len(sessions) >= 3:  # Only include users with sufficient data
                    all_users_data.append({
                        "user_id": user_id,
                        "sessions": sessions
                    })
        except Exception as e:
            logger.warning(f"Could not fetch peer comparison data: {e}")
        
        # Get session data with comprehensive analytics
        session_data = focus_tracker.get_user_session_data(
            user_id=user_id,
            historical_sessions=historical_sessions,
            all_users_data=all_users_data
        )
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No session found for user {user_id}"
            )
        
        # Convert comprehensive analytics to response format
        comprehensive_analytics = None
        if session_data.get("comprehensive_analytics"):
            try:
                analytics_dict = session_data["comprehensive_analytics"]
                comprehensive_analytics = {
                    "deep_work_metrics": analytics_dict.get("deep_work_metrics", {}),
                    "distraction_analytics": analytics_dict.get("distraction_analytics", {}),
                    "biological_trends": analytics_dict.get("biological_trends", {}),
                    "gamification_stats": analytics_dict.get("gamification_stats", {}),
                    "insights": analytics_dict.get("insights", [])
                }
            except Exception as e:
                logger.error(f"Error formatting comprehensive analytics: {e}")
        
        return SessionData(
            user_id=session_data["user_id"],
            session_start=datetime.fromisoformat(session_data["session_start"]),
            session_end=datetime.fromisoformat(session_data["session_end"]),
            total_frames=session_data["total_frames"],
            focused_frames=session_data["focused_frames"],
            distracted_frames=session_data["distracted_frames"],
            away_frames=session_data["away_frames"],
            focus_score=session_data["focus_score"],
            baseline_angle=session_data["baseline_angle"],
            average_fps=session_data.get("average_fps", 30.0),
            productivity_level=session_data.get("productivity_level", "MODERATELY_PRODUCTIVE"),
            session_duration_seconds=session_data.get("session_duration_seconds", 0.0),
            ground_frame_calibrated=session_data.get("ground_frame_calibrated", False),
            reference_angle=session_data.get("reference_angle"),
            gaze_consistency_score=session_data.get("gaze_consistency_score"),
            average_gaze_deviation=session_data.get("average_gaze_deviation"),
            comprehensive_analytics=comprehensive_analytics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session data: {str(e)}"
        )


@router.get("/focus/users/active", response_model=ActiveUsersResponse)
def get_active_users():
    """
    Get list of currently active users.
    
    Returns:
        List of active user IDs
    """
    try:
        active_users = focus_tracker.get_active_users()
        
        return ActiveUsersResponse(
            active_users=active_users,
            total_count=len(active_users),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active users: {str(e)}"
        )


@router.post("/focus/cleanup")
def cleanup_inactive_sessions():
    """
    Clean up inactive sessions using config timeout.
    
    Returns:
        Cleanup status
    """
    try:
        focus_tracker.cleanup_inactive_sessions(timeout_minutes=config.SESSION_TIMEOUT_MINUTES)
        
        return {
            "status": "success",
            "message": "Inactive sessions cleaned up",
            "active_users": len(focus_tracker.get_active_users()),
            "timeout_minutes": config.SESSION_TIMEOUT_MINUTES,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup sessions: {str(e)}"
        )


@router.get("/focus/health", response_model=HealthResponse)
def focus_health_check():
    """
    Health check for focus tracking service.
    
    Returns:
        Service health status
    """
    try:
        active_sessions = len(focus_tracker.get_active_users())
        
        return HealthResponse(
            status="healthy",
            active_sessions=active_sessions,
            service_version="1.0.0",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Focus service unavailable: {str(e)}"
        )


@router.get("/focus/stream/health")
def focus_stream_health_check():
    """Health endpoint for the TCP image ingestion service."""
    stats = image_stream_server.get_stats()
    stats["timestamp"] = datetime.now().isoformat()
    return stats
