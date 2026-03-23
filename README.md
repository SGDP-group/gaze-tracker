# Focus Management System

A comprehensive focus tracking and productivity analysis system using computer vision, machine learning, and personalized recommendations.

## Features

### 🎯 Real-Time Focus Tracking
- **MediaPipe Face Detection** for accurate head pose tracking
- **Tri-State Classification**: Focused, Distracted, Away
- **Dynamic Calibration** with Weighted Moving Average (α = 0.05)
- **2-Second Distraction Confirmation** to avoid false positives

### 🤖 Personalized Machine Learning
- **Progressive Learning** with user feedback
- **Random Forest Classifier** for session productivity prediction
- **Transfer Learning** from base model to user-specific models
- **Feature Extraction**: Angle variance, stability score, presence ratio, context switches

### 📊 Session Analytics
- **Real-time Focus Score** visualization
- **2D Density Heatmap** using matplotlib.hexbin
- **Session Statistics** and productivity trends
- **Context Switches** detection

### 🌐 API Integration
- **FastAPI Backend** with SQLite database
- **RESTful Endpoints** for sessions, feedback, and recommendations
- **API Key Authentication** for secure access
- **Personalized Recommendations** based on historical patterns

### 🎯 Focus Tracking API (New!)
- **Server-Side Processing** with user separation
- **Multi-User Support** with isolated sessions
- **Frame Analysis Endpoint** for client applications
- **Real-Time Focus State** tracking via HTTP API
- **Session Management** with automatic cleanup

### 🖥️ Demo Clients (New!)
- **GUI Demo Client** (Python/Tkinter) with camera integration
- **Web Demo Client** (HTML/JavaScript) for browser testing
- **Command Line Client** for programmatic integration
- **Interactive Buttons** for all API endpoints
- **Real-Time Response** logging and status updates

## Project Structure

```
gaze_tracker/
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI application
│   │   ├── routes.py            # API endpoints
│   │   └── dependencies.py      # Authentication & database
│   ├── database/
│   │   ├── models.py            # SQLAlchemy models
│   │   └── database.py          # Database connection
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   └── services/
│       ├── auth.py              # Authentication service
│       ├── ml_service.py        # ML pipeline & recommendations
│       ├── api_client.py        # API client for main.py
│       ├── focus_service.py     # Focus tracking API service
│       ├── celery_app.py        # Celery configuration
│       └── tasks.py             # Async ML tasks
├── models/
│   ├── focus_schemas.py         # Focus API Pydantic models
│   └── schemas.py               # General API models
├── tests/
│   ├── test_api_pytest.py       # API endpoint tests
│   ├── test_focus_api.py        # Focus API tests
│   └── conftest.py              # Pytest configuration
├── examples/
│   ├── gui_demo_client.py       # Desktop GUI demo client
│   ├── web_demo_client.html     # Web-based demo client
│   ├── focus_client_example.py  # Command-line client
│   └── README_DEMO_CLIENTS.md   # Demo clients documentation
├── data/                        # SQLite database directory
├── main.py                      # Main focus tracking application
├── utils.py                     # Computer vision utilities
├── detector.tflite              # MediaPipe face detection model
├── docker-compose.yml           # Redis & Redis Commander
├── celery_worker.py             # Celery worker startup
├── pytest.ini                   # Pytest configuration
└── pyproject.toml               # Dependencies
```

## Installation

### Prerequisites
- Python 3.12+
- Webcam access
- UV package manager
- Redis server (for Celery async training)

### Setup

1. **Clone and install dependencies:**
```bash
cd gaze_tracker
uv sync
```

2. **Start Redis with Docker Compose:**
```bash
docker-compose up -d redis
```

3. **Verify MediaPipe model:**
```bash
ls detector.tflite  # Should exist in project root
```

## Usage

### 1. Start the API Server
For focus tracking API and personalized features:

```bash
uv run server.py
```

The API will be available at `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`
- **Focus API Health**: `http://localhost:8000/api/v1/focus/health`
- **Interactive Demo**: Open `examples/web_demo_client.html`

### 2. Start Celery Worker (for async training)

```bash
uv run celery -A src.services.celery_app worker --loglevel=info &
```

### 3. Test with Demo Clients

#### GUI Demo Client (Desktop)
```bash
python examples/gui_demo_client.py
```
Features:
- 🎯 Interactive buttons for all endpoints
- 📹 Real-time camera integration
- 📊 Live response logging
- ⚙️ Configurable API settings

#### Web Demo Client (Browser)
```bash
open examples/web_demo_client.html
```
Features:
- 🌐 Modern web interface
- 📱 Mobile-friendly design
- 📹 WebRTC camera support
- 🔄 Auto-send functionality

#### Command Line Client
```bash
python examples/focus_client_example.py
```
Features:
- 📹 Webcam demo
- 🖼️ Static image testing
- 👥 Multi-user demo
- 📊 Session management

### 4. Run Traditional Focus Tracking

```bash
uv run python main.py
```

**Features:**
- Real-time face detection and focus analysis
- Live focus score display
- Session data collection
- Interactive feedback collection
- Personalized recommendations (if API is running)

### 5. Test with Pytest

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m celery        # Celery tests only
uv run pytest -m slow          # Slow tests only

# Run focus API tests
uv run pytest tests/test_focus_api.py -v

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_api_pytest.py
```

```bash
uv run python tests/test_celery.py
```

This will:
- Create sample sessions with feedback
- Submit async training task to Celery
- Monitor training progress in real-time
- Check training history and status

## API Endpoints

### Focus Tracking API
#### `POST /api/v1/focus/analyze`
Analyze frame for focus tracking with real-time state detection.

**Request Body:**
```json
{
  "user_id": "string (required) - Unique user identifier",
  "frame_data": "string (required) - Base64 encoded image data",
  "image_width": "integer (required) - Image width in pixels",
  "image_height": "integer (required) - Image height in pixels"
}
```

**Response:**
```json
{
  "user_id": "string - User identifier",
  "current_state": "string - FOCUSED|DISTRACTED|AWAY",
  "focus_score": "number - 0-100% focus consistency",
  "baseline_angle": "number - Current baseline gaze angle in degrees",
  "average_fps": "number - Rolling average FPS",
  "face_metrics": {
    "centroid": {"x": "number", "y": "number"} - Face center coordinates",
    "angle": "number - Gaze angle in degrees",
    "magnitude": "number - Gaze vector magnitude",
    "eye_gap": "number - Distance between eyes in pixels",
    "confidence": "number - Face detection confidence 0-1",
    "timestamp": "string - ISO timestamp"
  },
  "session_stats": {
    "total_frames": "integer - Total frames processed",
    "focused_frames": "integer - Frames marked as focused",
    "distracted_frames": "integer - Frames marked as distracted",
    "away_frames": "integer - Frames with no face detected",
    "session_duration": "number - Session duration in seconds",
    "ground_frame_calibrated": "boolean - Whether ground frame is calibrated",
    "gaze_consistency_score": "number - 0-100% gaze consistency",
    "gaze_deviation": "number - Current deviation from reference angle",
    "is_consistent": "boolean - Whether gaze is within threshold"
  },
  "timestamp": "string - ISO timestamp"
}
```

#### `POST /api/v1/focus/session/start`
Start a new focus tracking session for a user.

**Request Body:**
```json
{
  "user_id": "string (required) - Unique user identifier",
  "session_name": "string (optional) - Descriptive session name"
}
```

**Response:**
```json
{
  "session_id": "string - Unique session identifier",
  "user_id": "string - User identifier",
  "session_name": "string - Session name",
  "status": "string - Session status",
  "timestamp": "string - ISO timestamp"
}
```

#### `POST /api/v1/focus/session/end?user_id={user_id}`
End a user's session and return final analytics.

**Query Parameters:**
- `user_id` (string, required) - User identifier

**Response:**
```json
{
  "user_id": "string - User identifier",
  "session_start": "string - Session start timestamp",
  "session_end": "string - Session end timestamp",
  "total_frames": "integer - Total frames processed",
  "focused_frames": "integer - Frames marked as focused",
  "distracted_frames": "integer - Frames marked as distracted",
  "away_frames": "integer - Frames with no face detected",
  "focus_score": "number - Final focus score 0-100%",
  "baseline_angle": "number - Final baseline angle",
  "average_fps": "number - Average FPS for session",
  "productivity_level": "string - HIGHLY_PRODUCTIVE|PRODUCTIVE|MODERATELY_PRODUCTIVE|NOT_PRODUCTIVE",
  "session_duration_seconds": "number - Total session duration",
  "ground_frame_calibrated": "boolean - Whether ground frame was calibrated",
  "reference_angle": "number - Reference gaze angle from ground frame",
  "gaze_consistency_score": "number - Average gaze consistency score",
  "average_gaze_deviation": "number - Average deviation from reference"
}
```

#### `GET /api/v1/focus/session/{user_id}`
Get current session data for an active user.

**Path Parameters:**
- `user_id` (string, required) - User identifier

**Response:** Same as session end response above

#### `POST /api/v1/focus/ground-frame/calibrate`
Calibrate ground frame for gaze direction reference.

**Request Body:**
```json
{
  "user_id": "string (required) - Unique user identifier",
  "frame_data": "string (required) - Base64 encoded image data for ground frame",
  "image_width": "integer (required) - Image width in pixels",
  "image_height": "integer (required) - Image height in pixels"
}
```

**Response:**
```json
{
  "success": "boolean - Calibration success status",
  "user_id": "string - User identifier",
  "reference_angle": "number - Reference gaze angle for calibration",
  "reference_magnitude": "number - Reference gaze magnitude",
  "confidence": "number - Face detection confidence",
  "message": "string - Calibration message",
  "timestamp": "string - ISO timestamp"
}
```

#### `GET /api/v1/focus/users/active`
List all currently active users.

**Response:**
```json
{
  "active_users": "array - List of active user IDs",
  "total_count": "integer - Number of active users",
  "timestamp": "string - ISO timestamp"
}
```

#### `POST /api/v1/focus/cleanup`
Clean up inactive sessions older than specified timeout.

**Request Body:**
```json
{
  "timeout_minutes": "integer (optional) - Inactivity timeout in minutes, default: 30"
}
```

**Response:**
```json
{
  "success": "boolean - Cleanup success status",
  "cleaned_users": "array - List of cleaned user IDs",
  "active_users": "array - Remaining active users",
  "timestamp": "string - ISO timestamp"
}
```

#### `GET /api/v1/focus/health`
Health check for focus tracking service.

**Response:**
```json
{
  "status": "string - Service status",
  "active_sessions": "integer - Number of active sessions",
  "timestamp": "string - ISO timestamp"
}
```

### Authentication Endpoints
#### `POST /api/v1/users`
Create a new user with API key for authenticated operations.

**Request Body:**
```json
{
  "user_id": "string (required) - Unique user identifier"
}
```

**Response:**
```json
{
  "user_id": "string - User identifier",
  "api_key": "string - Generated API key",
  "created_at": "string - ISO timestamp"
}
```

#### `GET /api/v1/users/me`
Get current authenticated user information.

**Headers:**
- `Authorization: Bearer {api_key}` (required) - API key for authentication

**Response:**
```json
{
  "user_id": "string - User identifier",
  "created_at": "string - Account creation timestamp",
  "session_count": "integer - Number of sessions"
}
```

### Session Management Endpoints
#### `POST /api/v1/sessions`
Create a new session record.

**Request Body:**
```json
{
  "user_id": "string (required) - User identifier",
  "session_name": "string (optional) - Session name",
  "start_time": "string (optional) - ISO timestamp, defaults to now"
}
```

**Response:**
```json
{
  "session_id": "string - Unique session identifier",
  "user_id": "string - User identifier",
  "session_name": "string - Session name",
  "start_time": "string - Start timestamp",
  "status": "string - Session status"
}
```

#### `GET /api/v1/sessions`
List sessions for authenticated user.

**Headers:**
- `Authorization: Bearer {api_key}` (required)

**Query Parameters:**
- `limit` (integer, optional) - Maximum number of sessions to return
- `offset` (integer, optional) - Number of sessions to skip

**Response:**
```json
{
  "sessions": "array - List of session objects",
  "total_count": "integer - Total number of sessions"
}
```

#### `GET /api/v1/sessions/{session_id}`
Get detailed session information.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Headers:**
- `Authorization: Bearer {api_key}` (required)

**Response:**
```json
{
  "session_id": "string - Session identifier",
  "user_id": "string - User identifier",
  "session_name": "string - Session name",
  "start_time": "string - Start timestamp",
  "end_time": "string - End timestamp",
  "duration_seconds": "number - Session duration",
  "focus_score": "number - Final focus score",
  "productivity_level": "string - Productivity classification"
}
```

### Feedback Endpoints
#### `POST /api/v1/feedback`
Submit feedback for a session.

**Request Body:**
```json
{
  "session_id": "string (required) - Session identifier",
  "productivity_rating": "integer (required) - 1-5 star rating",
  "feedback_text": "string (optional) - User feedback comments",
  "context": "string (optional) - Session context (work, study, etc.)"
}
```

**Response:**
```json
{
  "feedback_id": "string - Feedback identifier",
  "session_id": "string - Session identifier",
  "productivity_rating": "integer - Rating",
  "timestamp": "string - ISO timestamp"
}
```

### Machine Learning Endpoints
#### `POST /api/v1/models/train`
Train personalized model synchronously.

**Headers:**
- `Authorization: Bearer {api_key}` (required)

**Request Body:**
```json
{
  "user_id": "string (required) - User identifier",
  "training_config": {
    "model_type": "string (optional) - Model type, default: random_forest",
    "features": "array (optional) - Features to use",
    "test_size": "number (optional) - Test split ratio, default: 0.2"
  }
}
```

**Response:**
```json
{
  "success": "boolean - Training success status",
  "model_id": "string - Model identifier",
  "accuracy": "number - Model accuracy",
  "training_time": "number - Training time in seconds",
  "feature_importance": "object - Feature importance scores"
}
```

#### `POST /api/v1/models/train/async`
Train personalized model asynchronously.

**Headers:**
- `Authorization: Bearer {api_key}` (required)

**Request Body:**
```json
{
  "user_id": "string (required) - User identifier",
  "force_retrain": "boolean (optional) - Force retraining, default: false"
}
```

**Response:**
```json
{
  "task_id": "string - Unique task identifier",
  "user_id": "string - User identifier",
  "status": "string - Task status",
  "message": "string - Status message"
}
```

#### `GET /api/v1/models/train/status/{task_id}`
Get training task status.

**Path Parameters:**
- `task_id` (string, required) - Task identifier

**Headers:**
- `Authorization: Bearer {api_key}` (required)

**Response:**
```json
{
  "task_id": "string - Task identifier",
  "status": "string - PENDING|RUNNING|SUCCESS|FAILURE",
  "progress": "integer - Progress percentage 0-100",
  "result": "object - Training results (if completed)",
  "error": "string - Error message (if failed)",
  "created_at": "string - Task creation timestamp",
  "completed_at": "string - Task completion timestamp"
}
```

#### `GET /api/v1/models/train/history`
Get training history for user.

**Headers:**
- `Authorization: Bearer {api_key}` (required)

**Query Parameters:**
- `limit` (integer, optional) - Maximum results to return

**Response:**
```json
{
  "tasks": "array - List of training tasks",
  "total_count": "integer - Total number of tasks"
}
```

#### `GET /api/v1/models`
List user's trained models.

**Headers:**
- `Authorization: Bearer {api_key}` (required)

**Response:**
```json
{
  "models": "array - List of model objects",
  "total_count": "integer - Number of models"
}
```

### Analytics Endpoints
#### `GET /api/v1/analytics/statistics`
Get user statistics and analytics.

**Headers:**
- `Authorization: Bearer {api_key}` (required)

**Response:**
```json
{
  "user_id": "string - User identifier",
  "total_sessions": "integer - Total sessions",
  "average_focus_score": "number - Average focus score",
  "total_session_time": "number - Total session time in hours",
  "productivity_distribution": {
    "HIGHLY_PRODUCTIVE": "integer - Count",
    "PRODUCTIVE": "integer - Count",
    "MODERATELY_PRODUCTIVE": "integer - Count",
    "NOT_PRODUCTIVE": "integer - Count"
  },
  "best_session": {
    "session_id": "string - Session ID",
    "focus_score": "number - Focus score",
    "duration": "number - Duration"
  },
  "improvement_trend": "number - Improvement percentage"
}
```

#### `GET /api/v1/analytics/recommendations`
Get personalized focus recommendations.

**Headers:**
- `Authorization: Bearer {api_key}` (required)

**Response:**
```json
{
  "recommendations": "array - List of recommendations",
  "optimal_session_duration": "number - Recommended session length in minutes",
  "best_focus_times": "array - Optimal time periods",
  "confidence_score": "number - Recommendation confidence 0-1",
  "reasoning": "string - Explanation for recommendations"
}
```

### System Endpoints
#### `GET /api/v1/health`
System health check.

**Response:**
```json
{
  "status": "string - System status",
  "database_connected": "boolean - Database connection status",
  "total_users": "integer - Total users",
  "total_sessions": "integer - Total sessions",
  "timestamp": "string - ISO timestamp"
}
```

#### `GET /`
Root endpoint with system information.

**Response:**
```json
{
  "message": "string - System message",
  "version": "string - API version",
  "docs": "string - Documentation URL",
  "health": "string - Health endpoint URL"
}
```

## Focus Tracking API Architecture

### Client-Server Model
```
Client Application → API Server → Focus Service
       ↓                    ↓              ↓
   Capture Frame    →   Process Frame   →   Analyze Focus
   Send to API      →   Extract Face    →   Update Session
   Receive Results  →   Calculate Angle →   Return State
```

### Multi-User Support
- **Session Isolation**: Each user_id maintains independent tracking
- **Baseline Calibration**: Per-user angle adaptation
- **Concurrent Processing**: Multiple users tracked simultaneously
- **Memory Management**: Automatic cleanup after 30min inactivity

### Frame Processing Pipeline
1. **Frame Reception**: Base64 encoded image data
2. **Face Detection**: MediaPipe face landmark extraction
3. **Metric Calculation**: Angle, centroid, eye gap, confidence
4. **State Classification**: Focused/Distracted/Away determination
5. **Session Update**: Buffer management and statistics
6. **Response Generation**: JSON response with current state

### Real-Time Performance
- **Processing Time**: ~50-100ms per frame
- **Memory Usage**: ~1MB per active session
- **Scalability**: Horizontal scaling with load balancers
- **Optimization**: Frame skipping and compression options

## Machine Learning Pipeline

### Feature Extraction
- **Angle Variance**: Standard deviation of head yaw
- **Stability Score**: Ratio of frames with < 5 pixel motion
- **Presence Ratio**: Time face visible vs session duration
- **Context Switches**: Focused ↔ Distracted transitions

### Personalization Strategy

1. **Phase 1: Data Collection**
   - Rule-based labeling for obvious cases
   - User feedback collection (1-5 star ratings)
   - Session context tracking (time, task type, interruptions)

2. **Phase 2: Hybrid Learning**
   - Combine synthetic data with user feedback
   - Progressive model retraining
   - Uncertainty sampling for active learning

3. **Phase 3: Continuous Adaptation**
   - Online learning for real-time updates
   - Concept drift detection
   - Personalized recommendation engine

### Recommendation Engine

Analyzes successful sessions to provide:
- **Optimal focus times** (morning/afternoon/evening)
- **Ideal session duration** (median of productive sessions)
- **Confidence scores** based on data consistency
- **Personalized reasoning** from session patterns

## Configuration

### Environment Variables
```bash
FOCUS_API_URL=http://localhost:8000/api/v1
FOCUS_API_KEY=your_api_key_here
FOCUS_USER_ID=your_user_id_here
```

### Model Parameters
- **WMA Alpha**: 0.05 (baseline calibration drift)
- **Focus Threshold**: 20° (focused vs distracted)
- **Distraction Threshold**: 30° (distracted confirmation)
- **Distraction Duration**: 2.0 seconds

## Data Storage

### SQLite Database Tables
- **users**: User accounts and API keys
- **user_sessions**: Focus session data and features
- **user_feedback**: Productivity ratings and context
- **user_models**: Personalized ML models
- **focus_recommendations**: Time-based recommendations
- **training_tasks**: Async training task tracking

### Celery Architecture
- **Redis**: Message broker and result backend
- **Celery Workers**: Process training tasks asynchronously
- **Task Tracking**: Real-time progress monitoring
- **Error Handling**: Comprehensive error recovery and logging

### Session Features
```json
{
  "angle_variance": 15.2,
  "stability_score": 0.82,
  "presence_ratio": 0.90,
  "context_switches": 3,
  "focus_score": 75.5,
  "productivity_rating": 4
}
```

## Troubleshooting

### Common Issues

1. **Webcam not detected**
   - Check camera permissions
   - Verify no other applications are using the camera

2. **API connection failed**
   - Ensure API server is running on port 8000
   - Check network connectivity
   - Verify API key is valid

3. **Model training fails**
   - Need at least 3 sessions with feedback
   - Check database connection
   - Verify feature extraction is working

### Debug Mode
Set environment variable for verbose logging:
```bash
export DEBUG=1
uv run python main.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Documentation

- **[Main README](README.md)** - Project overview and quick start
- **[Focus Algorithm](FOCUS_ALGORITHM.md)** - Detailed algorithm flowcharts and technical specifications
- **[Focus API Guide](FOCUS_API_README.md)** - Complete API documentation and integration examples
- **[Demo Clients Guide](examples/README_DEMO_CLIENTS.md)** - Demo client usage and testing instructions

## Acknowledgments

- **MediaPipe** for face detection
- **FastAPI** for the backend framework
- **scikit-learn** for machine learning
- **OpenCV** for computer vision
- **matplotlib** for visualization
