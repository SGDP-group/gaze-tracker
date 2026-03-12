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

logger = logging.getLogger(__name__)

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
                "timestamp": datetime.now(datetime.timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error extracting face metrics: {e}")
            return None
    
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
                "session_start": datetime.now(datetime.timezone.utc).isoformat(),
                "total_frames": 0,
                "focused_frames": 0,
                "distracted_frames": 0,
                "away_frames": 0,
                "current_state": "AWAY",
                "distraction_start": None,
                "last_update": datetime.now(datetime.timezone.utc).isoformat()
            }
        
        session = self.user_sessions[user_id]
        session["total_frames"] += 1
        session["last_update"] = datetime.now(datetime.timezone.utc).isoformat()
        
        # Process face metrics
        if face_metrics is None:
            session["current_state"] = "AWAY"
            session["away_frames"] += 1
            session["distraction_start"] = None
        else:
            current_angle = face_metrics["angle"]
            
            # Update baseline with WMA (alpha=0.05)
            session["baseline_angle"] = (
                0.05 * current_angle + 
                0.95 * session["baseline_angle"]
            )
            
            # Calculate angle difference
            angle_diff = abs(current_angle - session["baseline_angle"])
            
            # Determine focus state
            now = datetime.now(datetime.timezone.utc)
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
                    if session["current_state"] != "DISTRACTED":
                        session["current_state"] = "FOCUSED"
                        session["focused_frames"] += 1
                    else:
                        session["distracted_frames"] += 1
            else:
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
        
        return {
            "user_id": user_id,
            "current_state": session["current_state"],
            "focus_score": focus_score,
            "baseline_angle": session["baseline_angle"],
            "session_stats": {
                "total_frames": session["total_frames"],
                "focused_frames": session["focused_frames"],
                "distracted_frames": session["distracted_frames"],
                "away_frames": session["away_frames"],
                "session_duration": session["total_frames"] / 30  # Assuming 30fps
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
        
        return {
            "user_id": user_id,
            "session_start": session["session_start"],
            "session_end": session["last_update"],
            "total_frames": session["total_frames"],
            "focused_frames": session["focused_frames"],
            "distracted_frames": session["distracted_frames"],
            "away_frames": session["away_frames"],
            "focus_score": focus_score,
            "baseline_angle": session["baseline_angle"]
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
        current_time = datetime.now(datetime.timezone.utc)
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
