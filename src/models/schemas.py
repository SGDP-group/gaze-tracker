"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserCreate(BaseModel):
    """Request model for creating a new user."""
    user_id: str = Field(..., description="Unique user identifier")


class UserResponse(BaseModel):
    """Response model for user data."""
    user_id: str
    api_key: str
    created_at: datetime
    last_active: datetime
    
    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    """Request model for creating a new session."""
    user_id: str
    session_id: str
    
    # Session metadata
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_frames: int
    
    # Session statistics
    focused_frames: int
    distracted_frames: int
    away_frames: int
    focus_score: float
    baseline_angle: Optional[float] = None
    
    # Raw session data (JSON)
    raw_session_data: str
    
    # Computed features
    angle_variance: Optional[float] = None
    stability_score: Optional[float] = None
    presence_ratio: Optional[float] = None
    context_switches: Optional[int] = None
    
    # Base model predictions
    base_prediction: Optional[str] = None
    base_confidence: Optional[float] = None


class SessionResponse(BaseModel):
    """Response model for session data."""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_frames: int
    focused_frames: int
    distracted_frames: int
    away_frames: int
    focus_score: float
    baseline_angle: Optional[float]
    angle_variance: Optional[float]
    stability_score: Optional[float]
    presence_ratio: Optional[float]
    context_switches: Optional[int]
    base_prediction: Optional[str]
    base_confidence: Optional[float]
    personalized_prediction: Optional[str]
    personalized_confidence: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    """Request model for user feedback."""
    user_id: str
    session_id: str
    
    # Ratings (1-5 scale)
    productivity_rating: int = Field(..., ge=1, le=5, description="Productivity rating (1-5)")
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5, description="Difficulty rating (1-5)")
    energy_level: Optional[int] = Field(None, ge=1, le=5, description="Energy level (1-5)")
    
    # Context
    task_type: Optional[str] = Field(None, description="Type of task performed")
    time_of_day: Optional[str] = Field(None, description="Time of day")
    interruptions: Optional[int] = Field(0, ge=0, description="Number of interruptions")
    
    # Free-form
    notes: Optional[str] = Field(None, description="Additional notes")


class FeedbackResponse(BaseModel):
    """Response model for feedback data."""
    id: int
    user_id: str
    session_id: str
    productivity_rating: int
    difficulty_rating: Optional[int]
    energy_level: Optional[int]
    task_type: Optional[str]
    time_of_day: Optional[str]
    interruptions: int
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ModelInfo(BaseModel):
    """Response model for user model information."""
    user_id: str
    model_version: int
    model_type: str
    training_sessions_count: int
    last_trained: datetime
    training_accuracy: Optional[float]
    validation_accuracy: Optional[float]
    is_active: bool
    is_base_model: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TrainingRequest(BaseModel):
    """Request model for triggering model training."""
    user_id: str
    force_retrain: Optional[bool] = Field(False, description="Force retraining even if model exists")


class TrainingResponse(BaseModel):
    """Response model for training results."""
    user_id: str
    model_version: int
    training_sessions_count: int
    training_accuracy: float
    validation_accuracy: Optional[float]
    feature_importance: Dict[str, float]
    training_time_seconds: float
    message: str


class RecommendationResponse(BaseModel):
    """Response model for focus recommendations."""
    user_id: str
    recommended_time_of_day: str
    recommended_duration_minutes: int
    confidence_score: float
    reasoning: str
    based_on_sessions: List[str]
    valid_from: datetime
    valid_until: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class SessionStatistics(BaseModel):
    """Statistics for user sessions."""
    total_sessions: int
    total_duration_hours: float
    average_focus_score: float
    most_productive_time: Optional[str]
    average_session_duration_minutes: float
    total_focused_hours: float
    productivity_trend: str  # "improving", "declining", "stable"


class HealthResponse(BaseModel):
    """API health check response."""
    status: str
    database_connected: bool
    total_users: int
    total_sessions: int
    timestamp: datetime


class TrainingTaskCreate(BaseModel):
    """Request model for creating a training task."""
    user_id: str
    force_retrain: Optional[bool] = Field(False, description="Force retraining even if model exists")


class TrainingTaskResponse(BaseModel):
    """Response model for training task status."""
    task_id: str
    user_id: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    error_message: Optional[str]
    result: Optional[Dict[str, Any]]
    task_type: str
    force_retrain: bool
    
    class Config:
        from_attributes = True


class TrainingStatusResponse(BaseModel):
    """Response model for training task status."""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    progress: Optional[int]
    date_done: Optional[datetime]


class TrainingHistoryResponse(BaseModel):
    """Response model for user training history."""
    task_id: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    result: Optional[Dict[str, Any]]


class AsyncTrainingResponse(BaseModel):
    """Response model for async training request."""
    task_id: str
    status: str
    message: str
    user_id: str
