"""
SQLAlchemy database models for the Focus Management System.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model for tracking individual users."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user")
    feedback = relationship("UserFeedback", back_populates="user")
    models = relationship("UserModel", back_populates="user")


class UserSession(Base):
    """Individual focus tracking session data."""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    session_id = Column(String, unique=True, index=True, nullable=False)
    
    # Session metadata
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    total_frames = Column(Integer, nullable=False)
    
    # Session statistics
    focused_frames = Column(Integer, nullable=False)
    distracted_frames = Column(Integer, nullable=False)
    away_frames = Column(Integer, nullable=False)
    focus_score = Column(Float, nullable=False)
    baseline_angle = Column(Float)
    
    # Raw session data (JSON string)
    raw_session_data = Column(Text)  # Stores session_data as JSON
    
    # Computed features for ML
    angle_variance = Column(Float)
    stability_score = Column(Float)
    presence_ratio = Column(Float)
    context_switches = Column(Integer)
    
    # ML predictions
    base_prediction = Column(String)  # Base model prediction
    base_confidence = Column(Float)
    personalized_prediction = Column(String)  # Personalized model prediction
    personalized_confidence = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    feedback = relationship("UserFeedback", back_populates="session", uselist=False)


class UserFeedback(Base):
    """User feedback on session productivity."""
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    session_id = Column(String, ForeignKey("user_sessions.session_id"), nullable=False)
    
    # User ratings (1-5 scale)
    productivity_rating = Column(Integer, nullable=False)  # 1=Very Unproductive, 5=Very Productive
    difficulty_rating = Column(Integer)  # Optional: 1=Very Easy, 5=Very Hard
    energy_level = Column(Integer)  # Optional: 1=Very Low, 5=Very High
    
    # Context information
    task_type = Column(String)  # e.g., "coding", "reading", "meeting"
    time_of_day = Column(String)  # e.g., "morning", "afternoon", "evening"
    interruptions = Column(Integer, default=0)
    
    # Free-form feedback
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="feedback")
    session = relationship("UserSession", back_populates="feedback")


class UserModel(Base):
    """Personalized ML models for each user."""
    __tablename__ = "user_models"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    model_version = Column(Integer, nullable=False)
    
    # Model metadata
    model_type = Column(String, default="random_forest")  # For future extensibility
    training_sessions_count = Column(Integer, nullable=False)
    last_trained = Column(DateTime, nullable=False)
    
    # Model performance metrics
    training_accuracy = Column(Float)
    validation_accuracy = Column(Float)
    
    # Model data (stored as JSON for simplicity)
    model_parameters = Column(Text)  # Serialized model parameters
    feature_importance = Column(Text)  # JSON of feature importance
    
    # Model status
    is_active = Column(Boolean, default=True)
    is_base_model = Column(Boolean, default=False)  # True for initial synthetic model
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="models")


class FocusRecommendation(Base):
    """Personalized focus time recommendations."""
    __tablename__ = "focus_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    
    # Recommendation parameters
    recommended_time_of_day = Column(String, nullable=False)
    recommended_duration_minutes = Column(Integer, nullable=False)
    confidence_score = Column(Float, nullable=False)
    
    # Recommendation reasoning
    reasoning = Column(Text)  # Why this time is recommended
    based_on_sessions = Column(Text)  # Session IDs that informed this recommendation
    
    # Recommendation metadata
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")


class TrainingTask(Base):
    """Tracking for asynchronous model training tasks."""
    __tablename__ = "training_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    
    # Task status and timing
    status = Column(String, nullable=False, default="PENDING")  # PENDING, PROGRESS, SUCCESS, FAILURE, COMPLETED
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Task results
    result = Column(Text)  # JSON string of training results
    error_message = Column(Text)
    
    # Task metadata
    task_type = Column(String, default="model_training")  # For future extensibility
    force_retrain = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User")
