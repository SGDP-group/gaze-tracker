"""
Pydantic models for focus tracking API endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class FocusState(str, Enum):
    """Focus state enumeration."""
    FOCUSED = "FOCUSED"
    DISTRACTED = "DISTRACTED"
    AWAY = "AWAY"

class DeepWorkMetrics(BaseModel):
    """Core Deep Work Metrics."""
    focus_duration: Dict[str, float] = Field(..., description="Focus duration metrics")
    focus_to_rest_ratio: float = Field(..., description="Ratio of focus to rest time")
    longest_focus_streak: Dict[str, float] = Field(..., description="Longest uninterrupted focus streak")
    session_completion_rate: float = Field(..., description="Percentage of completed sessions")
    focus_efficiency: float = Field(..., description="Focus efficiency percentage")

class DistractionAnalytics(BaseModel):
    """Distraction & Interference Analytics."""
    interruption_count: int = Field(..., description="Number of significant interruptions")
    context_switching_cost: Dict[str, float] = Field(..., description="Time lost to context switching")
    distraction_patterns: Dict[str, Any] = Field(..., description="Patterns in distractions")
    recovery_metrics: Dict[str, Any] = Field(..., description="Recovery time metrics")
    distraction_frequency: float = Field(..., description="Frequency of distractions")

class BiologicalTrends(BaseModel):
    """Biological & Rhythmic Trends."""
    focus_heatmap: List[Dict[str, Any]] = Field(..., description="Focus heatmap by hour/day")
    peak_performance_times: List[Dict[str, Any]] = Field(..., description="Peak performance times")
    rhythmic_insights: Dict[str, Any] = Field(..., description="Rhythmic pattern insights")

class GamificationStats(BaseModel):
    """Gamification & Retention Stats."""
    focus_streaks: Dict[str, Any] = Field(..., description="Focus streak information")
    peer_comparison: Dict[str, Any] = Field(..., description="Peer comparison metrics")
    achievements: List[Dict[str, Any]] = Field(..., description="User achievements")
    retention_metrics: Dict[str, Any] = Field(..., description="Retention metrics")

class ComprehensiveAnalytics(BaseModel):
    """Comprehensive session analytics."""
    deep_work_metrics: DeepWorkMetrics = Field(..., description="Core deep work metrics")
    distraction_analytics: DistractionAnalytics = Field(..., description="Distraction analytics")
    biological_trends: BiologicalTrends = Field(..., description="Biological trends")
    gamification_stats: GamificationStats = Field(..., description="Gamification stats")
    insights: List[str] = Field(..., description="Personalized insights")

class FrameRequest(BaseModel):
    """Request model for frame analysis."""
    user_id: str = Field(..., description="Unique user identifier")
    frame_data: str = Field(..., description="Base64 encoded image data")
    image_width: int = Field(..., description="Image width in pixels")
    image_height: int = Field(..., description="Image height in pixels")
    timestamp: Optional[datetime] = Field(None, description="Frame timestamp")

class FaceMetrics(BaseModel):
    """Face metrics extracted from frame."""
    centroid: Dict[str, int] = Field(..., description="Face centroid coordinates")
    angle: float = Field(..., description="Face yaw angle in degrees")
    magnitude: float = Field(..., description="Focus vector magnitude")
    eye_gap: float = Field(..., description="Distance between eyes")
    confidence: float = Field(..., description="Detection confidence")
    timestamp: datetime = Field(..., description="Metrics timestamp")

class FocusResponse(BaseModel):
    """Response model for focus analysis."""
    user_id: str = Field(..., description="User identifier")
    current_state: FocusState = Field(..., description="Current focus state")
    focus_score: float = Field(..., description="Focus score (0-100)")
    baseline_angle: float = Field(..., description="Current baseline angle")
    average_fps: float = Field(..., description="Current average FPS")
    face_metrics: Optional[FaceMetrics] = Field(None, description="Face metrics if detected")
    session_stats: Dict[str, Any] = Field(..., description="Session statistics")
    timestamp: datetime = Field(..., description="Response timestamp")

class GroundFrameRequest(BaseModel):
    """Request model for ground frame calibration."""
    user_id: str = Field(..., description="User identifier")
    frame_data: str = Field(..., description="Base64 encoded image data for ground frame")
    image_width: int = Field(..., description="Image width")
    image_height: int = Field(..., description="Image height")


class GroundFrameResponse(BaseModel):
    """Response model for ground frame calibration."""
    success: bool = Field(..., description="Calibration success status")
    user_id: str = Field(..., description="User identifier")
    reference_angle: float = Field(..., description="Reference gaze angle for calibration")
    reference_magnitude: float = Field(..., description="Reference gaze magnitude")
    confidence: float = Field(..., description="Face detection confidence")
    message: str = Field(..., description="Calibration message")
    timestamp: datetime = Field(..., description="Calibration timestamp")


class SessionStartRequest(BaseModel):
    """Request model for starting a focus session."""
    user_id: str = Field(..., description="Unique user identifier")
    session_name: Optional[str] = Field(None, description="Optional session name")
    settings: Optional[Dict[str, Any]] = Field(None, description="Session settings")

class SessionResponse(BaseModel):
    """Response model for session operations."""
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    session_start: datetime = Field(..., description="Session start time")
    status: str = Field(..., description="Session status")
    message: str = Field(..., description="Status message")

class SessionData(BaseModel):
    """Session data response model with comprehensive analytics."""
    user_id: str = Field(..., description="User identifier")
    session_start: datetime = Field(..., description="Session start time")
    session_end: datetime = Field(..., description="Session end time")
    total_frames: int = Field(..., description="Total frames processed")
    focused_frames: int = Field(..., description="Number of focused frames")
    distracted_frames: int = Field(..., description="Number of distracted frames")
    away_frames: int = Field(..., description="Number of away frames")
    focus_score: float = Field(..., description="Overall focus score (0-100)")
    baseline_angle: float = Field(..., description="Final baseline angle")
    average_fps: float = Field(..., description="Average frames per second")
    productivity_level: str = Field(..., description="Productivity classification level")
    session_duration_seconds: float = Field(..., description="Session duration in seconds")
    # Ground frame metrics
    ground_frame_calibrated: bool = Field(False, description="Whether ground frame was calibrated")
    reference_angle: Optional[float] = Field(None, description="Reference gaze angle from ground frame")
    gaze_consistency_score: Optional[float] = Field(None, description="Gaze consistency score (0-100)")
    average_gaze_deviation: Optional[float] = Field(None, description="Average deviation from reference angle")
    # Comprehensive analytics
    comprehensive_analytics: Optional[ComprehensiveAnalytics] = Field(None, description="Comprehensive session analytics")

class ActiveUsersResponse(BaseModel):
    """Response model for active users endpoint."""
    active_users: List[str] = Field(..., description="List of active user IDs")
    total_count: int = Field(..., description="Total number of active users")
    timestamp: datetime = Field(..., description="Response timestamp")

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    active_sessions: int = Field(..., description="Number of active sessions")
    service_version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Health check timestamp")

class BatchProcessRequest(BaseModel):
    """Request model for batch processing session frames."""
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    frames_directory: str = Field(..., description="Directory path containing session frames")
    session_start: datetime = Field(..., description="Session start time")

class BatchProcessResponse(BaseModel):
    """Response model for batch processing initiation."""
    task_id: str = Field(..., description="Celery task ID for batch processing")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    estimated_frames: Optional[int] = Field(None, description="Estimated number of frames to process")
    timestamp: datetime = Field(..., description="Response timestamp")
