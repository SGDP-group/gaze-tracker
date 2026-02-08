from typing import Tuple, Union, List, Dict, Optional
import math
import cv2
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt

MARGIN = 10  # pixels
ROW_SIZE = 10  # pixels
FONT_SIZE = 1
FONT_THICKNESS = 1
TEXT_COLOR = (255, 0, 0)  # red

# Keypoint mapping: index to name
KEYPOINT_NAMES = {
    0: "right_eye",
    1: "left_eye",
    2: "nose_tip",
    3: "mouth",
    4: "right_ear",
    5: "left_ear",
}


def _normalized_to_pixel_coordinates(
    normalized_x: float, normalized_y: float, image_width: int,
    image_height: int) -> Union[None, Tuple[int, int]]:
  """Converts normalized value pair to pixel coordinates."""

  # Checks if the float value is between 0 and 1.
  def is_valid_normalized_value(value: float) -> bool:
    return (value > 0 or math.isclose(0, value)) and (value < 1 or
                                                      math.isclose(1, value))

  if not (is_valid_normalized_value(normalized_x) and
          is_valid_normalized_value(normalized_y)):
    # TODO: Draw coordinates even if it's outside of the image bounds.
    return None
  x_px = min(math.floor(normalized_x * image_width), image_width - 1)
  y_px = min(math.floor(normalized_y * image_height), image_height - 1)
  return x_px, y_px


def extract_face_metrics(detection_result, image_width: int, image_height: int) -> Optional[Dict]:
    """
    Extract face metrics from MediaPipe detection result.
    
    Returns a dictionary containing:
    - centroid: (x, y) tuple representing face center with 20% vertical offset
    - angle: Yaw angle in degrees (direction of focus vector)
    - magnitude: Length of focus vector (vertical/pitch deviation)
    - eye_gap: Pixel distance between eyes (depth proxy)
    - nose_tip: (x, y) tuple of nose tip position
    """
    if not detection_result.detections:
        return None
    
    detection = detection_result.detections[0]
    keypoints_px = []
    
    for keypoint in detection.keypoints:
        kp_px = _normalized_to_pixel_coordinates(
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
        "nose_tip": nose_tip,
        "vx": vx,
        "vy": vy
    }


def visualize(image, detection_result) -> Tuple[np.ndarray, Optional[Dict]]:
    """
    Visualize face detection with focus vector overlay.
    Returns annotated image and face_metrics dictionary.
    """
    annotated_image = image.copy()
    height, width, _ = image.shape
    
    face_metrics = extract_face_metrics(detection_result, width, height)
    
    if face_metrics:
        centroid = face_metrics["centroid"]
        nose_tip = face_metrics["nose_tip"]
        vx, vy = face_metrics["vx"], face_metrics["vy"]
        angle = face_metrics["angle"]
        
        # Draw focus vector (extended)
        end_point = (nose_tip[0] + vx, nose_tip[1] + vy)
        cv2.line(annotated_image, centroid, end_point, (0, 255, 255), 3)
        
        # Draw centroid
        cv2.circle(annotated_image, centroid, 5, (255, 0, 255), -1)
        
        # Draw nose tip
        cv2.circle(annotated_image, nose_tip, 4, (0, 255, 0), -1)
        
        # Display angle
        cv2.putText(
            annotated_image, 
            f"Yaw: {angle:.1f}deg", 
            (10, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            (0, 255, 0), 
            2
        )
        
        # Display eye gap (depth indicator)
        cv2.putText(
            annotated_image,
            f"Depth: {face_metrics['eye_gap']:.0f}px",
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2
        )
    
    return annotated_image, face_metrics


def compute_session_features(session_data: List[Dict]) -> Dict:
    """
    Compute session-level features for ML classification.
    
    Features:
    - angle_variance: Standard deviation of head yaw
    - stability_score: Ratio of frames where head motion was < 5 pixels
    - presence_ratio: Time face was visible vs session duration
    - context_switches: Frequency of transitions between Focused and Distracted
    """
    if not session_data:
        return {
            "angle_variance": 0.0,
            "stability_score": 0.0,
            "presence_ratio": 0.0,
            "context_switches": 0
        }
    
    total_frames = len(session_data)
    
    # Extract angles and centroids from frames with valid metrics
    angles = []
    centroids = []
    states = []
    
    for frame_data in session_data:
        states.append(frame_data.get("state", "AWAY"))
        metrics = frame_data.get("metrics")
        if metrics:
            angles.append(metrics["angle"])
            centroids.append(metrics["centroid"])
    
    # Angle Variance
    angle_variance = float(np.std(angles)) if len(angles) > 1 else 0.0
    
    # Stability Score: ratio of frames with < 5 pixel motion
    stable_frames = 0
    if len(centroids) > 1:
        for i in range(1, len(centroids)):
            dx = centroids[i][0] - centroids[i-1][0]
            dy = centroids[i][1] - centroids[i-1][1]
            motion = math.sqrt(dx**2 + dy**2)
            if motion < 5:
                stable_frames += 1
        stability_score = stable_frames / (len(centroids) - 1)
    else:
        stability_score = 1.0 if len(centroids) == 1 else 0.0
    
    # Presence Ratio
    presence_ratio = len(angles) / total_frames if total_frames > 0 else 0.0
    
    # Context Switches: transitions between FOCUSED and DISTRACTED
    context_switches = 0
    prev_state = None
    for state in states:
        if state in ["FOCUSED", "DISTRACTED"]:
            if prev_state and prev_state != state and prev_state in ["FOCUSED", "DISTRACTED"]:
                context_switches += 1
            prev_state = state
    
    return {
        "angle_variance": angle_variance,
        "stability_score": stability_score,
        "presence_ratio": presence_ratio,
        "context_switches": context_switches
    }


class SessionClassifier:
    """
    Random Forest Classifier for session-level productivity analysis.
    Classifies sessions as "Productive" or "Unproductive/Fragmented".
    """
    
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        self._is_trained = False
        self._generate_training_data()
    
    def _generate_training_data(self):
        """Generate synthetic training data for the classifier."""
        np.random.seed(42)
        
        # Productive sessions: low variance, high stability, high presence, few switches
        productive_samples = []
        for _ in range(100):
            productive_samples.append([
                np.random.uniform(5, 20),    # angle_variance
                np.random.uniform(0.7, 1.0), # stability_score
                np.random.uniform(0.8, 1.0), # presence_ratio
                np.random.randint(0, 5)      # context_switches
            ])
        
        # Unproductive sessions: high variance, low stability, variable presence, many switches
        unproductive_samples = []
        for _ in range(100):
            unproductive_samples.append([
                np.random.uniform(25, 60),   # angle_variance
                np.random.uniform(0.2, 0.6), # stability_score
                np.random.uniform(0.4, 0.8), # presence_ratio
                np.random.randint(8, 25)     # context_switches
            ])
        
        X = np.array(productive_samples + unproductive_samples)
        y = np.array([1] * 100 + [0] * 100)  # 1 = Productive, 0 = Unproductive
        
        self.model.fit(X, y)
        self._is_trained = True
    
    def predict(self, session_features: Dict) -> Tuple[str, float]:
        """
        Predict session productivity.
        
        Returns:
        - label: "Productive Session" or "Unproductive/Fragmented Session"
        - confidence: Probability of the prediction
        """
        if not self._is_trained:
            return "Unknown", 0.0
        
        features = np.array([[
            session_features["angle_variance"],
            session_features["stability_score"],
            session_features["presence_ratio"],
            session_features["context_switches"]
        ]])
        
        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]
        confidence = max(probabilities)
        
        label = "Productive Session" if prediction == 1 else "Unproductive/Fragmented Session"
        return label, confidence


def generate_focus_heatmap(session_data: List[Dict], output_path: str = "focus_heatmap.png"):
    """
    Generate a 2D Density Heatmap using matplotlib.hexbin.
    
    X-Axis: Yaw Angle (Horizontal deviation)
    Y-Axis: Vector Magnitude (Vertical/Pitch deviation)
    
    Provides a "Visual Focus Map" showing where the head was pointed during the session.
    """
    angles = []
    magnitudes = []
    
    for frame_data in session_data:
        metrics = frame_data.get("metrics")
        if metrics:
            angles.append(metrics["angle"])
            magnitudes.append(metrics["magnitude"])
    
    if len(angles) < 2:
        print("Not enough data points to generate heatmap.")
        return None
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Create hexbin heatmap
    hb = ax.hexbin(
        angles, 
        magnitudes, 
        gridsize=30, 
        cmap='YlOrRd',
        mincnt=1
    )
    
    ax.set_xlabel('Yaw Angle (degrees)', fontsize=12)
    ax.set_ylabel('Vector Magnitude (pixels)', fontsize=12)
    ax.set_title('Focus Heatmap - Visual Focus Map', fontsize=14, fontweight='bold')
    
    # Add colorbar
    cb = fig.colorbar(hb, ax=ax)
    cb.set_label('Frame Count', fontsize=10)
    
    # Add mean marker
    mean_angle = np.mean(angles)
    mean_magnitude = np.mean(magnitudes)
    ax.scatter(
        [mean_angle], 
        [mean_magnitude], 
        color='blue', 
        s=100, 
        marker='x', 
        linewidths=3,
        label=f'Mean ({mean_angle:.1f}°, {mean_magnitude:.1f}px)'
    )
    ax.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    
    print(f"Focus heatmap saved to: {output_path}")
    return output_path