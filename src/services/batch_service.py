"""
Batch Processing Service for handling frame directory processing at session end.
Processes all frames for a user session in timestamp order using a single-user approach.
"""

import os
import cv2
import numpy as np
import math
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from enum import Enum
import shutil

logger = logging.getLogger(__name__)

from src.config import config
from src.services.analytics_service import analytics_service

class ProductivityLevel(str, Enum):
    """Productivity classification levels."""
    HIGHLY_PRODUCTIVE = "HIGHLY_PRODUCTIVE"
    PRODUCTIVE = "PRODUCTIVE"
    MODERATELY_PRODUCTIVE = "MODERATELY_PRODUCTIVE"
    NOT_PRODUCTIVE = "NOT_PRODUCTIVE"

class BatchFocusProcessor:
    """Batch processor for focus tracking from frame directories."""
    
    def __init__(self):
        """Initialize the batch processor with MediaPipe face detector."""
        self.face_detector = None
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
            logger.info("Face detector initialized successfully for batch processing")
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
    
    def _extract_timestamp_from_filename(self, filename: str) -> float:
        """Extract timestamp from filename (timestamp.png format)."""
        try:
            # Remove .png extension and convert to float
            timestamp_str = filename.replace('.png', '')
            return float(timestamp_str)
        except (ValueError, AttributeError):
            # Fallback to current time if timestamp parsing fails
            return datetime.now().timestamp()
    
    def _get_sorted_frame_files(self, frames_directory: str) -> List[Tuple[str, float]]:
        """Get sorted list of frame files with their timestamps."""
        frames_dir = Path(frames_directory)
        
        if not frames_dir.exists():
            raise FileNotFoundError(f"Frames directory not found: {frames_directory}")
        
        frame_files = []
        pattern = re.compile(r'^\d+\.png$')  # Match timestamp.png pattern
        
        for file_path in frames_dir.glob('*.png'):
            if pattern.match(file_path.name):
                timestamp = self._extract_timestamp_from_filename(file_path.name)
                frame_files.append((str(file_path), timestamp))
        
        # Sort by timestamp
        frame_files.sort(key=lambda x: x[1])
        
        logger.info(f"Found {len(frame_files)} frame files in {frames_directory}")
        return frame_files
    
    def _extract_face_metrics_from_file(self, frame_path: str) -> Optional[Dict]:
        """
        Extract face metrics from a frame file.
        
        Args:
            frame_path: Path to the frame image file
            
        Returns:
            Dictionary with face metrics or None if no face detected
        """
        try:
            # Read image from file
            frame = cv2.imread(frame_path)
            if frame is None:
                logger.error(f"Failed to read frame: {frame_path}")
                return None
            
            image_height, image_width = frame.shape[:2]
            
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
            logger.error(f"Error extracting face metrics from {frame_path}: {e}")
            return None
    
    def _calculate_gaze_consistency(self, session_data: Dict, current_angle: float) -> Dict:
        """
        Calculate gaze consistency based on deviation from reference angle.
        
        Args:
            session_data: Session data dictionary
            current_angle: Current gaze angle
            
        Returns:
            Gaze consistency metrics
        """
        if not session_data.get("ground_frame_calibrated") or session_data.get("reference_angle") is None:
            return {
                "gaze_consistency_score": None,
                "gaze_deviation": None,
                "is_consistent": None
            }
        
        reference_angle = session_data["reference_angle"]
        
        # Normalize angles to handle circular nature (e.g., 180° and -180° are the same)
        def normalize_angle(angle):
            """Normalize angle to [-180, 180] range"""
            while angle > 180:
                angle -= 360
            while angle < -180:
                angle += 360
            return angle
        
        ref_angle_norm = normalize_angle(reference_angle)
        curr_angle_norm = normalize_angle(current_angle)
        
        # Calculate minimum angular distance
        raw_diff = abs(curr_angle_norm - ref_angle_norm)
        gaze_deviation = min(raw_diff, 360 - raw_diff)
        
        # Track deviation
        session_data["gaze_deviations"].append(gaze_deviation)
        
        # Keep only last 50 deviations
        if len(session_data["gaze_deviations"]) > 50:
            session_data["gaze_deviations"].pop(0)
        
        # Calculate consistency score (100 = perfect alignment, 0 = completely off)
        max_acceptable_deviation = 30.0  # degrees
        consistency_score = max(0, 100 - (gaze_deviation / max_acceptable_deviation) * 100)
        
        # Update consistency buffer
        session_data["gaze_consistency_buffer"].append(consistency_score)
        if len(session_data["gaze_consistency_buffer"]) > 50:
            session_data["gaze_consistency_buffer"].pop(0)
        
        # Calculate rolling average consistency
        if session_data["gaze_consistency_buffer"]:
            avg_consistency = sum(session_data["gaze_consistency_buffer"]) / len(session_data["gaze_consistency_buffer"])
        else:
            avg_consistency = consistency_score
        
        return {
            "gaze_consistency_score": avg_consistency,
            "gaze_deviation": gaze_deviation,
            "is_consistent": gaze_deviation <= max_acceptable_deviation
        }
    
    def _calculate_inconsistency_penalty(self, focus_buffer: List[str]) -> float:
        """Calculate penalty for inconsistent focus patterns."""
        if not config.INCONSISTENCY_PENALTY_ENABLED or len(focus_buffer) < 10:
            return 0.0
        
        # Count state changes
        state_changes = 0
        for i in range(1, len(focus_buffer)):
            if focus_buffer[i] != focus_buffer[i-1]:
                state_changes += 1
        
        # Calculate penalty based on change frequency
        max_possible_changes = len(focus_buffer) - 1
        change_frequency = state_changes / max_possible_changes
        
        # Apply penalty factor
        penalty = change_frequency * config.INCONSISTENCY_PENALTY_FACTOR * 100
        
        # Cap at maximum penalty
        penalty = min(penalty, config.MAX_INCONSISTENCY_PENALTY)
        
        return penalty
    
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
    
    def _cleanup_frames_directory(self, frames_directory: str) -> bool:
        """
        Clean up frames directory by deleting all frames and the directory itself.
        
        Args:
            frames_directory: Path to the frames directory to clean up
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            frames_dir = Path(frames_directory)
            
            if not frames_dir.exists():
                logger.warning(f"Frames directory does not exist: {frames_directory}")
                return True  # Consider it successful if directory is already gone
            
            # Count files before deletion for logging
            frame_files = list(frames_dir.glob('*.png'))
            file_count = len(frame_files)
            
            # Delete all frame files
            for frame_file in frame_files:
                try:
                    frame_file.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete frame file {frame_file}: {e}")
            
            # Delete the directory
            try:
                frames_dir.rmdir()  # rmdir only works if directory is empty
                logger.info(f"Successfully cleaned up frames directory: {frames_directory} "
                           f"(deleted {file_count} frame files)")
                return True
            except OSError as e:
                # If directory is not empty, force delete
                try:
                    shutil.rmtree(frames_dir)
                    logger.info(f"Force cleaned up frames directory: {frames_directory} "
                               f"(deleted {file_count} frame files)")
                    return True
                except Exception as e:
                    logger.error(f"Failed to force delete directory {frames_directory}: {e}")
                    return False
            
        except Exception as e:
            logger.error(f"Error during frames directory cleanup: {e}")
            return False
    
    def _auto_calibrate_with_first_frames(self, frame_files: List[Tuple[str, float]], user_id: str) -> Dict:
        """
        Auto-calibrate using frames from the first 10 seconds of the session.
        
        Args:
            frame_files: List of (frame_path, timestamp) tuples sorted by timestamp
            user_id: User identifier
            
        Returns:
            Calibration result with reference angle and metrics
        """
        try:
            if not frame_files:
                return {
                    "success": False,
                    "error": "No frames available for calibration",
                    "reference_angle": None,
                    "reference_magnitude": None
                }
            
            # Find frames from first 10 seconds
            first_timestamp = frame_files[0][1]
            ten_seconds_cutoff = first_timestamp + 10.0
            
            calibration_frames = [
                (frame_path, timestamp) for frame_path, timestamp in frame_files 
                if timestamp <= ten_seconds_cutoff
            ]
            
            if not calibration_frames:
                return {
                    "success": False,
                    "error": "No frames found in first 10 seconds",
                    "reference_angle": None,
                    "reference_magnitude": None
                }
            
            logger.info(f"Auto-calibrating using {len(calibration_frames)} frames from first 10 seconds")
            
            # Extract face metrics from calibration frames
            calibration_angles = []
            calibration_magnitudes = []
            valid_frames = 0
            
            for frame_path, timestamp in calibration_frames:
                face_metrics = self._extract_face_metrics_from_file(frame_path)
                if face_metrics:
                    calibration_angles.append(face_metrics["angle"])
                    calibration_magnitudes.append(face_metrics["magnitude"])
                    valid_frames += 1
                    
                    # Use first valid frame for initial reference
                    if len(calibration_angles) == 1:
                        initial_reference_angle = face_metrics["angle"]
                        initial_reference_magnitude = face_metrics["magnitude"]
            
            if not calibration_angles:
                return {
                    "success": False,
                    "error": "No valid face detections in first 10 seconds",
                    "reference_angle": None,
                    "reference_magnitude": None
                }
            
            # Calculate reference angle as median of calibration angles (more robust to outliers)
            calibration_angles.sort()
            calibration_magnitudes.sort()
            
            median_angle = calibration_angles[len(calibration_angles) // 2]
            median_magnitude = calibration_magnitudes[len(calibration_magnitudes) // 2]
            
            # Use first frame as primary reference but median for stability
            reference_angle = initial_reference_angle if valid_frames == 1 else median_angle
            reference_magnitude = initial_reference_magnitude if valid_frames == 1 else median_magnitude
            
            logger.info(f"Auto-calibration successful: reference_angle={reference_angle:.2f}°, "
                       f"reference_magnitude={reference_magnitude:.2f}, valid_frames={valid_frames}")
            
            return {
                "success": True,
                "reference_angle": reference_angle,
                "reference_magnitude": reference_magnitude,
                "calibration_frames_used": valid_frames,
                "calibration_method": "auto_first_10_seconds"
            }
            
        except Exception as e:
            logger.error(f"Error during auto-calibration: {e}")
            return {
                "success": False,
                "error": str(e),
                "reference_angle": None,
                "reference_magnitude": None
            }
    
    def process_session_frames(
        self, 
        user_id: str, 
        session_id: str,
        frames_directory: str,
        session_start: datetime,
        ground_frame_calibrated: bool = False,  # Kept for compatibility but not used
        reference_angle: Optional[float] = None  # Kept for compatibility but not used
    ) -> Dict:
        """
        Process all frames in a session directory in timestamp order.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            frames_directory: Directory containing session frames
            session_start: Session start time
            ground_frame_calibrated: Whether ground frame calibration is available (ignored, auto-calibration used)
            reference_angle: Reference angle from ground frame calibration (ignored, auto-calibration used)
            
        Returns:
            Complete session processing results
        """
        try:
            # Get sorted frame files
            frame_files = self._get_sorted_frame_files(frames_directory)
            
            if not frame_files:
                raise ValueError(f"No valid frame files found in {frames_directory}")
            
            # Auto-calibrate using first 10 seconds of frames
            logger.info("Starting auto-calibration using first 10 seconds of frames")
            calibration_result = self._auto_calibrate_with_first_frames(frame_files, user_id)
            
            if not calibration_result["success"]:
                logger.warning(f"Auto-calibration failed: {calibration_result['error']}")
                # Continue without calibration - will use baseline angle only
                reference_angle = None
                reference_magnitude = None
                ground_frame_calibrated = False
            else:
                reference_angle = calibration_result["reference_angle"]
                reference_magnitude = calibration_result["reference_magnitude"]
                ground_frame_calibrated = True
                logger.info(f"Auto-calibration completed successfully")
            
            # Initialize session data
            session_data = {
                "user_id": user_id,
                "session_id": session_id,
                "session_start": session_start.isoformat(),
                "baseline_angle": 0.0,
                "focus_buffer": [],
                "total_frames": 0,
                "focused_frames": 0,
                "distracted_frames": 0,
                "away_frames": 0,
                "current_state": "AWAY",
                "distraction_start": None,
                "frame_timestamps": [],
                "ground_frame_calibrated": ground_frame_calibrated,
                "reference_angle": reference_angle,
                "reference_magnitude": reference_magnitude,
                "gaze_deviations": [],
                "gaze_consistency_buffer": [],
                "interruptions": [],
                "focus_streaks": [],
                "current_focus_streak_start": None,
                "session_states": [],
                "processing_start": datetime.now().isoformat(),
                "calibration_result": calibration_result  # Store calibration info
            }
            
            logger.info(f"Starting batch processing for {len(frame_files)} frames")
            
            # Process each frame
            for i, (frame_path, frame_timestamp) in enumerate(frame_files):
                try:
                    # Extract face metrics
                    face_metrics = self._extract_face_metrics_from_file(frame_path)
                    
                    # Update session data
                    self._update_session_with_frame(session_data, face_metrics, frame_timestamp)
                    
                    # Log progress every 100 frames
                    if (i + 1) % 100 == 0:
                        logger.info(f"Processed {i + 1}/{len(frame_files)} frames")
                    
                except Exception as e:
                    logger.error(f"Error processing frame {frame_path}: {e}")
                    # Continue processing other frames
                    continue
            
            # Calculate final metrics
            session_data["session_end"] = datetime.now().isoformat()
            session_data["processing_end"] = datetime.now().isoformat()
            
            # Calculate final focus score
            focus_score = self._calculate_final_focus_score(session_data)
            session_data["focus_score"] = focus_score
            
            # Classify productivity
            productivity_level = self._classify_productivity(focus_score)
            session_data["productivity_level"] = productivity_level.value
            
            # Calculate session duration
            if frame_files:
                first_timestamp = frame_files[0][1]
                last_timestamp = frame_files[-1][1]
                session_duration = last_timestamp - first_timestamp
                session_data["session_duration_seconds"] = session_duration
            else:
                session_data["session_duration_seconds"] = 0.0
            
            # Calculate ground frame metrics
            if session_data.get("ground_frame_calibrated") and session_data.get("gaze_deviations"):
                session_data["gaze_consistency_score"] = (
                    sum(session_data["gaze_consistency_buffer"]) / len(session_data["gaze_consistency_buffer"])
                    if session_data["gaze_consistency_buffer"] else None
                )
                session_data["average_gaze_deviation"] = (
                    sum(session_data["gaze_deviations"]) / len(session_data["gaze_deviations"])
                    if session_data["gaze_deviations"] else None
                )
            
            # Generate comprehensive analytics
            try:
                comprehensive_analytics = analytics_service.generate_comprehensive_session_report(
                    user_id=user_id,
                    session_data=session_data,
                    historical_sessions=[],
                    all_users_data=[]
                )
                session_data["comprehensive_analytics"] = comprehensive_analytics
            except Exception as e:
                logger.error(f"Error generating comprehensive analytics: {e}")
                session_data["comprehensive_analytics"] = None
            
            # Clean up frames directory after processing
            logger.info("Starting cleanup of frames directory")
            cleanup_success = self._cleanup_frames_directory(frames_directory)
            
            if cleanup_success:
                session_data["frames_cleanup_successful"] = True
                session_data["frames_cleanup_status"] = "completed"
                logger.info(f"Frames directory cleanup completed successfully")
            else:
                session_data["frames_cleanup_successful"] = False
                session_data["frames_cleanup_status"] = "failed"
                logger.warning(f"Frames directory cleanup failed - directory may need manual cleanup")
            
            logger.info(f"Batch processing completed for session {session_id}")
            
            return session_data
            
        except Exception as e:
            logger.error(f"Batch processing failed for session {session_id}: {e}")
            # Attempt cleanup even if processing failed
            try:
                self._cleanup_frames_directory(frames_directory)
                logger.info(f"Cleanup attempted after processing failure")
            except Exception as cleanup_error:
                logger.error(f"Cleanup failed after processing error: {cleanup_error}")
            raise
    
    def _update_session_with_frame(self, session_data: Dict, face_metrics: Optional[Dict], frame_timestamp: float):
        """Update session data with a single frame."""
        session_data["total_frames"] += 1
        current_time = datetime.fromtimestamp(frame_timestamp)
        
        # Track detailed state changes with timestamps
        previous_state = session_data.get("current_state", "AWAY")
        
        # Process face metrics
        if face_metrics is None:
            session_data["current_state"] = "AWAY"
            session_data["away_frames"] += 1
            session_data["distraction_start"] = None
        else:
            current_angle = face_metrics["angle"]
            
            # Calculate gaze consistency if ground frame is calibrated
            gaze_metrics = self._calculate_gaze_consistency(session_data, current_angle)
            
            # Update baseline with WMA using config alpha
            session_data["baseline_angle"] = (
                config.BASELINE_ALPHA * current_angle + 
                (1 - config.BASELINE_ALPHA) * session_data["baseline_angle"]
            )
            
            # Calculate angle difference
            angle_diff = abs(current_angle - session_data["baseline_angle"])
            
            # Determine focus state using config parameters
            now = datetime.now()
            if angle_diff < config.FOCUSED_ANGLE_THRESHOLD:
                session_data["current_state"] = "FOCUSED"
                session_data["focused_frames"] += 1
                session_data["distraction_start"] = None
            elif angle_diff > config.DISTRACTED_ANGLE_THRESHOLD:
                if session_data["distraction_start"] is None:
                    session_data["distraction_start"] = now
                
                elapsed = (now - session_data["distraction_start"]).total_seconds()
                if elapsed >= config.DISTRACTION_CONFIRMATION_TIME:
                    session_data["current_state"] = "DISTRACTED"
                    session_data["distracted_frames"] += 1
                else:
                    # Grace period: not yet confirmed as distracted
                    session_data["current_state"] = "FOCUSED"
                    session_data["focused_frames"] += 1
                    session_data["distraction_start"] = None
            else:
                # Angle between thresholds, consider as FOCUSED
                session_data["current_state"] = "FOCUSED"
                session_data["focused_frames"] += 1
                session_data["distraction_start"] = None
        
        # Track state changes for enhanced analytics
        if previous_state != session_data["current_state"]:
            state_change = {
                "timestamp": current_time.isoformat(),
                "from_state": previous_state,
                "to_state": session_data["current_state"],
                "frame_number": session_data["total_frames"]
            }
            session_data["session_states"].append(state_change)
            
            # Track focus streaks
            if session_data["current_state"] == "FOCUSED":
                if previous_state != "FOCUSED":
                    session_data["current_focus_streak_start"] = current_time
            else:
                if session_data["current_focus_streak_start"] is not None:
                    streak_duration = (current_time - session_data["current_focus_streak_start"]).total_seconds()
                    session_data["focus_streaks"].append({
                        "start_time": session_data["current_focus_streak_start"].isoformat(),
                        "end_time": current_time.isoformat(),
                        "duration_seconds": streak_duration
                    })
                    session_data["current_focus_streak_start"] = None
            
            # Track interruptions (transitions from FOCUSED to DISTRACTED/AWAY)
            if previous_state == "FOCUSED" and session_data["current_state"] in ["DISTRACTED", "AWAY"]:
                session_data["interruptions"].append({
                    "timestamp": current_time.isoformat(),
                    "from_state": previous_state,
                    "to_state": session_data["current_state"],
                    "frame_number": session_data["total_frames"]
                })
        
        # Update focus buffer using config size
        session_data["focus_buffer"].append(session_data["current_state"])
        if len(session_data["focus_buffer"]) > config.FOCUS_BUFFER_SIZE:
            session_data["focus_buffer"].pop(0)
    
    def _calculate_final_focus_score(self, session_data: Dict) -> float:
        """Calculate final focus score with realistic variation and inconsistency penalties."""
        if session_data["focus_buffer"]:
            focused_count = sum(1 for state in session_data["focus_buffer"] if state == "FOCUSED")
            base_focus_score = (focused_count / len(session_data["focus_buffer"])) * 100
            
            # Calculate inconsistency penalty
            inconsistency_penalty = self._calculate_inconsistency_penalty(session_data["focus_buffer"])
            
            # Apply penalty to base score
            base_focus_score = max(0, base_focus_score - inconsistency_penalty)
            
            # Add realistic variation using config thresholds
            if base_focus_score > config.MAX_REALISTIC_FOCUS_SCORE:
                # Cap at max realistic score with diminishing returns
                focus_score = config.MAX_REALISTIC_FOCUS_SCORE + (base_focus_score - config.MAX_REALISTIC_FOCUS_SCORE) * 0.3
            elif base_focus_score > config.HIGH_FOCUS_THRESHOLD:
                # High focus range with small variation
                focus_score = base_focus_score - (config.MAX_REALISTIC_FOCUS_SCORE - base_focus_score) * 0.1
            else:
                # Normal calculation with small randomization
                import random
                focus_score = max(0, base_focus_score + random.uniform(-2, 2))
            
            focus_score = round(focus_score, 1)
        else:
            focus_score = 0.0
        
        return focus_score


# Global batch processor instance
batch_processor = BatchFocusProcessor()
