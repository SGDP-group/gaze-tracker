from typing import Tuple, Union
import math
import cv2
import numpy as np

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


def visualize(
    image,
    detection_result
) -> np.ndarray:
  """Draws bounding boxes and keypoints on the input image and return it.
  Args:
    image: The input RGB image.
    detection_result: The list of all "Detection" entities to be visualize.
  Returns:
    Image with bounding boxes.
  """
  annotated_image = image.copy()
  height, width, _ = image.shape

  for detection in detection_result.detections:
    # Draw bounding_box
    bbox = detection.bounding_box
    start_point = bbox.origin_x, bbox.origin_y
    end_point = bbox.origin_x + bbox.width, bbox.origin_y + bbox.height
    cv2.rectangle(annotated_image, start_point, end_point, TEXT_COLOR, 3)

    # Draw keypoints
    keypoints_px = []
    for i, keypoint in enumerate(detection.keypoints):
      keypoint_px = _normalized_to_pixel_coordinates(keypoint.x, keypoint.y,
                                                     width, height)
      keypoints_px.append(keypoint_px)

      color, thickness, radius = (0, 255, 0), 2, 2
      cv2.circle(annotated_image, keypoint_px, thickness, color, radius)
      if keypoint_px:
        cv2.putText(annotated_image, KEYPOINT_NAMES[i], (keypoint_px[0] + 5, keypoint_px[1] - 5), cv2.FONT_HERSHEY_PLAIN, 0.5, (255, 255, 255), 1)

    # Draw tetrahedron: base is left_eye, right_eye, mouth_mid; top is nose_tip
    if len(keypoints_px) >= 5 and all(kp is not None for kp in keypoints_px[:5]):
      left_eye = keypoints_px[0]
      right_eye = keypoints_px[1]
      nose_tip = keypoints_px[2]
      mouth = keypoints_px[3]

      # Base triangle
      cv2.line(annotated_image, left_eye, right_eye, (255, 0, 0), 2)
      cv2.line(annotated_image, right_eye, mouth, (255, 0, 0), 2)
      cv2.line(annotated_image, mouth, left_eye, (255, 0, 0), 2)

      # Sides to top
      cv2.line(annotated_image, left_eye, nose_tip, (255, 0, 0), 2)
      cv2.line(annotated_image, right_eye, nose_tip, (255, 0, 0), 2)
      cv2.line(annotated_image, mouth, nose_tip, (255, 0, 0), 2)
      # Draw extended line from centroid of base to nose_tip
      centroid_x = round((left_eye[0] + right_eye[0] + mouth[0]) / 3)
      centroid_y = round((left_eye[1] + right_eye[1] + mouth[1]) / 3)
      # Lower centroid_y by 10% of the eye gap distance
      eye_gap = abs(right_eye[0] - left_eye[0])
      centroid_y += round(eye_gap * 0.2)
      centroid = (centroid_x, centroid_y)
      vector_x = nose_tip[0] - centroid[0]
      vector_y = nose_tip[1] - centroid[1]
      extended_x = nose_tip[0] + vector_x
      extended_y = nose_tip[1] + vector_y
      cv2.line(annotated_image, centroid, (extended_x, extended_y), (0, 255, 255), 3)

      # Calculate and display face direction angle
      angle = math.degrees(math.atan2(vector_y, vector_x))
      cv2.putText(annotated_image, f"Face Direction: {angle:.1f}°", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    category = detection.categories[0]
    category_name = category.category_name
    category_name = '' if category_name is None else category_name
    probability = round(category.score, 2)
    result_text = category_name + ' (' + str(probability) + ')'
    text_location = (MARGIN + bbox.origin_x,
                     MARGIN + ROW_SIZE + bbox.origin_y)
    cv2.putText(annotated_image, result_text, text_location, cv2.FONT_HERSHEY_PLAIN,
                FONT_SIZE, TEXT_COLOR, FONT_THICKNESS)

  return annotated_image