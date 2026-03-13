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
    """Session data response model."""
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
