# Focus Tracking API Documentation

## Overview

The Focus Management System provides comprehensive API-based focus tracking with advanced analytics, multi-user support, and real-time processing. The system now includes deep work metrics, distraction analytics, biological trends, gamification features, and inconsistency penalties.

## Architecture

```
Client Application → API Server → Focus Service → Analytics Engine
       ↓                    ↓              ↓              ↓
   Capture Frame    →   Process Frame   →   Analyze Focus  →   Calculate Analytics
   Send to API      →   Extract Face    →   Update Session →   Generate Insights
   Receive Results  →   Calculate Angle →   Return State   →   Track Progress
```

## 🆕 New Features

### Comprehensive Analytics
- **Deep Work Metrics**: Focus duration, efficiency, ratios, streaks
- **Distraction Analytics**: Interruptions, context switching costs, recovery times
- **Biological Trends**: Peak performance times, heatmaps, pattern consistency
- **Gamification Stats**: Focus streaks, achievements, peer comparison
- **Personalized Insights**: Actionable recommendations based on patterns

### Inconsistency Penalties
- **State Change Detection**: Penalizes frequent focus/distraction switching
- **Configurable Severity**: Adjustable penalty factors and maximum caps
- **Realistic Scoring**: Prevents unrealistic perfect scores

### Enhanced Web Interface
- **Interactive Dashboard**: Visual analytics with charts and progress bars
- **Real-Time Updates**: Live data during active sessions
- **Mobile Responsive**: Works on all device sizes

## API Endpoints

### 1. Start Focus Session
```http
POST /api/v1/focus/session/start
```

**Request Body:**
```json
{
  "user_id": "user123",
  "session_name": "Morning Work Session",
  "settings": {
    "focus_threshold": 20,
    "distraction_threshold": 30
  }
}
```

**Response:**
```json
{
  "user_id": "user123",
  "session_id": "session_abc123",
  "session_start": "2024-01-01T10:00:00Z",
  "status": "active",
  "message": "Focus tracking session started for user user123"
}
```

### 2. Analyze Frame
```http
POST /api/v1/focus/analyze
```

**Request Body:**
```json
{
  "user_id": "user123",
  "frame_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABA...",
  "image_width": 640,
  "image_height": 480,
  "timestamp": "2024-01-01T10:00:01Z"
}
```

**Response:**
```json
{
  "user_id": "user123",
  "current_state": "FOCUSED",
  "focus_score": 85.5,
  "baseline_angle": 12.3,
  "face_metrics": {
    "centroid": {"x": 320, "y": 240},
    "angle": 15.7,
    "magnitude": 25.4,
    "eye_gap": 45.2,
    "confidence": 0.92,
    "timestamp": "2024-01-01T10:00:01Z"
  },
  "session_stats": {
    "total_frames": 150,
    "focused_frames": 128,
    "distracted_frames": 15,
    "away_frames": 7,
    "session_duration": 5.0,
    "ground_frame_calibrated": true,
    "gaze_consistency_score": 78.5,
    "gaze_deviation": 3.2,
    "is_consistent": true
  },
  "timestamp": "2024-01-01T10:00:01Z"
}
```

### 3. Get Session Data
```http
GET /api/v1/focus/session/{user_id}
```

**Response:**
```json
{
  "user_id": "user123",
  "session_start": "2024-01-01T10:00:00Z",
  "session_end": "2024-01-01T10:05:00Z",
  "total_frames": 9000,
  "focused_frames": 7650,
  "distracted_frames": 900,
  "away_frames": 450,
  "focus_score": 85.0,
  "baseline_angle": 12.3,
  "comprehensive_analytics": {
    "deep_work_metrics": {
      "focus_duration": {
        "current_session_hours": 0.08,
        "daily_total_hours": 2.5,
        "weekly_total_hours": 12.3
      },
      "focus_efficiency": 85.0,
      "focus_to_rest_ratio": 8.5,
      "longest_focus_streak": {
        "minutes": 12.5,
        "start_time": "2024-01-01T10:01:00Z",
        "end_time": "2024-01-01T10:13:30Z"
      },
      "session_completion_rate": 95.0
    },
    "distraction_analytics": {
      "interruption_count": 3,
      "context_switching_cost": {
        "total_minutes": 69.0,
        "interruption_count": 3,
        "cost_per_interruption": 23.0
      },
      "distraction_frequency": 15.0,
      "distraction_patterns": {
        "distraction_percentage": 15.0,
        "away_percentage": 5.0,
        "common_distraction_types": {"DISTRACTED": 3, "AWAY": 1},
        "total_transitions": 8
      },
      "recovery_metrics": {
        "average_recovery_time_seconds": 45.2,
        "recovery_events": 3
      }
    },
    "biological_trends": {
      "focus_heatmap": [
        {"day_of_week": 0, "hour": 9, "focus_score": 88.5, "session_count": 2},
        {"day_of_week": 0, "hour": 10, "focus_score": 92.1, "session_count": 3}
      ],
      "peak_performance_times": [
        {"hour": 10, "average_focus_score": 92.1, "session_count": 3, "performance_level": "PEAK"}
      ],
      "rhythmic_insights": {
        "best_performance_day": 1,
        "pattern_consistency": 78.5,
        "average_score": 85.0,
        "score_std_deviation": 8.2
      }
    },
    "gamification_stats": {
      "focus_streaks": {
        "current_streak": 5,
        "longest_streak": 12,
        "total_active_days": 45,
        "recent_session_dates": ["2024-01-01", "2024-01-02", "2024-01-03"]
      },
      "achievements": [
        {"id": "first_session", "name": "First Focus", "description": "Completed your first focus session"},
        {"id": "dedicated_focus", "name": "Dedicated Focus", "description": "Completed 10 focus sessions"}
      ],
      "peer_comparison": {
        "focus_score_percentile": 75.0,
        "session_count_percentile": 60.0,
        "focus_hours_percentile": 80.0,
        "comparison_summary": "You focused more than 75% of users",
        "total_peers": 150
      }
    },
    "insights": [
      "Your peak focus time is 10:00 AM - consider scheduling important tasks then",
      "You have a 78.5% pattern consistency - try maintaining regular work hours",
      "Context switching costs you 69 minutes per session - minimize interruptions"
    ]
  }
}
```

### 4. End Session
```http
POST /api/v1/focus/session/end?user_id=user123
```

**Response:** Same as Get Session Data with final comprehensive analytics.

### 5. Get Active Users
```http
GET /api/v1/focus/users/active
```

**Response:**
```json
{
  "active_users": ["user123", "user456", "user789"],
  "total_count": 3,
  "timestamp": "2024-01-01T10:05:00Z"
}
```

### 6. Health Check
```http
GET /api/v1/focus/health
```

**Response:**
```json
{
  "status": "healthy",
  "active_sessions": 3,
  "service_version": "2.0.0",
  "timestamp": "2024-01-01T10:05:00Z"
}
```

### 7. Ground Frame Calibration
```http
POST /api/v1/focus/ground-frame/calibrate
```

**Request Body:**
```json
{
  "user_id": "user123",
  "frame_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABA...",
  "image_width": 640,
  "image_height": 480
}
```

**Response:**
```json
{
  "user_id": "user123",
  "calibrated": true,
  "baseline_angle": 12.3,
  "message": "Ground frame calibrated successfully",
  "timestamp": "2024-01-01T10:00:00Z"
}
```

## Focus States

| State | Description | Trigger | Penalty Impact |
|-------|-------------|---------|----------------|
| **FOCUSED** | User is attentive and focused | Angle < 20° from baseline | No penalty |
| **DISTRACTED** | User is looking away | Angle > 30° for 2+ seconds | Increases inconsistency |
| **AWAY** | No face detected | No face in frame | Increases inconsistency |

## 🎯 Inconsistency Penalty System

### How It Works
1. **Track State Changes**: Counts transitions between FOCUSED/DISTRACTED/AWAY
2. **Calculate Frequency**: (state_changes / (buffer_size - 1))
3. **Apply Penalty**: frequency × penalty_factor × 100
4. **Cap Maximum**: Limited by MAX_INCONSISTENCY_PENALTY

### Configuration
```python
# In src/config.py
INCONSISTENCY_PENALTY_ENABLED = True
INCONSISTENCY_PENALTY_FACTOR = 0.1      # 0.05-0.2
MAX_INCONSISTENCY_PENALTY = 15.0        # 5-20%
```

### Impact Examples
- **Consistent Focus**: 90% → 89.8% (0.2% penalty)
- **Moderately Inconsistent**: 80% → 79.2% (0.8% penalty)
- **Highly Inconsistent**: 50% → 40.0% (10% penalty)

## 📊 Analytics Explained

### Deep Work Metrics
- **Focus Duration**: Time spent in focused state (hours)
- **Focus Efficiency**: Percentage of session time focused
- **Focus-to-Rest Ratio**: focused_time / (distracted_time + away_time)
- **Longest Focus Streak**: Continuous focus period without interruptions
- **Session Completion Rate**: Percentage of sessions completed vs abandoned

### Distraction Analytics
- **Interruption Count**: Significant distractions (>60 seconds)
- **Context Switching Cost**: 23 minutes lost per interruption (research-based)
- **Distraction Frequency**: Percentage of time distracted
- **Recovery Metrics**: Time to refocus after distractions

### Biological Trends
- **Focus Heatmap**: 24×7 grid of performance patterns
- **Peak Performance Times**: Best performing hours with categorization
- **Pattern Consistency**: Predictability of focus patterns (0-100%)

### Gamification Stats
- **Focus Streaks**: Consecutive days with sessions (48-hour grace period)
- **Achievements**: Milestone badges with progressive difficulty
- **Peer Comparison**: Percentile rankings across user base

## Client Integration

### Python Client Example

```python
import requests
import base64
import cv2

class FocusTrackingClient:
    def __init__(self, api_url="http://localhost:8002"):
        self.api_url = api_url
        self.user_id = None
    
    def start_session(self, user_id):
        response = requests.post(
            f"{self.api_url}/api/v1/focus/session/start",
            json={"user_id": user_id, "session_name": "Python Client Session"}
        )
        self.user_id = user_id
        return response.json()
    
    def send_frame(self, frame):
        # Convert OpenCV frame to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        frame_data = f"data:image/jpeg;base64,{frame_base64}"
        
        height, width = frame.shape[:2]
        
        response = requests.post(
            f"{self.api_url}/api/v1/focus/analyze",
            json={
                "user_id": self.user_id,
                "frame_data": frame_data,
                "image_width": width,
                "image_height": height
            }
        )
        
        return response.json()
    
    def calibrate_ground_frame(self, frame):
        """Calibrate ground frame for gaze tracking"""
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        frame_data = f"data:image/jpeg;base64,{frame_base64}"
        
        height, width = frame.shape[:2]
        
        response = requests.post(
            f"{self.api_url}/api/v1/focus/ground-frame/calibrate",
            json={
                "user_id": self.user_id,
                "frame_data": frame_data,
                "image_width": width,
                "image_height": height
            }
        )
        
        return response.json()
    
    def end_session(self):
        response = requests.post(
            f"{self.api_url}/api/v1/focus/session/end",
            params={"user_id": self.user_id}
        )
        return response.json()

# Usage
client = FocusTrackingClient()
client.start_session("user123")

# Calibrate ground frame for enhanced metrics
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    calibration_result = client.calibrate_ground_frame(frame)
    print(f"Calibration: {calibration_result.get('message', 'Failed')}")

# Process frames from webcam
frame_count = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Send every 3rd frame for performance
    if frame_count % 3 == 0:
        result = client.send_frame(frame)
        print(f"Focus state: {result['current_state']} (Score: {result['focus_score']:.1f}%)")
        
        # Check for ground frame metrics
        if result['session_stats']['ground_frame_calibrated']:
            consistency = result['session_stats']['gaze_consistency_score']
            if consistency:
                print(f"Gaze consistency: {consistency:.1f}%")
    
    frame_count += 1
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

final_data = client.end_session()

# Display comprehensive analytics
if 'comprehensive_analytics' in final_data:
    analytics = final_data['comprehensive_analytics']
    print(f"\n📊 Session Analytics:")
    print(f"Focus Duration: {analytics['deep_work_metrics']['focus_duration']['current_session_hours']:.2f}h")
    print(f"Focus Efficiency: {analytics['deep_work_metrics']['focus_efficiency']:.1f}%")
    print(f"Interruptions: {analytics['distraction_analytics']['interruption_count']}")
    print(f"Context Switching Cost: {analytics['distraction_analytics']['context_switching_cost']['total_minutes']:.1f}m")
    print(f"Current Streak: {analytics['gamification_stats']['focus_streaks']['current_streak']} days")
    
    # Display insights
    print(f"\n💡 Insights:")
    for insight in analytics['insights']:
        print(f"• {insight}")

print(f"Final focus score: {final_data['focus_score']:.1f}%")
```

### JavaScript Client Example

```javascript
class FocusTrackingClient {
    constructor(apiUrl = 'http://localhost:8002') {
        this.apiUrl = apiUrl;
        this.userId = null;
    }
    
    async startSession(userId) {
        const response = await fetch(`${this.apiUrl}/api/v1/focus/session/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_id: userId,
                session_name: "Web Client Session"
            })
        });
        this.userId = userId;
        return await response.json();
    }
    
    async sendFrame(canvas) {
        const frameData = canvas.toDataURL('image/jpeg', 0.8);
        const response = await fetch(`${this.apiUrl}/api/v1/focus/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: this.userId,
                frame_data: frameData,
                image_width: canvas.width,
                image_height: canvas.height
            })
        });
        return await response.json();
    }
    
    async calibrateGroundFrame(canvas) {
        const frameData = canvas.toDataURL('image/jpeg', 0.8);
        const response = await fetch(`${this.apiUrl}/api/v1/focus/ground-frame/calibrate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: this.userId,
                frame_data: frameData,
                image_width: canvas.width,
                image_height: canvas.height
            })
        });
        return await response.json();
    }
    
    async endSession() {
        const response = await fetch(`${this.apiUrl}/api/v1/focus/session/end?user_id=${this.userId}`, {
            method: 'POST'
        });
        return await response.json();
    }
    
    async getSessionData() {
        const response = await fetch(`${this.apiUrl}/api/v1/focus/session/${this.userId}`);
        return await response.json();
    }
}

// Usage with video element
const client = new FocusTrackingClient();
let frameCount = 0;

// Start session
await client.startSession('web_user_123');

const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

// Calibrate ground frame
const calibrationResult = await client.calibrateGroundFrame(canvas);
console.log('Calibration:', calibrationResult.message);

// Process frames
setInterval(async () => {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Send every 3rd frame for performance
    if (frameCount % 3 === 0) {
        const result = await client.sendFrame(canvas);
        
        console.log('Focus state:', result.current_state);
        console.log('Focus score:', result.focus_score.toFixed(1) + '%');
        
        // Check ground frame metrics
        if (result.session_stats.ground_frame_calibrated) {
            console.log('Gaze consistency:', result.session_stats.gaze_consistency_score + '%');
            console.log('Gaze deviation:', result.session_stats.gaze_deviation + '°');
        }
    }
    
    frameCount++;
}, 100); // Check every 100ms, send every 300ms

// End session and show analytics
document.getElementById('endSession').addEventListener('click', async () => {
    const finalData = await client.endSession();
    
    if (finalData.comprehensive_analytics) {
        displayAnalytics(finalData.comprehensive_analytics);
    }
});

function displayAnalytics(analytics) {
    console.log('📊 Session Analytics:');
    console.log('Focus Duration:', analytics.deep_work_metrics.focus_duration.current_session_hours + 'h');
    console.log('Focus Efficiency:', analytics.deep_work_metrics.focus_efficiency + '%');
    console.log('Interruptions:', analytics.distraction_analytics.interruption_count);
    console.log('Context Switching Cost:', analytics.distraction_analytics.context_switching_cost.total_minutes + 'm');
    console.log('Current Streak:', analytics.gamification_stats.focus_streaks.current_streak + ' days');
    
    console.log('\n💡 Insights:');
    analytics.insights.forEach(insight => console.log('•', insight));
}
```

## 🌐 Web Demo Client

### Enhanced Features
- **Interactive Analytics Dashboard**: Visual representation of all metrics
- **Real-Time Updates**: Live data during active sessions
- **Progress Bars**: Visual efficiency indicators
- **Heatmap Visualization**: 7×24 hour performance grid
- **Achievement Badges**: Hover tooltips with descriptions
- **Mobile Responsive**: Works on all device sizes

### Quick Start
1. Start server: `python server.py`
2. Open browser: `http://localhost:8002/examples/web_demo_client.html`
3. Test workflow: Start Session → Send Test Frame → End Session
4. Analytics dashboard appears automatically!

### Demo Script
```bash
# Run the comprehensive demo
python demo_web_analytics.py
```

## Frame Format Requirements

### Supported Formats
- **JPEG**: Recommended for size/quality balance
- **PNG**: Higher quality, larger file size
- **Base64 encoding**: Required for API transmission

### Resolution Guidelines
- **Minimum**: 320x240 pixels
- **Recommended**: 640x480 pixels
- **Maximum**: 1920x1080 pixels

### Frame Rate
- **Client sending**: 10-30 FPS
- **Server processing**: Real-time per frame
- **Recommended**: Send every 3rd frame for performance

## ⚙️ Configuration

### Key Parameters
```python
# Focus Detection
FOCUSED_ANGLE_THRESHOLD = 20          # degrees from baseline
DISTRACTED_ANGLE_THRESHOLD = 30        # degrees from baseline
DISTRACTION_CONFIRMATION_TIME = 2.0    # seconds

# Realistic Scoring
MAX_REALISTIC_FOCUS_SCORE = 99.0      # maximum achievable
HIGH_FOCUS_THRESHOLD = 85.0           # high performance threshold

# Inconsistency Penalties
INCONSISTENCY_PENALTY_ENABLED = True
INCONSISTENCY_PENALTY_FACTOR = 0.1     # 0.05-0.2
MAX_INCONSISTENCY_PENALTY = 15.0       # 5-20%

# Analytics
CONTEXT_SWITCH_RECOVERY_MINUTES = 23    # minutes lost per interruption
MINIMUM_INTERUPTION_DURATION_SECONDS = 60

# Gamification
ACHIEVEMENT_THRESHOLDS = {
    "first_session": 1,
    "dedicated_focus": 10,
    "hour_power": 1,
    "deep_work_expert": 10
}
STREAK_RESET_HOURS = 48                 # grace period
```

### Configuration Guide
See `CONFIG_GUIDE.md` for detailed tuning instructions and scenarios.

## User Session Management

### Session Isolation
- Each user_id maintains separate session data
- Baseline angles are tracked per user
- Focus buffers are independent per user
- Ground frame calibration is per user

### Session Lifecycle
1. **Start**: Initialize session with user_id
2. **Active**: Process frames and update state
3. **End**: Finalize session and return comprehensive analytics
4. **Cleanup**: Automatic cleanup after 30 minutes inactivity

### Concurrent Users
- **Maximum**: Limited by server resources
- **Memory**: ~1MB per active session
- **CPU**: ~5-10% per active user at 10 FPS

## Performance Considerations

### Client Side
- **Frame compression**: Use JPEG quality 80-90%
- **Frame rate**: 10-15 FPS for real-time
- **Batch processing**: Send frames in batches if needed
- **Ground frame calibration**: One-time setup per session

### Server Side
- **Processing time**: ~50-100ms per frame
- **Memory usage**: Proportional to active users
- **Analytics calculation**: ~200ms for comprehensive analytics
- **Scalability**: Horizontal scaling with load balancers

### Optimization Tips
```python
# Send every 3rd frame for performance
if frame_count % 3 == 0:
    result = client.send_frame(frame)

# Use lower resolution for better performance
small_frame = cv2.resize(frame, (320, 240))

# Compress frames before sending
encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
_, buffer = cv2.imencode('.jpg', frame, encode_param)

# Calibrate ground frame once per session
if not calibrated:
    client.calibrate_ground_frame(frame)
    calibrated = True
```

## Error Handling

### Common Errors
| Error Code | Description | Solution |
|------------|-------------|----------|
| 400 | Invalid frame data | Check base64 encoding |
| 404 | Session not found | Start session first |
| 422 | Missing fields | Include all required fields |
| 500 | Server error | Check server logs |

### Error Response Format
```json
{
  "error": "ValidationError",
  "message": "Missing required field: user_id",
  "details": {
    "field": "user_id",
    "expected": "string"
  },
  "timestamp": "2024-01-01T10:00:00Z"
}
```

## Security Considerations

### Authentication
- API key authentication recommended for production
- Rate limiting to prevent abuse
- User ID validation

### Data Privacy
- Frames are processed in memory only
- No persistent storage of frame data
- Session data retention configurable
- Ground frame data stored securely per user

### Network Security
- HTTPS for production deployments
- CORS configuration for web clients
- Request size limits

## Deployment

### Docker Setup
```yaml
version: '3.8'
services:
  focus-api:
    build: .
    ports:
      - "8002:8002"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Environment Variables
```bash
export API_HOST=0.0.0.0
export API_PORT=8002
export REDIS_URL=redis://localhost:6379
export LOG_LEVEL=INFO
```

## Monitoring

### Metrics
- Active sessions count
- Frames processed per second
- Average processing time
- Error rates
- Analytics calculation time

### Health Checks
```bash
# Service health
curl http://localhost:8002/api/v1/focus/health

# Active users
curl http://localhost:8002/api/v1/focus/users/active
```

### Logging
- Session start/end events
- Frame processing errors
- Performance metrics
- User activity logs
- Analytics calculation logs

## Testing

### Unit Tests
```bash
# Run focus API tests
uv run pytest tests/test_focus_api.py -v

# Test analytics service
uv run pytest tests/test_analytics_service.py -v

# Test inconsistency penalties
python test_inconsistency_penalties.py
```

### Integration Tests
```bash
# Run example client
python examples/focus_client_example.py

# Test comprehensive analytics
python test_comprehensive_analytics.py

# Test realistic scoring
python test_realistic_analytics.py
```

### Load Testing
```bash
# Test with multiple concurrent users
python examples/multi_user_demo.py
```

## 📚 Documentation

- **`ANALYTICS_LOGIC.md`**: Detailed technical explanation of all analytics calculations
- **`CONFIG_GUIDE.md`**: Comprehensive configuration tuning guide
- **`demo_web_analytics.py`**: Interactive demo script with testing instructions

## Migration from Webcam

### Changes Required
1. **Remove webcam code** from main.py
2. **Add API client** integration
3. **Convert frames** to base64
4. **Handle responses** from API
5. **Update UI** for remote processing
6. **Add analytics dashboard** for comprehensive insights

### Benefits
- **Multi-user support**: Server-side processing
- **Comprehensive analytics**: Deep insights into focus patterns
- **Scalability**: Horizontal scaling possible
- **Resource sharing**: Centralized face detection
- **Data persistence**: Server-side session storage
- **Advanced features**: Ground frame calibration, inconsistency penalties

## 🚀 Quick Start Guide

1. **Start Server**: `python server.py`
2. **Open Web Client**: `http://localhost:8002/examples/web_demo_client.html`
3. **Test Basic Flow**: Start Session → Send Test Frame → End Session
4. **View Analytics**: Comprehensive dashboard appears automatically
5. **Explore Features**: Ground frame calibration, real-time updates, insights

This enhanced API-based approach enables robust, multi-user focus tracking applications with comprehensive analytics, realistic scoring, and actionable insights for productivity improvement.
