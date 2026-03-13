"""
Focus Tracking Service for API-based processing.
Handles frame analysis from client requests with user separation.
"""

import math
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ProductivityLevel(str, Enum):
    """Productivity classification levels."""
    HIGHLY_PRODUCTIVE = "HIGHLY_PRODUCTIVE"
    PRODUCTIVE = "PRODUCTIVE"
    MODERATELY_PRODUCTIVE = "MODERATELY_PRODUCTIVE"
    NOT_PRODUCTIVE = "NOT_PRODUCTIVE"

class FocusTracker:
    """Focus tracking service for API-based frame processing."""
    
    def __init__(self):
        """Initialize the focus tracker with MediaPipe face detector."""
        self.face_detector = None
        self.user_sessions = {}  # Track sessions per user
        self._init_face_detector()
    
    def _init_face_detector(self):
        """Initialize MediaPipe face detector."""
        try:
            base_options = python.BaseOptions(
                model_asset_path='model/detector.tflite'
            )
            options = vision.FaceDetectorOptions(
                base_options=base_options,
                min_detection_confidence=0.5
            )
            self.face_detector = vision.FaceDetector.create_from_options(options)
            logger.info("Face detector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize face detector: {e}")
            raise
    
    def _normalized_to_pixel_coordinates(
        self, 
        normalized_x: float, 
        normalized_y: float, 
        image_width: int, 
        image_height: int
    ) -> Optional[Tuple[int, int]]:
        """Convert normalized coordinates to pixel coordinates."""
        if not (0 <= normalized_x <= 1 and 0 <= normalized_y <= 1):
            return None
        
        x_px = min(math.floor(normalized_x * image_width), image_width - 1)
        y_px = min(math.floor(normalized_y * image_height), image_height - 1)
        
        return x_px, y_px
    
    def _calculate_fps(self, session: Dict) -> float:
        """Calculate rolling average FPS from frame timestamps."""
        timestamps = session.get("frame_timestamps", [])
        if not timestamps or len(timestamps) < 2:
            return 30.0  # Default FPS
        
        # Keep only timestamps from last 10 seconds
        current_time = timestamps[-1]
        ten_seconds_ago = current_time.timestamp() - 10.0
        
        recent_timestamps = [ts for ts in timestamps if ts.timestamp() >= ten_seconds_ago]
        
        if len(recent_timestamps) < 2:
            return 30.0
        
        # Calculate FPS from the time span
        time_span = (recent_timestamps[-1] - recent_timestamps[0]).total_seconds()
        if time_span > 0:
            fps = (len(recent_timestamps) - 1) / time_span
        else:
            fps = 30.0
        
        # Update FPS buffer and return rolling average
        fps_buffer = session.get("fps_buffer", [])
        fps_buffer.append(fps)
        if len(fps_buffer) > 10:  # Keep last 10 FPS calculations
            fps_buffer.pop(0)
        
        return sum(fps_buffer) / len(fps_buffer)
    
    def _classify_productivity(self, focus_score: float) -> ProductivityLevel:
        """Classify session productivity based on focus score."""
        if focus_score >= 85:
            return ProductivityLevel.HIGHLY_PRODUCTIVE
        elif focus_score >= 70:
            return ProductivityLevel.PRODUCTIVE
        elif focus_score >= 50:
            return ProductivityLevel.MODERATELY_PRODUCTIVE
        else:
            return ProductivityLevel.NOT_PRODUCTIVE
    
    def extract_face_metrics(self, frame_data: bytes, image_shape: Tuple[int, int]) -> Optional[Dict]:
        """
        Extract face metrics from frame data.
        
        Args:
            frame_data: Raw image bytes
            image_shape: (height, width) of the image
            
        Returns:
            Dictionary with face metrics or None if no face detected
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.error("Failed to decode frame")
                return None
            
            # Create MediaPipe image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            
            # Detect faces
            detection_result = self.face_detector.detect(mp_image)
            
            if not detection_result.detections:
                return None
            
            # Get first face detection
            detection = detection_result.detections[0]
            
            # Extract keypoints
            keypoints_px = []
            image_height, image_width = image_shape
            
            for keypoint in detection.keypoints:
                kp_px = self._normalized_to_pixel_coordinates(
                    keypoint.x, keypoint.y, image_width, image_height
                )
                keypoints_px.append(kp_px)
            
            if len(keypoints_px) < 4 or not all(kp is not None for kp in keypoints_px[:4]):
                return None
            
            right_eye, left_eye, nose_tip, mouth = keypoints_px[:4]
            
            # Calculate Eye Gap (depth proxy)
            eye_gap = math.sqrt(
                (right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2
            )
            
            # Calculate Centroid with 20% vertical offset
            centroid_x = round((left_eye[0] + right_eye[0] + mouth[0]) / 3)
            centroid_y = round((left_eye[1] + right_eye[1] + mouth[1]) / 3) + round(eye_gap * 0.2)
            centroid = (centroid_x, centroid_y)
            
            # Focus Vector: from centroid to nose tip
            vx = nose_tip[0] - centroid_x
            vy = nose_tip[1] - centroid_y
            
            # Yaw Angle via atan2
            angle = math.degrees(math.atan2(vy, vx))
            
            # Vector Magnitude
            magnitude = math.sqrt(vx**2 + vy**2)
            
            return {
                "centroid": centroid,
                "angle": angle,
                "magnitude": magnitude,
                "eye_gap": eye_gap,
                "confidence": detection.categories[0].score,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error extracting face metrics: {e}")
            return None
    
    def calibrate_ground_frame(self, user_id: str, frame_data: bytes, image_shape: Tuple[int, int]) -> Dict:
        """
        Calibrate ground frame for gaze direction reference.
        
        Args:
            user_id: Unique user identifier
            frame_data: Raw image bytes for ground frame
            image_shape: (height, width) of the image
            
        Returns:
            Calibration result with reference angle and metrics
        """
        try:
            # Extract face metrics from ground frame
            face_metrics = self.extract_face_metrics(frame_data, image_shape)
            
            if face_metrics is None:
                return {
                    "success": False,
                    "error": "No face detected in ground frame",
                    "message": "Please ensure your face is clearly visible in the ground frame"
                }
            
            # Initialize session if not exists
            if user_id not in self.user_sessions:
                self.update_user_session(user_id, None)  # Create empty session
            
            session = self.user_sessions[user_id]
            
            # Store ground frame reference
            session["ground_frame_calibrated"] = True
            session["reference_angle"] = face_metrics["angle"]
            session["reference_magnitude"] = face_metrics["magnitude"]
            session["gaze_deviations"] = []
            session["gaze_consistency_buffer"] = []
            
            return {
                "success": True,
                "user_id": user_id,
                "reference_angle": face_metrics["angle"],
                "reference_magnitude": face_metrics["magnitude"],
                "confidence": face_metrics["confidence"],
                "message": "Ground frame calibrated successfully",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calibrating ground frame: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to calibrate ground frame"
            }
    
    def _calculate_gaze_consistency(self, session: Dict, current_angle: float) -> Dict:
        """
        Calculate gaze consistency based on deviation from reference angle.
        
        Args:
            session: User session data
            current_angle: Current gaze angle
            
        Returns:
            Gaze consistency metrics
        """
        if not session.get("ground_frame_calibrated") or session.get("reference_angle") is None:
            return {
                "gaze_consistency_score": None,
                "gaze_deviation": None,
                "is_consistent": None
            }
        
        reference_angle = session["reference_angle"]
        gaze_deviation = abs(current_angle - reference_angle)
        
        # Track deviation
        session["gaze_deviations"].append(gaze_deviation)
        
        # Keep only last 50 deviations
        if len(session["gaze_deviations"]) > 50:
            session["gaze_deviations"].pop(0)
        
        # Calculate consistency score (100 = perfect alignment, 0 = completely off)
        max_acceptable_deviation = 30.0  # degrees
        consistency_score = max(0, 100 - (gaze_deviation / max_acceptable_deviation) * 100)
        
        # Update consistency buffer
        session["gaze_consistency_buffer"].append(consistency_score)
        if len(session["gaze_consistency_buffer"]) > 50:
            session["gaze_consistency_buffer"].pop(0)
        
        # Calculate rolling average consistency
        if session["gaze_consistency_buffer"]:
            avg_consistency = sum(session["gaze_consistency_buffer"]) / len(session["gaze_consistency_buffer"])
        else:
            avg_consistency = consistency_score
        
        return {
            "gaze_consistency_score": avg_consistency,
            "gaze_deviation": gaze_deviation,
            "is_consistent": gaze_deviation <= max_acceptable_deviation
        }
    
    def update_user_session(self, user_id: str, face_metrics: Optional[Dict]) -> Dict:
        """
        Update user's focus tracking session.
        
        Args:
            user_id: Unique user identifier
            face_metrics: Face metrics from current frame
            
        Returns:
            Current focus state and session data
        """
        # Initialize user session if not exists
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "user_id": user_id,
                "baseline_angle": 0.0,
                "focus_buffer": [],
                "session_start": datetime.now().isoformat(),
                "total_frames": 0,
                "focused_frames": 0,
                "distracted_frames": 0,
                "away_frames": 0,
                "current_state": "AWAY",
                "distraction_start": None,
                "last_update": datetime.now().isoformat(),
                "frame_timestamps": [],  # Track frame timestamps for FPS calculation
                "fps_buffer": [],  # Rolling FPS buffer
                # Ground frame calibration data
                "ground_frame_calibrated": False,
                "reference_angle": None,
                "reference_magnitude": None,
                "gaze_deviations": [],  # Track deviations from reference angle
                "gaze_consistency_buffer": []  # Track gaze consistency over time
            }
        
        session = self.user_sessions[user_id]
        session["total_frames"] += 1
        current_time = datetime.now()
        session["last_update"] = current_time.isoformat()
        
        # Track frame timestamp for FPS calculation
        if "frame_timestamps" not in session:
            session["frame_timestamps"] = []
        session["frame_timestamps"].append(current_time)
        
        # Process face metrics
        if face_metrics is None:
            session["current_state"] = "AWAY"
            session["away_frames"] += 1
            session["distraction_start"] = None
        else:
            current_angle = face_metrics["angle"]
            
            # Calculate gaze consistency if ground frame is calibrated
            gaze_metrics = self._calculate_gaze_consistency(session, current_angle)
            
            # Update baseline with WMA (alpha=0.05)
            session["baseline_angle"] = (
                0.05 * current_angle + 
                0.95 * session["baseline_angle"]
            )
            
            # Calculate angle difference
            angle_diff = abs(current_angle - session["baseline_angle"])
            
            # Determine focus state
            now = datetime.now()
            if angle_diff < 20:
                session["current_state"] = "FOCUSED"
                session["focused_frames"] += 1
                session["distraction_start"] = None
            elif angle_diff > 30:
                if session["distraction_start"] is None:
                    session["distraction_start"] = now
                
                elapsed = (now - session["distraction_start"]).total_seconds()
                if elapsed >= 2.0:
                    session["current_state"] = "DISTRACTED"
                    session["distracted_frames"] += 1
                else:
                    # Grace period: not yet confirmed as distracted
                    session["current_state"] = "FOCUSED"
                    session["focused_frames"] += 1
                    session["distraction_start"] = None
            else:
                # Angle between 20-30 degrees, consider as FOCUSED
                session["current_state"] = "FOCUSED"
                session["focused_frames"] += 1
                session["distraction_start"] = None
        
        # Update focus buffer (keep last 50 states)
        session["focus_buffer"].append(session["current_state"])
        if len(session["focus_buffer"]) > 50:
            session["focus_buffer"].pop(0)
        
        # Calculate focus score
        if session["focus_buffer"]:
            focused_count = sum(1 for state in session["focus_buffer"] if state == "FOCUSED")
            focus_score = (focused_count / len(session["focus_buffer"])) * 100
        else:
            focus_score = 0.0
        
        # Calculate FPS (rolling average of last 10 seconds)
        avg_fps = self._calculate_fps(session)
        
        # Get gaze consistency metrics
        gaze_consistency_score = gaze_metrics.get("gaze_consistency_score") if 'gaze_metrics' in locals() else None
        gaze_deviation = gaze_metrics.get("gaze_deviation") if 'gaze_metrics' in locals() else None
        is_consistent = gaze_metrics.get("is_consistent") if 'gaze_metrics' in locals() else None
        
        return {
            "user_id": user_id,
            "current_state": session["current_state"],
            "focus_score": focus_score,
            "baseline_angle": session["baseline_angle"],
            "average_fps": avg_fps,
            "session_stats": {
                "total_frames": session["total_frames"],
                "focused_frames": session["focused_frames"],
                "distracted_frames": session["distracted_frames"],
                "away_frames": session["away_frames"],
                "session_duration": session["total_frames"] / max(avg_fps, 1),  # Use actual FPS
                "ground_frame_calibrated": session.get("ground_frame_calibrated", False),
                "gaze_consistency_score": gaze_consistency_score,
                "gaze_deviation": gaze_deviation,
                "is_consistent": is_consistent
            },
            "timestamp": session["last_update"]
        }
    
    def get_user_session_data(self, user_id: str) -> Optional[Dict]:
        """Get complete session data for a user."""
        if user_id not in self.user_sessions:
            return None
        
        session = self.user_sessions[user_id]
        
        # Calculate final metrics
        if session["focus_buffer"]:
            focused_count = sum(1 for state in session["focus_buffer"] if state == "FOCUSED")
            focus_score = (focused_count / len(session["focus_buffer"])) * 100
        else:
            focus_score = 0.0
        
        # Calculate average FPS for the session
        try:
            avg_fps = self._calculate_fps(session)
        except:
            avg_fps = 30.0  # Default FPS if calculation fails
        
        # Classify productivity
        productivity_level = self._classify_productivity(focus_score)
        
        # Calculate ground frame metrics
        gaze_consistency_score = None
        average_gaze_deviation = None
        
        if session.get("ground_frame_calibrated") and session.get("gaze_deviations"):
            gaze_consistency_score = sum(session["gaze_consistency_buffer"]) / len(session["gaze_consistency_buffer"]) if session["gaze_consistency_buffer"] else None
            average_gaze_deviation = sum(session["gaze_deviations"]) / len(session["gaze_deviations"]) if session["gaze_deviations"] else None
        
        return {
            "user_id": user_id,
            "session_start": session["session_start"],
            "session_end": session["last_update"],
            "total_frames": session["total_frames"],
            "focused_frames": session["focused_frames"],
            "distracted_frames": session["distracted_frames"],
            "away_frames": session["away_frames"],
            "focus_score": focus_score,
            "baseline_angle": session["baseline_angle"],
            "average_fps": avg_fps,
            "productivity_level": productivity_level.value,
            "session_duration_seconds": session["total_frames"] / max(avg_fps, 1),
            # Ground frame metrics
            "ground_frame_calibrated": session.get("ground_frame_calibrated", False),
            "reference_angle": session.get("reference_angle"),
            "gaze_consistency_score": gaze_consistency_score,
            "average_gaze_deviation": average_gaze_deviation
        }
    
    def end_user_session(self, user_id: str) -> Optional[Dict]:
        """End user session and return final data."""
        session_data = self.get_user_session_data(user_id)
        
        if session_data:
            # Remove from active sessions
            del self.user_sessions[user_id]
            logger.info(f"Ended session for user {user_id}")
        
        return session_data
    
    def get_active_users(self) -> List[str]:
        """Get list of currently active user IDs."""
        return list(self.user_sessions.keys())
    
    def cleanup_inactive_sessions(self, timeout_minutes: int = 30):
        """Clean up inactive sessions."""
        current_time = datetime.now()
        inactive_users = []
        
        for user_id, session in self.user_sessions.items():
            last_update = datetime.fromisoformat(session["last_update"])
            inactive_duration = (current_time - last_update).total_seconds() / 60
            
            if inactive_duration > timeout_minutes:
                inactive_users.append(user_id)
        
        for user_id in inactive_users:
            self.end_user_session(user_id)
            logger.info(f"Cleaned up inactive session for user {user_id}")


# Global focus tracker instance
focus_tracker = FocusTracker()
