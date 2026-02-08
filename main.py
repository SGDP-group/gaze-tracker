import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from utils import (
    visualize, 
    compute_session_features, 
    SessionClassifier, 
    generate_focus_heatmap
)
import time
from collections import deque
import json
import uuid
import os
from datetime import datetime

# Import API client
try:
    from src.services.api_client import FocusTrackerAPIClient, collect_user_feedback_interactive
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    print("Warning: API client not available. Running in standalone mode.")


class FocusState:
    """Tri-State Focus Classifier with temporal tracking."""
    FOCUSED = "FOCUSED"
    DISTRACTED = "DISTRACTED"
    AWAY = "AWAY"


class FocusTracker:
    """
    Manages focus state with:
    - Weighted Moving Average for baseline calibration (alpha=0.05)
    - Tri-state classification (Focused/Distracted/Away)
    - 2-second distraction confirmation timer
    """
    
    def __init__(self, alpha: float = 0.05, focus_threshold: float = 20.0, 
                 distraction_threshold: float = 30.0, distraction_duration: float = 2.0):
        self.alpha = alpha
        self.focus_threshold = focus_threshold
        self.distraction_threshold = distraction_threshold
        self.distraction_duration = distraction_duration
        
        self.baseline_angle = None
        self.current_state = FocusState.AWAY
        self.distraction_start_time = None
        self.focus_score = 0.0
        
        # Session statistics
        self.focused_frames = 0
        self.distracted_frames = 0
        self.away_frames = 0
        self.total_frames = 0
    
    def update(self, metrics: dict) -> str:
        """
        Update focus state based on current frame metrics.
        
        Args:
            metrics: Dictionary with 'angle', 'centroid', 'magnitude', 'eye_gap'
                    or None if no face detected
        
        Returns:
            Current focus state string
        """
        self.total_frames += 1
        current_time = time.time()
        
        if metrics is None:
            self.current_state = FocusState.AWAY
            self.distraction_start_time = None
            self.away_frames += 1
            return self.current_state
        
        current_angle = metrics['angle']
        
        # Dynamic Calibration: Weighted Moving Average
        if self.baseline_angle is None:
            self.baseline_angle = current_angle
        else:
            self.baseline_angle = (self.alpha * current_angle) + ((1 - self.alpha) * self.baseline_angle)
        
        # Calculate deviation from baseline
        deviation = abs(current_angle - self.baseline_angle)
        
        # Tri-State Classification
        if deviation < self.focus_threshold:
            # Focused: deviation < 20°
            self.current_state = FocusState.FOCUSED
            self.distraction_start_time = None
            self.focused_frames += 1
            
        elif deviation > self.distraction_threshold:
            # Potential Distraction: deviation > 30°
            if self.distraction_start_time is None:
                self.distraction_start_time = current_time
            
            # Confirm distraction after 2 seconds
            if (current_time - self.distraction_start_time) >= self.distraction_duration:
                self.current_state = FocusState.DISTRACTED
                self.distracted_frames += 1
            else:
                # Still in grace period, maintain previous focused state
                if self.current_state != FocusState.DISTRACTED:
                    self.current_state = FocusState.FOCUSED
                    self.focused_frames += 1
                else:
                    self.distracted_frames += 1
        else:
            # Transition zone (20° - 30°): maintain current state
            if self.current_state == FocusState.FOCUSED:
                self.focused_frames += 1
            elif self.current_state == FocusState.DISTRACTED:
                self.distracted_frames += 1
            self.distraction_start_time = None
        
        # Calculate real-time focus score
        if self.total_frames > 0:
            self.focus_score = (self.focused_frames / self.total_frames) * 100
        
        return self.current_state
    
    def get_stats(self) -> dict:
        """Return session statistics."""
        return {
            "focused_frames": self.focused_frames,
            "distracted_frames": self.distracted_frames,
            "away_frames": self.away_frames,
            "total_frames": self.total_frames,
            "focus_score": self.focus_score,
            "baseline_angle": self.baseline_angle
        }


def draw_ui_overlay(image: np.ndarray, state: str, focus_score: float, 
                    baseline_angle: float, deviation: float = None) -> np.ndarray:
    """Draw focus status and score overlay on the frame."""
    
    # State colors
    state_colors = {
        FocusState.FOCUSED: (0, 255, 0),      # Green
        FocusState.DISTRACTED: (0, 0, 255),   # Red
        FocusState.AWAY: (255, 165, 0)        # Orange
    }
    color = state_colors.get(state, (255, 255, 255))
    
    # Draw semi-transparent background for UI
    overlay = image.copy()
    cv2.rectangle(overlay, (5, 65), (300, 160), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, image, 0.5, 0, image)
    
    # Status text
    cv2.putText(image, f"STATUS: {state}", (10, 90), 
                cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 2)
    
    # Focus score bar
    bar_width = 200
    bar_height = 20
    bar_x, bar_y = 10, 105
    
    # Background bar
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                  (50, 50, 50), -1)
    
    # Fill bar based on score
    fill_width = int((focus_score / 100) * bar_width)
    bar_color = (0, 255, 0) if focus_score >= 70 else (0, 255, 255) if focus_score >= 40 else (0, 0, 255)
    cv2.rectangle(image, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), 
                  bar_color, -1)
    
    # Score text
    cv2.putText(image, f"Focus: {focus_score:.1f}%", (bar_x + bar_width + 10, bar_y + 15), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Baseline angle
    if baseline_angle is not None:
        cv2.putText(image, f"Baseline: {baseline_angle:.1f}deg", (10, 150), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Instructions
    cv2.putText(image, "Press 'q' to quit and see results", (10, image.shape[0] - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    
    return image


def main():
    print("=" * 60)
    print("FOCUS MANAGEMENT SYSTEM")
    print("=" * 60)
    print("Initializing MediaPipe Face Detector...")
    
    # Initialize API client if available
    api_client = None
    if API_AVAILABLE:
        try:
            # Get user ID from environment or prompt
            user_id = os.getenv("FOCUS_USER_ID")
            if not user_id:
                user_id = input("Enter your user ID (or press Enter for default): ").strip()
                if not user_id:
                    user_id = f"user_{int(time.time())}"
            
            api_client = FocusTrackerAPIClient()
            
            # Create user if needed
            try:
                user_data = api_client.create_user_if_needed(user_id)
                print(f"✅ User authenticated: {user_data['user_id']}")
                print(f"   API Key: {user_data['api_key'][:20]}...")
                
                # Save credentials for future use
                os.environ["FOCUS_USER_ID"] = user_data['user_id']
                os.environ["FOCUS_API_KEY"] = user_data['api_key']
                
            except Exception as e:
                print(f"⚠️  API connection failed: {e}")
                print("   Running in standalone mode...")
                api_client = None
                
        except Exception as e:
            print(f"⚠️  Failed to initialize API client: {e}")
            api_client = None
    
    # Setup MediaPipe Face Detector
    base_options = python.BaseOptions(model_asset_path='detector.tflite')
    options = vision.FaceDetectorOptions(base_options=base_options)
    detector = vision.FaceDetector.create_from_options(options)
    
    # Initialize video capture
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
    
    # Get frame dimensions for display
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera resolution: {frame_width}x{frame_height}")
    
    # Initialize Focus Tracker with specified parameters
    tracker = FocusTracker(
        alpha=0.05,              # WMA smoothing factor
        focus_threshold=20.0,    # < 20° = Focused
        distraction_threshold=30.0,  # > 30° = Distracted
        distraction_duration=2.0     # 2 seconds to confirm distraction
    )
    
    # Session data collection for ML analysis
    session_data = []
    session_start_time = time.time()
    session_id = str(uuid.uuid4())
    
    print("Starting focus tracking session...")
    print("Press 'q' to quit and generate session report.\n")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Detect faces
        detection_result = detector.detect(image)
        
        # Visualize and extract metrics
        annotated_image, metrics = visualize(frame, detection_result)
        
        # Update focus state
        state = tracker.update(metrics)
        
        # Collect session data
        frame_data = {
            "timestamp": time.time() - session_start_time,
            "state": state,
            "metrics": metrics
        }
        session_data.append(frame_data)
        
        # Calculate deviation for display
        deviation = None
        if metrics and tracker.baseline_angle is not None:
            deviation = abs(metrics['angle'] - tracker.baseline_angle)
        
        # Draw UI overlay
        stats = tracker.get_stats()
        annotated_image = draw_ui_overlay(
            annotated_image, 
            state, 
            stats['focus_score'],
            stats['baseline_angle'],
            deviation
        )
        
        # Display frame
        cv2.imshow('Focus Management System', annotated_image)
        
        # Check for quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    
    # Session duration
    session_duration = time.time() - session_start_time
    
    print("\n" + "=" * 60)
    print("SESSION COMPLETE - GENERATING REPORT")
    print("=" * 60)
    
    # Get final statistics
    final_stats = tracker.get_stats()
    
    print(f"\n📊 SESSION STATISTICS:")
    print(f"   Duration: {session_duration:.1f} seconds")
    print(f"   Total Frames: {final_stats['total_frames']}")
    print(f"   Focused Frames: {final_stats['focused_frames']} ({final_stats['focused_frames']/max(1,final_stats['total_frames'])*100:.1f}%)")
    print(f"   Distracted Frames: {final_stats['distracted_frames']} ({final_stats['distracted_frames']/max(1,final_stats['total_frames'])*100:.1f}%)")
    print(f"   Away Frames: {final_stats['away_frames']} ({final_stats['away_frames']/max(1,final_stats['total_frames'])*100:.1f}%)")
    print(f"   Real-time Focus Score: {final_stats['focus_score']:.1f}%")
    
    # Compute session features for ML classification
    print(f"\n🔬 ML FEATURE EXTRACTION:")
    session_features = compute_session_features(session_data)
    print(f"   Angle Variance: {session_features['angle_variance']:.2f}°")
    print(f"   Stability Score: {session_features['stability_score']:.2%}")
    print(f"   Presence Ratio: {session_features['presence_ratio']:.2%}")
    print(f"   Context Switches: {session_features['context_switches']}")
    
    # Random Forest Classification
    print(f"\n🤖 RANDOM FOREST CLASSIFICATION:")
    classifier = SessionClassifier()
    prediction, confidence = classifier.predict(session_features)
    print(f"   Prediction: {prediction}")
    print(f"   Confidence: {confidence:.1%}")
    
    # Generate Focus Heatmap
    print(f"\n🗺️  GENERATING FOCUS HEATMAP...")
    heatmap_path = generate_focus_heatmap(session_data, "focus_heatmap.png")
    
    # API Integration: Send session data
    api_session_data = None
    if api_client:
        try:
            print(f"\n📤 SENDING SESSION DATA TO API...")
            
            # Prepare session data for API
            api_session_data = {
                "session_id": session_id,
                "start_time": datetime.fromtimestamp(session_start_time).isoformat(),
                "end_time": datetime.fromtimestamp(time.time()).isoformat(),
                "duration_seconds": session_duration,
                "total_frames": final_stats['total_frames'],
                "focused_frames": final_stats['focused_frames'],
                "distracted_frames": final_stats['distracted_frames'],
                "away_frames": final_stats['away_frames'],
                "focus_score": final_stats['focus_score'],
                "baseline_angle": final_stats['baseline_angle'],
                "raw_session_data": json.dumps(session_data),
                "angle_variance": session_features['angle_variance'],
                "stability_score": session_features['stability_score'],
                "presence_ratio": session_features['presence_ratio'],
                "context_switches": session_features['context_switches'],
                "base_prediction": prediction,
                "base_confidence": confidence
            }
            
            # Send to API
            session_response = api_client.send_session_data(api_session_data)
            print(f"   ✅ Session data sent successfully")
            print(f"   Session ID: {session_response['session_id']}")
            
        except Exception as e:
            print(f"   ❌ Failed to send session data: {e}")
            api_client = None
    
    # Collect user feedback if API is available
    if api_client and API_AVAILABLE:
        try:
            print(f"\n💬 COLLECTING USER FEEDBACK...")
            feedback_data = collect_user_feedback_interactive(session_id)
            
            # Send feedback to API
            feedback_response = api_client.send_feedback(session_id, feedback_data)
            print(f"   ✅ Feedback sent successfully")
            print(f"   Feedback ID: {feedback_response['id']}")
            
        except Exception as e:
            print(f"   ❌ Failed to send feedback: {e}")
    
    # API Integration: Get personalized insights
    if api_client:
        try:
            print(f"\n🎯 GETTING PERSONALIZED INSIGHTS...")
            
            # Get user statistics
            user_stats = api_client.get_statistics()
            print(f"   Total Sessions: {user_stats['total_sessions']}")
            print(f"   Total Duration: {user_stats['total_duration_hours']} hours")
            print(f"   Average Focus Score: {user_stats['average_focus_score']}%")
            print(f"   Most Productive Time: {user_stats['most_productive_time'] or 'N/A'}")
            print(f"   Productivity Trend: {user_stats['productivity_trend']}")
            
            # Get recommendations
            recommendations = api_client.get_recommendations()
            if recommendations:
                rec = recommendations[0]  # Get primary recommendation
                print(f"\n📅 RECOMMENDATION:")
                print(f"   Best Time: {rec['recommended_time_of_day']}")
                print(f"   Duration: {rec['recommended_duration_minutes']} minutes")
                print(f"   Confidence: {rec['confidence_score']:.1%}")
                print(f"   Reasoning: {rec['reasoning']}")
            
            # Train model if enough data
            if user_stats['total_sessions'] >= 3:
                print(f"\n🤖 TRAINING PERSONALIZED MODEL...")
                training_result = api_client.train_model()
                print(f"   Model Version: {training_result['model_version']}")
                print(f"   Training Accuracy: {training_result['training_accuracy']:.1%}")
                print(f"   Message: {training_result['message']}")
            
        except Exception as e:
            print(f"   ❌ Failed to get personalized insights: {e}")
    
    print("\n" + "=" * 60)
    print("Session analysis complete!")
    if api_client:
        print("✅ Data synced with Focus Management System")
    else:
        print("⚠️  Running in standalone mode - no API sync")
    print("=" * 60)


if __name__ == "__main__":
    main()


