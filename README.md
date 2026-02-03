# Gaze Tracker

A real-time face detection application using MediaPipe and OpenCV.

## Description

This project detects faces in real-time using a webcam feed. It utilizes MediaPipe's face detection models to identify and visualize faces in the video stream.

## Requirements

- Python 3.12 or higher
- Webcam

## Installation

1. **Install dependencies:**
   ```powershell
   python -m pip install mediapipe opencv-python
   ```

   Or with specific versions:
   ```powershell
   python -m pip install mediapipe>=0.10.31 opencv-python>=4.12.0.88
   ```

2. **Verify installation:**
   ```powershell
   python -c "import mediapipe; import cv2; print('All dependencies installed successfully')"
   ```

## Project Structure

```
gaze-tracker/
├── main.py                    # Main application entry point
├── utils.py                   # Utility functions for visualization
├── detector.tflite           # TensorFlow Lite face detection model
├── face_landmarker.task      # MediaPipe face landmark detection model
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Usage

Run the face detection application:

```powershell
python main.py
```

### Controls

- **Press 'q'** to exit the application

The application will:
1. Access your webcam
2. Display a video feed with detected faces highlighted
3. Run in real-time until you press 'q'

## How It Works

1. Captures frames from your webcam using OpenCV
2. Converts frames from BGR to RGB format for MediaPipe
3. Uses the face detection model (`detector.tflite`) to detect faces
4. Visualizes the detected faces on the video feed
5. Displays the annotated feed in a window

## Troubleshooting

- **"python is not recognized"**: Make sure Python is installed and added to your system PATH
- **"No module named mediapipe"**: Run the installation command above
- **Black screen or no camera feed**: Check that your webcam is connected and not being used by another application
- **"pip is not recognized"**: Use `python -m pip` instead

## Requirements File

The project dependencies are specified in `pyproject.toml`:
- `mediapipe>=0.10.31` - Face detection and landmark models
- `opencv-python>=4.12.0.88` - Video capture and image processing
