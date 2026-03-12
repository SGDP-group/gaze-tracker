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

### Focus Tracking API (New!)
- `POST /api/v1/focus/analyze` - Analyze frame for focus tracking
- `POST /api/v1/focus/session/start` - Start focus tracking session
- `POST /api/v1/focus/session/end` - End session and get results
- `GET /api/v1/focus/session/{user_id}` - Get current session data
- `GET /api/v1/focus/users/active` - List active users
- `POST /api/v1/focus/cleanup` - Clean up inactive sessions
- `GET /api/v1/focus/health` - Focus service health check

### Authentication
- `POST /api/v1/users` - Create user with API key
- `GET /api/v1/users/me` - Get current user info

### Sessions
- `POST /api/v1/sessions` - Create new session
- `GET /api/v1/sessions` - List user sessions
- `GET /api/v1/sessions/{session_id}` - Get session details

### Feedback
- `POST /api/v1/feedback` - Submit session feedback

### Machine Learning
- `POST /api/v1/models/train` - Train personalized model (synchronous)
- `POST /api/v1/models/train/async` - Train personalized model (asynchronous)
- `GET /api/v1/models/train/status/{task_id}` - Get training task status
- `GET /api/v1/models/train/history` - Get training task history
- `GET /api/v1/models/train/tasks` - Get user training tasks
- `GET /api/v1/models` - List user models

### Analytics
- `GET /api/v1/analytics/statistics` - User statistics
- `GET /api/v1/analytics/recommendations` - Focus recommendations
- `GET /api/v1/health` - API health check

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